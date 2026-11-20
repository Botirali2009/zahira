"""Cross-field validation and confidence adjustment.

The extractor reports how confidently it *found* a value. That is not the same
as whether the value is *right*: a label match is just as confident when OCR
mangled the digits after the label. This module is the second opinion — it
checks the numbers against each other and against the document's own arithmetic,
and pushes confidence down where the evidence disagrees.

The metric this exists to protect is the silent error rate: a wrong value that
still looks confident is the one that reaches a tax filing without a human
looking at it. A flagged wrong value costs the accountant ten seconds; a silent
one costs them a penalty of $200-$2,000 (deep-dive §1).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation
from typing import Any

from app.services.extract.base import REQUIRED_FIELDS, ExtractionResult, FieldValue
from app.services.extract.parsers import TIN_LENGTH, is_valid_tin
from app.services.script_detect import CONFUSABLE_CHARS, classify_char

# Money tolerance. UZS invoices are rounded to the tiyin, and 1C accepts a
# one-unit rounding difference, so anything inside this is not a discrepancy.
AMOUNT_TOLERANCE = Decimal("1.00")
# Relative tolerance for the VAT-rate check: vendors round VAT per line item,
# which drifts from a whole-invoice calculation by small amounts.
VAT_RELATIVE_TOLERANCE = Decimal("0.005")

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"

# Confidence ceilings applied when a check fails. Each is below the 0.85 review
# threshold, so a failing check always puts the field in front of a human.
CEILING_HARD = 0.35
CEILING_SOFT = 0.60


class ValidationReport:
    def __init__(self) -> None:
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.checks: dict[str, bool] = {}

    def add(self, severity: str, code: str, message: str, fields: list[str]) -> None:
        entry = {"code": code, "message": message, "fields": fields}
        if severity == SEVERITY_ERROR:
            self.errors.append(entry)
        else:
            self.warnings.append(entry)

    def to_dict(self) -> dict[str, Any]:
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "checks": self.checks,
            "is_valid": not self.errors,
        }


def _decimal(entry: FieldValue) -> Decimal | None:
    if not entry.is_present:
        return None
    try:
        return Decimal(str(entry.value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _cap(result: ExtractionResult, field: str, ceiling: float) -> None:
    entry = result.fields.get(field)
    if entry is not None and entry.confidence > ceiling:
        entry.confidence = ceiling


def validate_extraction(
    result: ExtractionResult,
    vat_rate_percent: float = 12.0,
    today: dt.date | None = None,
) -> ValidationReport:
    """Run every check, lowering confidence on the fields each one implicates."""
    report = ValidationReport()
    today = today or dt.date.today()

    _check_required(result, report)
    _check_tins(result, report)
    _check_totals_arithmetic(result, report)
    _check_line_item_sum(result, report)
    _check_vat_rate(result, report, vat_rate_percent)
    _check_date(result, report, today)
    _check_script_corruption(result, report)
    _check_amount_sanity(result, report)

    return report


def _check_required(result: ExtractionResult, report: ValidationReport) -> None:
    missing = [name for name in REQUIRED_FIELDS if not result.get(name).is_present]
    report.checks["required_fields_present"] = not missing
    if missing:
        report.add(
            SEVERITY_ERROR,
            "missing_required_fields",
            f"Required fields could not be extracted: {', '.join(missing)}",
            missing,
        )


def _check_tins(result: ExtractionResult, report: ValidationReport) -> None:
    vendor = result.get("vendor_tin")
    buyer = result.get("buyer_tin")
    if vendor.is_present and buyer.is_present and str(vendor.value) == str(buyer.value):
        # A company does not invoice itself. One of the two labels bound to the
        # wrong counterparty, and there is no way to tell which from here.
        report.checks["counterparties_distinct"] = False
        report.add(
            SEVERITY_ERROR,
            "identical_counterparty_tins",
            f"Supplier and buyer both show STIR {vendor.value}; "
            "one of them was read from the wrong block",
            ["vendor_tin", "buyer_tin"],
        )
        _cap(result, "vendor_tin", CEILING_SOFT)
        _cap(result, "buyer_tin", CEILING_SOFT)
    else:
        report.checks["counterparties_distinct"] = True

    for field in ("vendor_tin", "buyer_tin"):
        entry = result.fields.get(field)
        if entry is None or not entry.is_present:
            continue
        value = str(entry.value)
        valid = is_valid_tin(value)
        report.checks[f"{field}_format"] = valid
        if not valid:
            report.add(
                SEVERITY_ERROR,
                "invalid_tin",
                f"{field} '{value}' is not a {TIN_LENGTH}-digit STIR",
                [field],
            )
            _cap(result, field, CEILING_HARD)


def _check_totals_arithmetic(result: ExtractionResult, report: ValidationReport) -> None:
    """subtotal + VAT must equal the total. The single most useful check here.

    It is the one that catches OCR digit damage: a corrupted amount almost never
    still balances against the other two.
    """
    subtotal = _decimal(result.get("subtotal"))
    vat = _decimal(result.get("vat_amount"))
    total = _decimal(result.get("total_amount"))

    if subtotal is None or vat is None or total is None:
        report.checks["totals_balance"] = False
        return

    difference = abs(subtotal + vat - total)
    balanced = difference <= AMOUNT_TOLERANCE
    report.checks["totals_balance"] = balanced
    if not balanced:
        report.add(
            SEVERITY_ERROR,
            "totals_do_not_balance",
            f"subtotal ({subtotal}) + VAT ({vat}) = {subtotal + vat}, "
            f"but the document total is {total} (off by {difference})",
            ["subtotal", "vat_amount", "total_amount"],
        )
        for field in ("subtotal", "vat_amount", "total_amount"):
            # Any one of the three could be the damaged value, so all three go
            # to review rather than guessing which to trust.
            _cap(result, field, CEILING_SOFT)


def _check_line_item_sum(result: ExtractionResult, report: ValidationReport) -> None:
    if not result.line_items:
        report.checks["line_items_sum"] = False
        return
    amounts = [item.amount for item in result.line_items if item.amount is not None]
    if not amounts:
        report.checks["line_items_sum"] = False
        return

    line_total = sum((Decimal(str(amount)) for amount in amounts), Decimal("0"))
    subtotal = _decimal(result.get("subtotal"))
    if subtotal is None:
        report.checks["line_items_sum"] = False
        return

    difference = abs(line_total - subtotal)
    matches = difference <= AMOUNT_TOLERANCE
    report.checks["line_items_sum"] = matches
    if not matches:
        report.add(
            SEVERITY_WARNING,
            "line_items_do_not_sum",
            f"Line items total {line_total} but the invoice subtotal is {subtotal}",
            ["subtotal"],
        )
        _cap(result, "subtotal", CEILING_SOFT)
        for index, item in enumerate(result.line_items):
            if item.confidence > CEILING_SOFT:
                result.line_items[index].confidence = CEILING_SOFT


def _check_vat_rate(
    result: ExtractionResult, report: ValidationReport, vat_rate_percent: float
) -> None:
    subtotal = _decimal(result.get("subtotal"))
    vat = _decimal(result.get("vat_amount"))
    if subtotal is None or vat is None or subtotal == 0:
        report.checks["vat_rate_plausible"] = False
        return

    expected = subtotal * Decimal(str(vat_rate_percent)) / Decimal("100")
    tolerance = max(AMOUNT_TOLERANCE, abs(expected) * VAT_RELATIVE_TOLERANCE)
    plausible = abs(expected - vat) <= tolerance
    report.checks["vat_rate_plausible"] = plausible
    if not plausible:
        actual_rate = (vat / subtotal * 100).quantize(Decimal("0.01"))
        # Exempt and zero-rated supplies are legitimate, so this is a warning.
        severity = SEVERITY_WARNING if vat == 0 else SEVERITY_WARNING
        report.add(
            severity,
            "unexpected_vat_rate",
            f"VAT is {actual_rate}% of the subtotal, not the standard {vat_rate_percent}%",
            ["vat_amount"],
        )
        if vat != 0:
            _cap(result, "vat_amount", CEILING_SOFT)


def _check_date(result: ExtractionResult, report: ValidationReport, today: dt.date) -> None:
    entry = result.fields.get("invoice_date")
    if entry is None or not entry.is_present:
        report.checks["date_plausible"] = False
        return

    value = entry.value
    if isinstance(value, str):
        try:
            value = dt.date.fromisoformat(value)
        except ValueError:
            report.checks["date_plausible"] = False
            report.add(SEVERITY_ERROR, "unparseable_date",
                       f"Invoice date '{entry.value}' is not a valid date", ["invoice_date"])
            _cap(result, "invoice_date", CEILING_HARD)
            return
    if not isinstance(value, dt.date):
        return

    # Uzbek tax records are retained 5 years; anything older is a misread year.
    too_old = value < today - dt.timedelta(days=365 * 6)
    too_new = value > today + dt.timedelta(days=30)
    plausible = not (too_old or too_new)
    report.checks["date_plausible"] = plausible
    if not plausible:
        report.add(
            SEVERITY_WARNING,
            "implausible_date",
            f"Invoice date {value.isoformat()} is "
            + ("far in the past" if too_old else "in the future"),
            ["invoice_date"],
        )
        _cap(result, "invoice_date", CEILING_SOFT)


def _check_script_corruption(result: ExtractionResult, report: ValidationReport) -> None:
    """Flag words that mix Latin and Cyrillic letters internally.

    Real Uzbek documents mix scripts *between* words and blocks all the time —
    that is the market's defining trait. Mixing them *inside a single word* is
    almost always OCR substituting a homoglyph (`Пoставщик` with a Latin o), and
    it is invisible to a human proof-reading the value on screen, which makes it
    exactly the kind of error that needs to be flagged rather than trusted.
    """
    suspicious: list[str] = []
    for field in ("vendor_name", "buyer_name", "vendor_address", "buyer_address"):
        entry = result.fields.get(field)
        if entry is None or not entry.is_present:
            continue
        if _has_intraword_script_mix(str(entry.value)):
            suspicious.append(field)
            _cap(result, field, CEILING_SOFT)

    report.checks["no_script_corruption"] = not suspicious
    if suspicious:
        report.add(
            SEVERITY_WARNING,
            "possible_ocr_script_corruption",
            "Latin and Cyrillic characters appear inside the same word, which "
            "usually means OCR substituted a look-alike character: "
            + ", ".join(suspicious),
            suspicious,
        )


def _has_intraword_script_mix(text: str) -> bool:
    for word in text.split():
        letters = [char for char in word if char.isalpha()]
        if len(letters) < 3:
            continue
        scripts = {classify_char(char) for char in letters}
        if {"latin", "cyrillic"} <= scripts:
            # Only count it when the minority script is a known look-alike; a
            # genuine bilingual token like "1C:Buxgalteriya" is not corruption.
            minority = _minority_characters(letters)
            if any(char in CONFUSABLE_CHARS for char in minority):
                return True
    return False


def _minority_characters(letters: list[str]) -> list[str]:
    latin = [char for char in letters if classify_char(char) == "latin"]
    cyrillic = [char for char in letters if classify_char(char) == "cyrillic"]
    return latin if len(latin) <= len(cyrillic) else cyrillic


def _check_amount_sanity(result: ExtractionResult, report: ValidationReport) -> None:
    """Catch impossible money values (negative totals, absurd magnitudes)."""
    total = _decimal(result.get("total_amount"))
    if total is None:
        return
    if total < 0:
        report.add(SEVERITY_ERROR, "negative_total",
                   f"Invoice total is negative ({total})", ["total_amount"])
        _cap(result, "total_amount", CEILING_HARD)
    # 10 trillion UZS is ~$800M: a real invoice at that size does not exist in
    # this segment, so it is a misplaced separator or a doubled digit.
    if abs(total) > Decimal("10000000000000"):
        report.add(SEVERITY_WARNING, "implausible_magnitude",
                   f"Invoice total {total} is implausibly large", ["total_amount"])
        _cap(result, "total_amount", CEILING_SOFT)
