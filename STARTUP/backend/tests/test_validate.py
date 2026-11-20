"""Validation tests.

These assert the safety property the product is sold on: when a value is wrong,
its confidence must drop below the review threshold so a human sees it. A test
here failing means silent errors reaching 1C.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from app.services.extract.base import ExtractionResult, FieldValue, LineItem
from app.services.validate import validate_extraction

THRESHOLD = 0.85


def build_result(**fields) -> ExtractionResult:
    result = ExtractionResult()
    for name, value in fields.items():
        result.set(name, FieldValue(value=value, confidence=0.95, source="label:test"))
    return result


def test_balanced_invoice_passes() -> None:
    result = build_result(
        invoice_number="1245",
        invoice_date=dt.date(2026, 3, 12),
        vendor_name='"OLTIN VODIY" MChJ',
        vendor_tin="302145879",
        subtotal=Decimal("1000000.00"),
        vat_amount=Decimal("120000.00"),
        total_amount=Decimal("1120000.00"),
    )
    report = validate_extraction(result, today=dt.date(2026, 4, 1))

    assert report.errors == []
    assert report.checks["totals_balance"] is True
    assert report.checks["vat_rate_plausible"] is True
    assert result.get("total_amount").confidence >= THRESHOLD


def test_unbalanced_totals_flag_all_three_amounts() -> None:
    """OCR damage to any one amount breaks the sum; all three go to review."""
    result = build_result(
        invoice_number="1", invoice_date=dt.date(2026, 3, 12),
        vendor_name="X", vendor_tin="302145879",
        subtotal=Decimal("1000000.00"),
        vat_amount=Decimal("120000.00"),
        total_amount=Decimal("9120000.00"),   # a digit was misread
    )
    report = validate_extraction(result, today=dt.date(2026, 4, 1))

    assert any(error["code"] == "totals_do_not_balance" for error in report.errors)
    for field in ("subtotal", "vat_amount", "total_amount"):
        assert result.get(field).confidence < THRESHOLD


def test_invalid_tin_is_flagged() -> None:
    result = build_result(
        invoice_number="1", invoice_date=dt.date(2026, 3, 12),
        vendor_name="X", vendor_tin="30214",
        total_amount=Decimal("100.00"),
    )
    report = validate_extraction(result, today=dt.date(2026, 4, 1))

    assert any(error["code"] == "invalid_tin" for error in report.errors)
    assert result.get("vendor_tin").confidence < THRESHOLD


def test_identical_counterparty_tins_are_flagged() -> None:
    """A company does not invoice itself: one label bound to the wrong block."""
    result = build_result(
        invoice_number="1", invoice_date=dt.date(2026, 3, 12),
        vendor_name="X", vendor_tin="302145879", buyer_tin="302145879",
        total_amount=Decimal("100.00"),
    )
    report = validate_extraction(result, today=dt.date(2026, 4, 1))

    assert any(error["code"] == "identical_counterparty_tins" for error in report.errors)
    assert result.get("vendor_tin").confidence < THRESHOLD
    assert result.get("buyer_tin").confidence < THRESHOLD


def test_missing_required_fields_reported() -> None:
    result = build_result(invoice_number="1")
    report = validate_extraction(result, today=dt.date(2026, 4, 1))

    codes = {error["code"] for error in report.errors}
    assert "missing_required_fields" in codes
    assert report.checks["required_fields_present"] is False


def test_line_items_that_do_not_sum_are_warned() -> None:
    result = build_result(
        invoice_number="1", invoice_date=dt.date(2026, 3, 12),
        vendor_name="X", vendor_tin="302145879",
        subtotal=Decimal("1000000.00"),
        vat_amount=Decimal("120000.00"),
        total_amount=Decimal("1120000.00"),
    )
    result.line_items = [
        LineItem(index=1, description="Sement", amount=Decimal("400000.00"), confidence=0.9),
        LineItem(index=2, description="Armatura", amount=Decimal("300000.00"), confidence=0.9),
    ]
    report = validate_extraction(result, today=dt.date(2026, 4, 1))

    assert any(warning["code"] == "line_items_do_not_sum" for warning in report.warnings)
    assert result.get("subtotal").confidence < THRESHOLD


def test_unexpected_vat_rate_is_warned_not_rejected() -> None:
    """Zero-rated and exempt supplies are legal, so this is a warning."""
    result = build_result(
        invoice_number="1", invoice_date=dt.date(2026, 3, 12),
        vendor_name="X", vendor_tin="302145879",
        subtotal=Decimal("1000000.00"),
        vat_amount=Decimal("200000.00"),      # 20%, not the standard 12%
        total_amount=Decimal("1200000.00"),
    )
    report = validate_extraction(result, today=dt.date(2026, 4, 1))

    assert any(warning["code"] == "unexpected_vat_rate" for warning in report.warnings)
    assert not any(error["code"] == "unexpected_vat_rate" for error in report.errors)


def test_future_date_is_flagged() -> None:
    result = build_result(
        invoice_number="1", invoice_date=dt.date(2027, 12, 31),
        vendor_name="X", vendor_tin="302145879",
        total_amount=Decimal("100.00"),
    )
    report = validate_extraction(result, today=dt.date(2026, 4, 1))

    assert any(warning["code"] == "implausible_date" for warning in report.warnings)
    assert result.get("invoice_date").confidence < THRESHOLD


def test_intraword_script_mixing_is_flagged_as_ocr_damage() -> None:
    """`СЕРВИC` with a Latin C looks correct on screen but is a different string."""
    result = build_result(
        invoice_number="1", invoice_date=dt.date(2026, 3, 12),
        vendor_name='ООО "АГРОМАШ CЕРВИС"',   # Latin C inside a Cyrillic word
        vendor_tin="302145879",
        total_amount=Decimal("100.00"),
    )
    report = validate_extraction(result, today=dt.date(2026, 4, 1))

    assert any(w["code"] == "possible_ocr_script_corruption" for w in report.warnings)
    assert result.get("vendor_name").confidence < THRESHOLD


def test_clean_mixed_script_document_is_not_flagged() -> None:
    """Mixing scripts *between* words is normal here and must not be penalised."""
    result = build_result(
        invoice_number="1", invoice_date=dt.date(2026, 3, 12),
        vendor_name='ООО "OLTIN VODIY SAVDO"',   # whole words, each one script
        vendor_tin="302145879",
        total_amount=Decimal("100.00"),
    )
    report = validate_extraction(result, today=dt.date(2026, 4, 1))

    assert report.checks["no_script_corruption"] is True
    assert result.get("vendor_name").confidence >= THRESHOLD


def test_negative_total_is_an_error() -> None:
    result = build_result(
        invoice_number="1", invoice_date=dt.date(2026, 3, 12),
        vendor_name="X", vendor_tin="302145879",
        total_amount=Decimal("-500.00"),
    )
    report = validate_extraction(result, today=dt.date(2026, 4, 1))

    assert any(error["code"] == "negative_total" for error in report.errors)
