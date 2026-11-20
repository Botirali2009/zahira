"""Deterministic rule-based extraction for Uzbek/Russian invoices.

Why rules and not "just call the LLM": at 50 customers this runs on ~50,000
documents a month. Every field the rules resolve is a field nobody pays an API
for, and — more importantly for a chief accountant — the same document always
produces the same answer, with a citable reason for every value.

The LLM extractor (`extract/llm.py`) is the escalation path for documents these
rules cannot resolve confidently, not the default path.

Matching strategy
-----------------
1. Fold each line (casefold + Uzbek apostrophe normalisation) for matching while
   keeping the original text for values, so what the accountant sees is exactly
   what the document says.
2. Find every known label in a line with word-boundary checks, longest match
   first, and treat the text between one label and the next as that label's
   value. This is what lets a single line like
   `Yetkazib beruvchi: "OLTIN VODIY" MChJ   STIR: 302145879`
   yield both the vendor name and the vendor TIN.
3. Walk the labels in document order keeping track of which counterparty block
   we are inside, so an unqualified `STIR:` binds to the right party.
"""

from __future__ import annotations

import re
import time
from decimal import Decimal
from typing import Any

from app.services.extract import lexicon
from app.services.extract.base import (
    ExtractionContext,
    ExtractionResult,
    Extractor,
    FieldValue,
    LineItem,
)
from app.services.extract.parsers import (
    clean_party_name,
    parse_amount,
    parse_currency,
    parse_date,
    parse_tin,
)
from app.services.script_detect import (
    fold_confusables,
    lower_preserving_length,
    normalize_uzbek_latin,
)

# Confidence assigned by how the value was found. These are priors; validation
# (services/validate.py) adjusts them afterwards using cross-field arithmetic.
CONF_LABEL_SAME_LINE = 0.95
CONF_LABEL_NEXT_LINE = 0.85
CONF_TEMPLATE = 0.93
CONF_PATTERN = 0.75
CONF_DERIVED = 0.65
CONF_TABLE_ROW = 0.88
CONF_TABLE_ROW_CONSISTENT = 0.96  # quantity x price == amount
# Deliberately below the review threshold: a value reconstructed from OCR
# damage must always reach a human before it reaches a tax filing.
CONF_REPAIRED = 0.55

# Quote characters are NOT stripped: Uzbek company names are written
# `"OLTIN VODIY" MChJ` and 1C matches counterparties on the full legal name.
_VALUE_SEPARATORS = " \t:=—–-№#"
_PERCENT = re.compile(r"(\d{1,2}(?:[.,]\d+)?)\s*%")
_INVOICE_NUMBER = re.compile(r"[№#]?\s*([A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9\-/_.]{0,29})")
_NUMERIC_FRAGMENT = re.compile(r"^[\d.,'’]+$")
_GROUP_FRAGMENT = re.compile(r"^\d{3}(?:[.,]\d{1,3})?$")
_INDEX_PREFIX = re.compile(r"^\s*(\d{1,3})\s*[.)]?\s+")
_MULTISPACE = re.compile(r"\s{2,}")

# Field keys used by the label scanner (a superset of the output schema).
_SCAN_LABELS: dict[str, tuple[str, ...]] = {
    "invoice_number": lexicon.INVOICE_NUMBER_LABELS,
    "date": lexicon.DATE_LABELS,
    "vendor": lexicon.VENDOR_LABELS,
    "buyer": lexicon.BUYER_LABELS,
    "tin": lexicon.TIN_LABELS,
    "address": lexicon.ADDRESS_LABELS,
    "contract": lexicon.CONTRACT_LABELS,
    "bank_account": lexicon.BANK_ACCOUNT_LABELS,
    "total_with_vat": lexicon.TOTAL_WITH_VAT_LABELS,
    "subtotal": lexicon.SUBTOTAL_LABELS,
    "vat": lexicon.VAT_LABELS,
    "currency": lexicon.CURRENCY_LABELS,
}


def fold(text: str) -> str:
    """Canonical form for label matching: lowercase, apostrophes and homoglyphs.

    Length-preserving, because label offsets are used to slice values out of the
    original line.
    """
    return fold_confusables(normalize_uzbek_latin(lower_preserving_length(text)))


# Sorted longest-first so a specific label always wins over a shorter one that
# starts at the same position (e.g. "jami qqs bilan" over "jami").
_LABEL_INDEX: list[tuple[str, str]] = sorted(
    ((key, fold(label)) for key, labels in _SCAN_LABELS.items() for label in labels),
    key=lambda pair: len(pair[1]),
    reverse=True,
)


class LabelMatch:
    __slots__ = ("field", "label", "start", "end", "value")

    def __init__(self, field: str, label: str, start: int, end: int, value: str) -> None:
        self.field = field
        self.label = label
        self.start = start
        self.end = end
        self.value = value

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"LabelMatch({self.field!r}, {self.label!r}, value={self.value!r})"


def _is_boundary(text: str, start: int, end: int) -> bool:
    before = text[start - 1] if start > 0 else " "
    after = text[end] if end < len(text) else " "
    return not before.isalnum() and not (after.isalnum() and text[end - 1].isalnum())


def scan_labels(original: str) -> list[LabelMatch]:
    """Find all known labels in one line, longest-first, non-overlapping.

    Every occurrence is returned, not just the first: a side-by-side header
    prints `STIR: … STIR: …` on one line, and stopping at the first match loses
    the buyer's TIN entirely.
    """
    folded = fold(original)
    claimed: list[tuple[int, int]] = []
    matches: list[LabelMatch] = []

    for field_key, label in _LABEL_INDEX:
        start = folded.find(label)
        while start != -1:
            end = start + len(label)
            overlaps = any(start < c_end and end > c_start for c_start, c_end in claimed)
            if not overlaps and _is_boundary(folded, start, end):
                claimed.append((start, end))
                matches.append(LabelMatch(field_key, label, start, end, ""))
            start = folded.find(label, end if not overlaps else start + 1)

    matches.sort(key=lambda match: match.start)
    for position, match in enumerate(matches):
        stop = matches[position + 1].start if position + 1 < len(matches) else len(original)
        match.value = original[match.end:stop].strip().strip(_VALUE_SEPARATORS).strip()
    return matches


def merge_numeric_tokens(tokens: list[str]) -> list[str]:
    """Rejoin numbers that whitespace thousands separators split apart.

    `["12", "1", "250", "000,00"]` becomes `["12", "1 250 000,00"]`.

    Two rules keep this from gluing unrelated numbers together:
    * a fragment is only absorbed when it is exactly a 3-digit group (so the
      quantity `12` never merges into the price that follows it), and
    * absorption stops once the accumulated number has a decimal part, because
      nothing follows the tiyin.
    """
    merged: list[str] = []
    for token in tokens:
        if merged and _GROUP_FRAGMENT.match(token) and _is_open_numeric_run(merged[-1]):
            merged[-1] = f"{merged[-1]} {token}"
        else:
            merged.append(token)
    return merged


def _is_open_numeric_run(token: str) -> bool:
    """True when `token` is digits (possibly space-grouped) with no decimals yet."""
    compact = token.replace(" ", "").replace(" ", "")
    return bool(compact) and compact.isdigit()


def split_row(line: str) -> list[str]:
    """Split a table row into cells using whichever delimiter the layout uses."""
    if "|" in line:
        return [cell.strip() for cell in line.split("|") if cell.strip()]
    if "\t" in line:
        return [cell.strip() for cell in line.split("\t") if cell.strip()]
    if _MULTISPACE.search(line.strip()):
        cells = [cell.strip() for cell in _MULTISPACE.split(line.strip()) if cell.strip()]
        if len(cells) >= 3:
            return cells
    return merge_numeric_tokens(line.split())


class RuleBasedExtractor(Extractor):
    name = "rules"

    def is_available(self) -> bool:
        return True

    def extract(self, text: str, context: ExtractionContext) -> ExtractionResult:
        started = time.perf_counter()
        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        result = ExtractionResult(strategy=self.name)
        result.doc_type = detect_document_type(lines)

        line_matches = [scan_labels(line) for line in lines]

        self._extract_parties(lines, line_matches, result)
        self._extract_header(lines, line_matches, result)
        self._extract_line_items(lines, line_matches, result, context)
        self._extract_totals(lines, line_matches, result, context)
        self._apply_currency(lines, result, context)
        self._reconcile_totals(result, context)

        result.duration_ms = int((time.perf_counter() - started) * 1000)
        return result

    # -- parties ------------------------------------------------------------

    def _extract_parties(
        self, lines: list[str], line_matches: list[list[LabelMatch]], result: ExtractionResult
    ) -> None:
        """Bind names, TINs and addresses to the vendor or the buyer.

        Labels are walked in document order; an unqualified `STIR:` belongs to
        whichever counterparty block we are currently inside, which is how these
        documents are actually laid out.
        """
        current: str | None = None
        # Column layout of the most recent line that named counterparties. In a
        # side-by-side header the vendor and buyer blocks share every following
        # line, so an unqualified `STIR:` must bind by horizontal position, not
        # by "whichever party we saw last".
        party_columns: list[tuple[int, str]] = []

        for index, matches in enumerate(line_matches):
            line_parties = sorted(
                (match.start, "vendor" if match.field == "vendor" else "buyer")
                for match in matches
                if match.field in ("vendor", "buyer")
            )
            if line_parties:
                party_columns = line_parties

            party_by_match = self._bind_parties(matches, party_columns, current)

            for match in matches:
                if match.field in ("vendor", "buyer"):
                    current = "vendor" if match.field == "vendor" else "buyer"
                    name, confidence = self._value_or_next_line(match, lines, index)
                    cleaned = clean_party_name(name)
                    if cleaned and not _looks_like_label_noise(cleaned):
                        key = f"{current}_name"
                        if not result.get(key).is_present:
                            result.set(key, FieldValue(
                                value=cleaned,
                                confidence=confidence,
                                source=f"label:{match.label}",
                                raw_text=lines[index],
                                page=1,
                            ))

                elif match.field == "tin":
                    tin = parse_tin(match.value) or parse_tin(lines[index])
                    confidence = CONF_LABEL_SAME_LINE
                    source = f"label:{match.label}"
                    if not tin:
                        tin = parse_tin(match.value, repair=True)
                        if tin:
                            confidence = CONF_REPAIRED
                            source = f"label:{match.label}+ocr_repair"
                    if not tin:
                        continue
                    party = party_by_match.get(id(match))
                    party = party or ("vendor" if not result.get("vendor_tin").is_present else "buyer")
                    key = f"{party}_tin"
                    if not result.get(key).is_present:
                        result.set(key, FieldValue(
                            value=tin,
                            confidence=confidence,
                            source=source,
                            raw_text=lines[index],
                            page=1,
                        ))

                elif match.field == "address" and (current or party_columns):
                    party = party_by_match.get(id(match)) or current
                    if party is None:
                        continue
                    key = f"{party}_address"
                    address, confidence = self._value_or_next_line(match, lines, index)
                    if address and not result.get(key).is_present:
                        result.set(key, FieldValue(
                            value=re.sub(r"\s+", " ", address).strip(),
                            confidence=confidence,
                            source=f"label:{match.label}",
                            raw_text=lines[index],
                            page=1,
                        ))

        self._fallback_party_names(lines, result)

    @staticmethod
    def _bind_parties(
        matches: list[LabelMatch],
        party_columns: list[tuple[int, str]],
        current: str | None,
    ) -> dict[int, str]:
        """Decide which counterparty each TIN / address label on a line describes.

        When a line carries exactly as many labels of a kind as there are
        counterparty columns, bind them left-to-right by ordinal. That survives
        ragged whitespace, which raw offsets do not: OCR and PDF text extraction
        both reflow the gap between two side-by-side columns unpredictably.
        """
        binding: dict[int, str] = {}
        for field_name in ("tin", "address"):
            group = [match for match in matches if match.field == field_name]
            if not group:
                continue
            if len(party_columns) > 1 and len(group) == len(party_columns):
                for match, (_, party) in zip(group, party_columns, strict=True):
                    binding[id(match)] = party
            else:
                for match in group:
                    party = _party_for_position(match.start, party_columns, current)
                    if party:
                        binding[id(match)] = party
        return binding

    def _fallback_party_names(self, lines: list[str], result: ExtractionResult) -> None:
        """Unlabelled counterparty lines: fall back to legal-form detection.

        Some vendors print `"OLTIN VODIY SAVDO" MChJ` on its own line with no
        `Yetkazib beruvchi:` prefix at all.
        """
        if result.get("vendor_name").is_present:
            return
        for line in lines[:15]:
            folded = fold(line)
            words = {word.strip('.,:;()"«»') for word in folded.split()}
            if words & set(lexicon.LEGAL_FORMS):
                cleaned = clean_party_name(line)
                if cleaned and len(cleaned) > 3:
                    result.set("vendor_name", FieldValue(
                        value=cleaned,
                        confidence=CONF_PATTERN,
                        source="pattern:legal_form",
                        raw_text=line,
                        page=1,
                    ))
                    return

    # -- header fields ------------------------------------------------------

    def _extract_header(
        self, lines: list[str], line_matches: list[list[LabelMatch]], result: ExtractionResult
    ) -> None:
        for index, matches in enumerate(line_matches):
            for match in matches:
                if match.field == "invoice_number" and not result.get("invoice_number").is_present:
                    number = self._parse_invoice_number(match.value)
                    if number:
                        result.set("invoice_number", FieldValue(
                            value=number,
                            confidence=CONF_LABEL_SAME_LINE,
                            source=f"label:{match.label}",
                            raw_text=lines[index],
                            page=1,
                        ))

                elif match.field == "date" and not result.get("invoice_date").is_present:
                    parsed = parse_date(match.value)
                    if parsed is None and not match.value:
                        parsed = parse_date(_next_line(lines, index))
                    if parsed:
                        result.set("invoice_date", FieldValue(
                            value=parsed,
                            confidence=CONF_LABEL_SAME_LINE,
                            source=f"label:{match.label}",
                            raw_text=lines[index],
                            page=1,
                        ))

                elif match.field == "contract" and not result.get("contract_number").is_present:
                    number = self._parse_invoice_number(match.value)
                    if number:
                        result.set("contract_number", FieldValue(
                            value=number,
                            confidence=CONF_LABEL_SAME_LINE,
                            source=f"label:{match.label}",
                            raw_text=lines[index],
                            page=1,
                        ))
                    contract_date = parse_date(match.value)
                    if contract_date and not result.get("contract_date").is_present:
                        result.set("contract_date", FieldValue(
                            value=contract_date,
                            confidence=CONF_PATTERN,
                            source=f"label:{match.label}",
                            raw_text=lines[index],
                            page=1,
                        ))

        # Header-less documents: take the first plausible date near the top.
        if not result.get("invoice_date").is_present:
            for line in lines[:12]:
                parsed = parse_date(line)
                if parsed:
                    result.set("invoice_date", FieldValue(
                        value=parsed,
                        confidence=CONF_PATTERN,
                        source="pattern:first_date",
                        raw_text=line,
                        page=1,
                    ))
                    break

    @staticmethod
    def _parse_invoice_number(value: str) -> str | None:
        if not value:
            return None
        cleaned = value.strip().strip(_VALUE_SEPARATORS)
        match = _INVOICE_NUMBER.match(cleaned)
        if not match:
            return None
        number = match.group(1).strip(".,;:")
        # A bare date is not a document number.
        if parse_date(number) is not None:
            return None
        return number or None

    def _value_or_next_line(
        self, match: LabelMatch, lines: list[str], index: int
    ) -> tuple[str | None, float]:
        if match.value:
            return match.value, CONF_LABEL_SAME_LINE
        following = _next_line(lines, index)
        if following and not scan_labels(following):
            return following.strip(), CONF_LABEL_NEXT_LINE
        return None, 0.0

    # -- line items ---------------------------------------------------------

    def _extract_line_items(
        self,
        lines: list[str],
        line_matches: list[list[LabelMatch]],
        result: ExtractionResult,
        context: ExtractionContext,
    ) -> None:
        header_index, column_map, header_width = self._find_table_header(lines)
        if header_index is None:
            return

        items: list[LineItem] = []
        for index in range(header_index + 1, len(lines)):
            line = lines[index]
            if self._is_totals_line(line_matches[index]):
                break
            item = self._parse_row(line, column_map, len(items) + 1, header_width)
            if item is not None:
                items.append(item)
            elif items and not _has_numbers(line):
                # Blank-ish separator after at least one row: table is over.
                break

        result.line_items = items

    def _find_table_header(self, lines: list[str]) -> tuple[int | None, dict[int, str], int]:
        """Locate the column header row and map cell position to column type."""
        for index, line in enumerate(lines):
            cells = split_row(line)
            if len(cells) < 3:
                continue
            column_map: dict[int, str] = {}
            for position, cell in enumerate(cells):
                column = _classify_column(cell)
                if column:
                    column_map[position] = column
            named = set(column_map.values())
            if len({"description", "quantity", "unit_price", "amount"} & named) >= 2:
                return index, column_map, len(cells)
        return None, {}, 0

    @staticmethod
    def _is_totals_line(matches: list[LabelMatch]) -> bool:
        return any(match.field in ("subtotal", "total_with_vat", "vat") for match in matches)

    def _parse_row(
        self,
        line: str,
        column_map: dict[int, str],
        fallback_index: int,
        header_width: int,
    ) -> LineItem | None:
        cells = split_row(line)
        if len(cells) < 2:
            return None

        values: dict[str, str] = {}
        # Positional mapping is only trustworthy when the row has the same cell
        # count as the header; a wrapped description shifts every later column.
        if column_map and len(cells) == header_width:
            for position, cell in enumerate(cells):
                column = column_map.get(position)
                if column:
                    values[column] = cell

        if not values or "amount" not in values:
            values = _map_cells_heuristically(cells)
        if not values:
            return None

        description = values.get("description")
        amount = parse_amount(values.get("amount"))
        quantity = parse_amount(values.get("quantity"))
        unit_price = parse_amount(values.get("unit_price"))

        if amount is None and unit_price is None:
            return None
        if not description or not any(char.isalpha() for char in description):
            return None

        confidence = CONF_TABLE_ROW
        if quantity is not None and unit_price is not None and amount is not None:
            expected = quantity * unit_price
            if amount != 0 and abs(expected - amount) <= abs(amount) * Decimal("0.01"):
                confidence = CONF_TABLE_ROW_CONSISTENT
            else:
                confidence = 0.70

        index_value = parse_amount(values.get("index"))
        return LineItem(
            index=int(index_value) if index_value is not None else fallback_index,
            description=re.sub(r"\s+", " ", description).strip(),
            unit=values.get("unit"),
            quantity=quantity,
            unit_price=unit_price,
            amount=amount,
            vat_rate=parse_amount(values.get("vat_rate")),
            vat_amount=parse_amount(values.get("vat_amount")),
            confidence=confidence,
            raw_text=line,
        )

    # -- totals -------------------------------------------------------------

    def _extract_totals(
        self,
        lines: list[str],
        line_matches: list[list[LabelMatch]],
        result: ExtractionResult,
        context: ExtractionContext,
    ) -> None:
        for index, matches in enumerate(line_matches):
            for match in matches:
                if match.field not in ("subtotal", "total_with_vat", "vat"):
                    continue
                key = {
                    "subtotal": "subtotal",
                    "total_with_vat": "total_amount",
                    "vat": "vat_amount",
                }[match.field]

                value_text = match.value
                if match.field == "vat":
                    # `QQS (12%): 74 814 000,00` — record the rate, then take it
                    # out of the string so 12 cannot be read as the VAT amount.
                    percent = _PERCENT.search(value_text or lines[index])
                    if percent:
                        if not result.get("vat_rate").is_present:
                            result.set("vat_rate", FieldValue(
                                value=parse_amount(percent.group(1)),
                                confidence=CONF_LABEL_SAME_LINE,
                                source=f"label:{match.label}",
                                raw_text=lines[index],
                                page=1,
                            ))
                        value_text = (value_text or "").replace(percent.group(0), " ")

                amount = parse_amount(value_text)
                confidence = CONF_LABEL_SAME_LINE
                source = f"label:{match.label}"
                if amount is None:
                    amount = _last_number(lines[index])
                if amount is None:
                    # OCR turned digits into letters ("1 25O 000,OO"). Recover the
                    # number, but hand it to the reviewer rather than trusting it.
                    amount = parse_amount(value_text, repair=True) or _last_number(
                        lines[index], repair=True
                    )
                    if amount is not None:
                        confidence = CONF_REPAIRED
                        source = f"label:{match.label}+ocr_repair"
                if amount is None or result.get(key).is_present:
                    continue
                result.set(key, FieldValue(
                    value=amount,
                    confidence=confidence,
                    source=source,
                    raw_text=lines[index],
                    page=1,
                ))

    def _apply_currency(
        self, lines: list[str], result: ExtractionResult, context: ExtractionContext
    ) -> None:
        haystack = "\n".join(lines[-15:]) if len(lines) > 15 else "\n".join(lines)
        currency = parse_currency(haystack, default="")
        if not currency:
            currency = parse_currency("\n".join(lines), default=context.default_currency)
            confidence = CONF_PATTERN
        else:
            confidence = 0.90
        result.set("currency", FieldValue(
            value=currency,
            confidence=confidence,
            source="pattern:currency",
            page=1,
        ))

    def _reconcile_totals(self, result: ExtractionResult, context: ExtractionContext) -> None:
        """Fill whichever of subtotal / VAT / total is missing from the other two."""
        subtotal = _decimal_of(result.get("subtotal"))
        vat = _decimal_of(result.get("vat_amount"))
        total = _decimal_of(result.get("total_amount"))

        if subtotal is None and result.line_items:
            amounts = [item.amount for item in result.line_items if item.amount is not None]
            if amounts:
                subtotal = sum(amounts, Decimal("0"))
                result.set("subtotal", FieldValue(
                    value=subtotal,
                    confidence=CONF_DERIVED,
                    source="derived:sum(line_items)",
                ))

        if total is None and subtotal is not None and vat is not None:
            result.set("total_amount", FieldValue(
                value=subtotal + vat,
                confidence=CONF_DERIVED,
                source="derived:subtotal+vat",
            ))
        elif vat is None and subtotal is not None and total is not None:
            result.set("vat_amount", FieldValue(
                value=total - subtotal,
                confidence=CONF_DERIVED,
                source="derived:total-subtotal",
            ))
        elif subtotal is None and total is not None and vat is not None:
            result.set("subtotal", FieldValue(
                value=total - vat,
                confidence=CONF_DERIVED,
                source="derived:total-vat",
            ))

        # Last resort: a single unlabelled grand total equal to the item sum.
        if not result.get("total_amount").is_present and subtotal is not None:
            rate = Decimal(str(context.vat_rate_percent)) / Decimal("100")
            result.set("total_amount", FieldValue(
                value=(subtotal * (1 + rate)).quantize(Decimal("0.01")),
                confidence=0.45,
                source=f"derived:subtotal*(1+{context.vat_rate_percent}%)",
            ))


# --- helpers ----------------------------------------------------------------

def detect_document_type(lines: list[str]) -> str:
    """Classify the document from its title markers (top of page wins)."""
    haystack = fold("\n".join(lines[:20]))
    best: tuple[int, str] | None = None
    for doc_type, markers in lexicon.DOCUMENT_TYPE_MARKERS.items():
        for marker in markers:
            position = haystack.find(fold(marker))
            if position != -1 and (best is None or position < best[0]):
                best = (position, doc_type)
    return best[1] if best else "unknown"


def _classify_column(cell: str) -> str | None:
    """Identify which table column a header cell names.

    Matching is tiered deliberately. Short labels like `№` or `no` are only
    trusted on an exact match — a substring rule lets a one-letter label match
    any cell, which silently turns every row of the document into a table.
    """
    folded = fold(cell).strip(" .:|()№")
    if not folded:
        folded = fold(cell).strip(" .:|")
    if not folded:
        return None

    for column, labels in lexicon.COLUMN_LABELS.items():
        for label in labels:
            if folded == fold(label):
                return column

    for column, labels in lexicon.COLUMN_LABELS.items():
        for label in labels:
            normalized = fold(label)
            if len(normalized) >= 3 and folded.startswith(normalized):
                remainder = folded[len(normalized):]
                if not remainder or not remainder[0].isalnum():
                    return column

    for column, labels in lexicon.COLUMN_LABELS.items():
        for label in labels:
            normalized = fold(label)
            if len(normalized) >= 6 and normalized in folded:
                return column
    return None


def _map_cells_heuristically(cells: list[str]) -> dict[str, str]:
    """Map table cells to columns without a usable header row.

    Layout of essentially every invoice in this market:
    `№ | description | unit | quantity | unit price | amount`, with the trailing
    numeric columns being the reliable part.
    """
    values: dict[str, str] = {}
    working = list(cells)

    if working and parse_amount(working[0]) is not None and len(working[0].strip()) <= 3:
        values["index"] = working.pop(0)

    numeric_positions = [
        position for position, cell in enumerate(working) if parse_amount(cell) is not None
    ]
    text_positions = [position for position in range(len(working)) if position not in numeric_positions]
    if not text_positions:
        return {}

    description_position = text_positions[0]
    values["description"] = working[description_position]

    for position in text_positions[1:]:
        if fold(working[position]).strip(". ") in {fold(unit) for unit in lexicon.UNIT_TOKENS}:
            values["unit"] = working[position]
            break

    trailing = [position for position in numeric_positions if position > description_position]
    numbers = [working[position] for position in trailing]
    if len(numbers) >= 3:
        values["quantity"], values["unit_price"], values["amount"] = numbers[0], numbers[1], numbers[-1]
    elif len(numbers) == 2:
        first, second = parse_amount(numbers[0]), parse_amount(numbers[1])
        # Two numbers are quantity+amount when the amount is the larger one.
        if first is not None and second is not None and abs(second) >= abs(first):
            values["quantity"], values["amount"] = numbers[0], numbers[1]
        else:
            values["unit_price"], values["amount"] = numbers[0], numbers[1]
    elif len(numbers) == 1:
        values["amount"] = numbers[0]
    else:
        return {}
    return values


def _party_for_position(
    position: int, party_columns: list[tuple[int, str]], current: str | None
) -> str | None:
    """Which counterparty owns a label at this horizontal offset.

    With a single-column header there is only ever one candidate, so this falls
    back to the running `current` party. With two columns it picks the party
    whose block starts at or before this offset — the one directly above it.
    """
    if len(party_columns) <= 1:
        return current
    chosen: str | None = None
    for start, party in party_columns:
        if start <= position:
            chosen = party
        else:
            break
    return chosen or party_columns[0][1]


def _looks_like_label_noise(value: str) -> bool:
    folded = fold(value)
    return folded in {label for _, label in _LABEL_INDEX} or len(folded) < 2


def _next_line(lines: list[str], index: int) -> str | None:
    return lines[index + 1] if index + 1 < len(lines) else None


def _has_numbers(line: str) -> bool:
    return any(char.isdigit() for char in line)


def _last_number(line: str, skip: set[Decimal] | None = None, repair: bool = False) -> Decimal | None:
    tokens = merge_numeric_tokens(line.split())
    for token in reversed(tokens):
        value = parse_amount(token, repair=repair)
        if value is None:
            continue
        if skip and value in skip:
            continue
        # A bare percentage is a rate, not a money amount.
        if token.endswith("%"):
            continue
        return value
    return None


def _decimal_of(entry: FieldValue) -> Decimal | None:
    if not entry.is_present:
        return None
    if isinstance(entry.value, Decimal):
        return entry.value
    return parse_amount(str(entry.value))


def build_field_payload(result: ExtractionResult) -> dict[str, Any]:
    """Serialise for storage, dropping fields outside the MVP schema."""
    from app.services.extract.base import INVOICE_FIELDS  # noqa: PLC0415

    allowed = set(INVOICE_FIELDS) | {"vat_rate"}
    return {name: entry.to_dict() for name, entry in result.fields.items() if name in allowed}
