"""LLM field extraction via an OpenAI-compatible chat completions endpoint.

This is the *escalation* path, not the default one. The rule extractor resolves
the common layouts for nothing; the LLM is what handles the vendor whose invoice
looks like nothing else in the market. Running it only on low-confidence
documents is what keeps per-document cost at the fraction of a cent assumed in
the financial model instead of paying for every page.

Cost note: gpt-4o-mini at roughly $0.15 / 1M input tokens and a ~1,200-token
invoice works out to ~$0.0002 per escalated document. Even escalating 30% of a
50,000-document month is under $5.

Data residency: only OCR *text* is sent, never the page image. See
docs/data-residency.md — that split is what keeps document images inside
Uzbekistan while still using a foreign model API.
"""

from __future__ import annotations

import json
import time
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.extract.base import (
    ExtractionContext,
    ExtractionResult,
    Extractor,
    FieldValue,
    LineItem,
)
from app.services.extract.parsers import parse_amount, parse_date, parse_tin

logger = get_logger(__name__)

# Confidence assigned to LLM output before validation adjusts it. Deliberately
# below a clean rule-based label match: the model cannot cite the line it read
# the value from, so it gets less trust by default.
CONF_LLM = 0.82

SYSTEM_PROMPT = """\
You extract structured data from Uzbek and Russian business invoices \
(hisob-faktura / счёт-фактура) that have been through OCR.

Context you must assume:
- Text may mix Uzbek Latin, Uzbek Cyrillic and Russian, sometimes in one line.
- STIR (ИНН) is a 9-digit taxpayer number. The supplier's and the buyer's are \
different numbers; bind each to the right party.
- Amounts use space or comma thousands separators and a comma decimal mark: \
"1 250 000,00" means 1250000.00. Normalise every amount to a plain decimal \
with a dot.
- The standard VAT (QQS/НДС) rate is 12%.
- The default currency is UZS unless the document says otherwise.
- OCR damage is common. If a value is unreadable or you are unsure, return null \
for it. Never invent a value: a blank field is corrected in seconds, a \
plausible wrong number becomes a tax penalty.

Return ONLY a JSON object with exactly these keys:
{
  "invoice_number": string|null,
  "invoice_date": "YYYY-MM-DD"|null,
  "vendor_name": string|null,
  "vendor_tin": string|null,
  "vendor_address": string|null,
  "buyer_name": string|null,
  "buyer_tin": string|null,
  "contract_number": string|null,
  "subtotal": number|null,
  "vat_amount": number|null,
  "total_amount": number|null,
  "currency": string|null,
  "line_items": [
    {"description": string, "unit": string|null, "quantity": number|null,
     "unit_price": number|null, "amount": number|null}
  ],
  "uncertain_fields": [string]
}
List in "uncertain_fields" the name of every field you were not confident about.\
"""

FEW_SHOT_INPUT = """\
HISOB-FAKTURA
Raqami: 1245
Sana: 12.03.2026
Yetkazib beruvchi: "OLTIN VODIY SAVDO" MChJ
STIR: 302145879
Xaridor: "AGROMASH SERVIS" MChJ
STIR: 205673412
№   Tovar nomi      O'lchov   Soni   Narxi          Summa
1   Sement M-400    tonna     12     1 250 000,00   15 000 000,00
Jami: 15 000 000,00
QQS (12%): 1 800 000,00
Jami QQS bilan: 16 800 000,00 so'm\
"""

FEW_SHOT_OUTPUT = json.dumps({
    "invoice_number": "1245",
    "invoice_date": "2026-03-12",
    "vendor_name": '"OLTIN VODIY SAVDO" MChJ',
    "vendor_tin": "302145879",
    "vendor_address": None,
    "buyer_name": '"AGROMASH SERVIS" MChJ',
    "buyer_tin": "205673412",
    "contract_number": None,
    "subtotal": 15000000.00,
    "vat_amount": 1800000.00,
    "total_amount": 16800000.00,
    "currency": "UZS",
    "line_items": [
        {"description": "Sement M-400", "unit": "tonna", "quantity": 12,
         "unit_price": 1250000.00, "amount": 15000000.00}
    ],
    "uncertain_fields": [],
}, ensure_ascii=False)

# Truncation guard. Invoices are short; anything longer is a multi-page scan
# whose tail is signatures and stamps, not fields.
MAX_INPUT_CHARS = 12000

_TEXT_FIELDS = ("invoice_number", "vendor_name", "vendor_address", "buyer_name",
                "contract_number", "currency")
_TIN_FIELDS = ("vendor_tin", "buyer_tin")
_AMOUNT_FIELDS = ("subtotal", "vat_amount", "total_amount")


class LLMExtractor(Extractor):
    name = "llm"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        client: Any = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.llm_api_key
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model
        # Injectable so tests exercise the parsing without network access.
        self._client = client

    def is_available(self) -> bool:
        return bool(self.api_key) or self._client is not None

    def extract(self, text: str, context: ExtractionContext) -> ExtractionResult:
        started = time.perf_counter()
        result = ExtractionResult(strategy=self.name, model_name=self.model)

        payload = self._request_payload(text, context)
        try:
            body = self._post(payload)
        except httpx.HTTPError as exc:
            logger.warning("LLM extraction failed", extra={"error": str(exc)})
            result.warnings.append(f"llm request failed: {exc}")
            return result

        content = self._content_of(body)
        if content is None:
            result.warnings.append("llm returned no content")
            return result

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = _salvage_json(content)
            if data is None:
                result.warnings.append("llm returned unparseable JSON")
                return result

        self._populate(result, data)
        result.cost_usd = _estimate_cost(body, self.model)
        result.duration_ms = int((time.perf_counter() - started) * 1000)
        return result

    # -- request ------------------------------------------------------------

    def _request_payload(self, text: str, context: ExtractionContext) -> dict[str, Any]:
        truncated = text[:MAX_INPUT_CHARS]
        hint = ""
        if context.script_summary.get("mixed"):
            hint = ("\nNote: this document mixes scripts. Company names may appear "
                    "in a different alphabet than the labels.")
        return {
            "model": self.model,
            # Deterministic: the same document must extract identically every
            # time, or the accountant loses trust the first time it does not.
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": FEW_SHOT_INPUT},
                {"role": "assistant", "content": FEW_SHOT_OUTPUT},
                {"role": "user", "content": truncated + hint},
            ],
        }

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._client is not None:
            return self._client.create(payload)
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _content_of(body: dict[str, Any]) -> str | None:
        choices = body.get("choices") or []
        if not choices:
            return None
        return (choices[0].get("message") or {}).get("content")

    # -- response mapping ---------------------------------------------------

    def _populate(self, result: ExtractionResult, data: dict[str, Any]) -> None:
        uncertain = {str(name) for name in (data.get("uncertain_fields") or [])}

        def confidence_for(field: str) -> float:
            # The model self-reporting doubt is the most useful signal it gives;
            # honour it by dropping below the review threshold.
            return 0.55 if field in uncertain else CONF_LLM

        for field in _TEXT_FIELDS:
            value = data.get(field)
            if value not in (None, ""):
                result.set(field, FieldValue(
                    value=str(value).strip(),
                    confidence=confidence_for(field),
                    source="llm",
                ))

        for field in _TIN_FIELDS:
            tin = parse_tin(data.get(field))
            if tin:
                result.set(field, FieldValue(
                    value=tin, confidence=confidence_for(field), source="llm"
                ))

        for field in _AMOUNT_FIELDS:
            amount = parse_amount(str(data.get(field))) if data.get(field) is not None else None
            if amount is not None:
                result.set(field, FieldValue(
                    value=amount, confidence=confidence_for(field), source="llm"
                ))

        date_value = parse_date(data.get("invoice_date"))
        if date_value:
            result.set("invoice_date", FieldValue(
                value=date_value, confidence=confidence_for("invoice_date"), source="llm"
            ))

        for index, raw_item in enumerate(data.get("line_items") or [], start=1):
            if not isinstance(raw_item, dict):
                continue
            description = raw_item.get("description")
            if not description:
                continue
            result.line_items.append(LineItem(
                index=index,
                description=str(description).strip(),
                unit=(str(raw_item["unit"]).strip() if raw_item.get("unit") else None),
                quantity=_decimal(raw_item.get("quantity")),
                unit_price=_decimal(raw_item.get("unit_price")),
                amount=_decimal(raw_item.get("amount")),
                confidence=CONF_LLM,
            ))


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return parse_amount(str(value))


def _salvage_json(content: str) -> dict[str, Any] | None:
    """Recover a JSON object from a reply wrapped in prose or a code fence."""
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(content[start:end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


# Published per-1M-token prices. Only used for the cost figures shown on the
# dashboard, so being slightly stale is harmless.
_PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
}


def _estimate_cost(body: dict[str, Any], model: str) -> float:
    usage = body.get("usage") or {}
    prompt_tokens = float(usage.get("prompt_tokens") or 0)
    completion_tokens = float(usage.get("completion_tokens") or 0)
    input_price, output_price = _PRICES_PER_MILLION.get(model, (0.15, 0.60))
    return round(
        prompt_tokens / 1_000_000 * input_price + completion_tokens / 1_000_000 * output_price,
        6,
    )
