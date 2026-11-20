"""Extraction result types and the extractor interface."""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

# The MVP extraction schema (deep-dive §5). Anything outside this set is noise
# for the accountant and is not surfaced in the review UI.
INVOICE_FIELDS = (
    "invoice_number",
    "invoice_date",
    "vendor_name",
    "vendor_tin",
    "vendor_address",
    "buyer_name",
    "buyer_tin",
    "contract_number",
    "contract_date",
    "subtotal",
    "vat_amount",
    "total_amount",
    "currency",
)

#: Fields the accountant cannot post to 1C without.
REQUIRED_FIELDS = ("invoice_number", "invoice_date", "vendor_name", "vendor_tin", "total_amount")


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    return value


@dataclass
class FieldValue:
    """One extracted field with the evidence trail behind it.

    `source` is shown in the UI tooltip. An accountant deciding whether to trust
    a number wants to know it came from the line labelled "Jami QQS bilan" and
    not from a model's imagination.
    """

    value: Any = None
    confidence: float = 0.0
    source: str = "none"
    raw_text: str | None = None
    page: int | None = None
    bbox: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": _serialize(self.value),
            "confidence": round(float(self.confidence), 4),
            "source": self.source,
            "raw_text": self.raw_text,
            "page": self.page,
            "bbox": self.bbox,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FieldValue:
        return cls(
            value=data.get("value"),
            confidence=float(data.get("confidence") or 0.0),
            source=str(data.get("source") or "none"),
            raw_text=data.get("raw_text"),
            page=data.get("page"),
            bbox=data.get("bbox"),
        )

    @property
    def is_present(self) -> bool:
        return self.value not in (None, "", [])


@dataclass
class LineItem:
    index: int
    description: str | None = None
    unit: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None
    vat_rate: Decimal | None = None
    vat_amount: Decimal | None = None
    confidence: float = 0.0
    raw_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "description": self.description,
            "unit": self.unit,
            "quantity": _serialize(self.quantity),
            "unit_price": _serialize(self.unit_price),
            "amount": _serialize(self.amount),
            "vat_rate": _serialize(self.vat_rate),
            "vat_amount": _serialize(self.vat_amount),
            "confidence": round(float(self.confidence), 4),
            "raw_text": self.raw_text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LineItem:
        def dec(key: str) -> Decimal | None:
            raw = data.get(key)
            if raw in (None, ""):
                return None
            try:
                return Decimal(str(raw))
            except Exception:
                return None

        return cls(
            index=int(data.get("index") or 0),
            description=data.get("description"),
            unit=data.get("unit"),
            quantity=dec("quantity"),
            unit_price=dec("unit_price"),
            amount=dec("amount"),
            vat_rate=dec("vat_rate"),
            vat_amount=dec("vat_amount"),
            confidence=float(data.get("confidence") or 0.0),
            raw_text=data.get("raw_text"),
        )


@dataclass
class ExtractionResult:
    fields: dict[str, FieldValue] = field(default_factory=dict)
    line_items: list[LineItem] = field(default_factory=list)
    doc_type: str = "invoice"
    strategy: str = "rules"
    model_name: str | None = None
    duration_ms: int = 0
    cost_usd: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def get(self, name: str) -> FieldValue:
        return self.fields.get(name, FieldValue())

    def value(self, name: str) -> Any:
        return self.get(name).value

    def set(self, name: str, value: FieldValue) -> None:
        self.fields[name] = value

    @property
    def overall_confidence(self) -> float:
        """Mean confidence across required fields, penalised for missing ones.

        Weighted toward required fields on purpose: a perfect vendor address
        does not make up for a missing total.
        """
        scores: list[float] = []
        for name in REQUIRED_FIELDS:
            entry = self.fields.get(name)
            scores.append(entry.confidence if entry and entry.is_present else 0.0)
        optional = [
            entry.confidence
            for name, entry in self.fields.items()
            if name not in REQUIRED_FIELDS and entry.is_present
        ]
        if optional:
            scores.append(sum(optional) / len(optional))
        if self.line_items:
            scores.append(sum(item.confidence for item in self.line_items) / len(self.line_items))
        return round(sum(scores) / len(scores), 4) if scores else 0.0

    def fields_to_dict(self) -> dict[str, Any]:
        return {name: entry.to_dict() for name, entry in self.fields.items()}

    def line_items_to_dict(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.line_items]

    @classmethod
    def from_stored(
        cls, fields: dict[str, Any], line_items: list[dict[str, Any]], strategy: str = "stored"
    ) -> ExtractionResult:
        return cls(
            fields={name: FieldValue.from_dict(data) for name, data in (fields or {}).items()},
            line_items=[LineItem.from_dict(item) for item in (line_items or [])],
            strategy=strategy,
        )


@dataclass
class ExtractionContext:
    """Everything an extractor may use beyond the raw text."""

    blocks: list[dict[str, Any]] = field(default_factory=list)
    script_summary: dict[str, Any] = field(default_factory=dict)
    doc_type: str = "invoice"
    template_hints: dict[str, Any] = field(default_factory=dict)
    company_tin: str | None = None
    default_currency: str = "UZS"
    vat_rate_percent: float = 12.0


class Extractor(ABC):
    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def extract(self, text: str, context: ExtractionContext) -> ExtractionResult: ...
