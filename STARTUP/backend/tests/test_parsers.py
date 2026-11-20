"""Parser tests.

These cover the number and date conventions that actually appear on Uzbek
invoices. A parser bug here becomes a wrong amount in a tax filing, so the cases
are written as a specification, not as coverage filler.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from app.services.extract.parsers import (
    clean_party_name,
    is_valid_tin,
    parse_amount,
    parse_currency,
    parse_date,
    parse_tin,
    repair_numeric_text,
)


@pytest.mark.parametrize(("raw", "expected"), [
    # Local convention: space groups, comma decimals.
    ("1 250 000,00", Decimal("1250000.00")),
    ("1 250 000,00", Decimal("1250000.00")),          # non-breaking spaces
    ("15 000 000,50", Decimal("15000000.50")),
    # English-locale exports.
    ("1,250,000.00", Decimal("1250000.00")),
    ("1250000", Decimal("1250000")),
    ("1'250'000", Decimal("1250000")),
    # Single separator with three trailing digits is grouping, not milli-units.
    ("1.250", Decimal("1250")),
    ("1,250", Decimal("1250")),
    # Two decimals stay decimals.
    ("1250,75", Decimal("1250.75")),
    ("1250.75", Decimal("1250.75")),
    # Amount embedded in a label line.
    ("Jami: 44 400 000,00 so'm", Decimal("44400000.00")),
    ("Итого: 44 400 000,00 сум", Decimal("44400000.00")),
    # Accounting negative.
    ("(1 250,00)", Decimal("-1250.00")),
    ("-500,25", Decimal("-500.25")),
])
def test_parse_amount(raw: str, expected: Decimal) -> None:
    assert parse_amount(raw) == expected


def test_parse_amount_does_not_treat_stray_parens_as_negative() -> None:
    """`QQS (12%): 74 814 000,00` must not come back negative."""
    assert parse_amount("(12%): 74 814 000,00") == Decimal("12")
    assert parse_amount("QQS (12%) 74 814 000,00".replace("(12%)", "")) == Decimal("74814000.00")


@pytest.mark.parametrize("raw", ["", "   ", None, "no digits here", "abc"])
def test_parse_amount_returns_none_when_unparseable(raw) -> None:
    assert parse_amount(raw) is None


@pytest.mark.parametrize(("raw", "expected"), [
    ("12.03.2026", dt.date(2026, 3, 12)),
    ("12/03/2026", dt.date(2026, 3, 12)),
    ("2026-03-12", dt.date(2026, 3, 12)),
    ("12.03.26", dt.date(2026, 3, 12)),
    ("Sana: 01.02.2026", dt.date(2026, 2, 1)),
    ("12 mart 2026", dt.date(2026, 3, 12)),
    ("12 марта 2026", dt.date(2026, 3, 12)),
    ("5 dekabr 2025", dt.date(2025, 12, 5)),
    ("31 декабря 2025", dt.date(2025, 12, 31)),
])
def test_parse_date(raw: str, expected: dt.date) -> None:
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw", ["32.13.2026", "not a date", "", None])
def test_parse_date_rejects_invalid(raw) -> None:
    assert parse_date(raw) is None


def test_parse_tin_extracts_nine_digits() -> None:
    assert parse_tin("STIR: 302145879") == "302145879"
    assert parse_tin("ИНН 205673412") == "205673412"
    assert parse_tin("302 145 879") == "302145879"


def test_parse_tin_ignores_wrong_length() -> None:
    assert parse_tin("12345") is None
    assert parse_tin("PINFL 30212345678901") is None


def test_parse_tin_repair_recovers_ocr_damage() -> None:
    """`3O2145879` with a letter O is a damaged TIN, not an unknown one."""
    assert parse_tin("STIR: 3O2145879") is None
    assert parse_tin("STIR: 3O2145879", repair=True) == "302145879"


def test_is_valid_tin() -> None:
    assert is_valid_tin("302145879")
    assert not is_valid_tin("30214587")
    assert not is_valid_tin("3021458X9")
    assert not is_valid_tin(None)


@pytest.mark.parametrize(("raw", "expected"), [
    ("1 25O 000,OO", "1 250 000,00"),
    ("l2 345", "12 345"),
    ("Sement M-400", None),        # a product name must never be "repaired"
    ("abcdef", None),
    ("7", None),                   # too few digits to be sure
])
def test_repair_numeric_text(raw: str, expected: str | None) -> None:
    assert repair_numeric_text(raw) == expected


def test_parse_currency() -> None:
    assert parse_currency("Jami: 100 000 so'm") == "UZS"
    assert parse_currency("Итого: 100 000 сум") == "UZS"
    assert parse_currency("Total: 1 000 USD") == "USD"
    assert parse_currency("no currency mentioned") == "UZS"


def test_clean_party_name_preserves_quotes_and_legal_form() -> None:
    """1C matches counterparties on the full legal name, quotes included."""
    assert clean_party_name('  "OLTIN VODIY" MChJ  ') == '"OLTIN VODIY" MChJ'
    assert clean_party_name('"AGROMASH" MChJ STIR:') == '"AGROMASH" MChJ'
    assert clean_party_name("   ") is None
