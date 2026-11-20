"""Rule-based extraction tests across scripts and layouts."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from app.services.extract.base import ExtractionContext
from app.services.extract.rules import (
    RuleBasedExtractor,
    detect_document_type,
    merge_numeric_tokens,
    scan_labels,
    split_row,
)
from app.testing.corpus import LAYOUTS, STYLES, random_invoice, render_text

UZ_LATIN_INVOICE = """\
HISOB-FAKTURA
Raqami: 1245
Sana: 12.03.2026

Yetkazib beruvchi: "OLTIN VODIY SAVDO" MChJ
STIR: 302145879
Manzil: Toshkent sh., Chilonzor tumani, Bunyodkor ko'chasi 12

Xaridor: "AGROMASH SERVIS" MChJ
STIR: 205673412

Shartnoma: № 45 dan 01.02.2026

№     Tovar (xizmat) nomi     O'lchov birligi   Soni    Narxi           Summa
1     Sement M-400            tonna             12      1 250 000,00    15 000 000,00
2     Armatura 12 mm          tonna             3,5     8 400 000,00    29 400 000,00

Jami: 44 400 000,00 so'm
QQS (12%): 5 328 000,00 so'm
Jami QQS bilan: 49 728 000,00 so'm
"""

RUSSIAN_INVOICE = """\
СЧЁТ-ФАКТУРА № 778 от 05.04.2026
Поставщик: ООО "НАВРУЗ ЛОГИСТИКА"
ИНН: 301234567
Покупатель: ООО "МЕГА БИЛД"
ИНН: 205112233

№   Наименование товара   Ед.изм   Кол-во   Цена            Сумма
1   Транспортные услуги   услуга   4        2 500 000,00    10 000 000,00

Итого: 10 000 000,00 сум
НДС 12%: 1 200 000,00 сум
Всего к оплате: 11 200 000,00 сум
"""


@pytest.fixture()
def extractor() -> RuleBasedExtractor:
    return RuleBasedExtractor()


def test_extracts_uzbek_latin_invoice(extractor: RuleBasedExtractor) -> None:
    result = extractor.extract(UZ_LATIN_INVOICE, ExtractionContext())

    assert result.value("invoice_number") == "1245"
    assert result.value("invoice_date") == dt.date(2026, 3, 12)
    assert result.value("vendor_name") == '"OLTIN VODIY SAVDO" MChJ'
    assert result.value("vendor_tin") == "302145879"
    assert result.value("buyer_name") == '"AGROMASH SERVIS" MChJ'
    assert result.value("buyer_tin") == "205673412"
    assert result.value("subtotal") == Decimal("44400000.00")
    assert result.value("vat_amount") == Decimal("5328000.00")
    assert result.value("total_amount") == Decimal("49728000.00")
    assert result.value("currency") == "UZS"


def test_extracts_line_items_with_units(extractor: RuleBasedExtractor) -> None:
    result = extractor.extract(UZ_LATIN_INVOICE, ExtractionContext())

    assert len(result.line_items) == 2
    first, second = result.line_items
    assert first.description == "Sement M-400"
    assert first.unit == "tonna"
    assert first.quantity == Decimal("12")
    assert first.unit_price == Decimal("1250000.00")
    assert first.amount == Decimal("15000000.00")
    # quantity x price == amount, so the row is trusted more.
    assert first.confidence >= 0.95
    assert second.quantity == Decimal("3.5")


def test_extracts_russian_invoice(extractor: RuleBasedExtractor) -> None:
    result = extractor.extract(RUSSIAN_INVOICE, ExtractionContext())

    assert result.value("invoice_number") == "778"
    assert result.value("invoice_date") == dt.date(2026, 4, 5)
    assert result.value("vendor_tin") == "301234567"
    assert result.value("buyer_tin") == "205112233"
    assert result.value("total_amount") == Decimal("11200000.00")


def test_vat_percentage_is_not_mistaken_for_vat_amount(extractor: RuleBasedExtractor) -> None:
    """`QQS (12%): 5 328 000,00` — 12 is the rate, not the tax."""
    result = extractor.extract(UZ_LATIN_INVOICE, ExtractionContext())
    assert result.value("vat_amount") == Decimal("5328000.00")
    assert result.value("vat_rate") == Decimal("12")


def test_grand_total_wins_over_subtotal_label(extractor: RuleBasedExtractor) -> None:
    """`Jami QQS bilan` must not be matched by the shorter `Jami`."""
    result = extractor.extract(UZ_LATIN_INVOICE, ExtractionContext())
    assert result.value("subtotal") == Decimal("44400000.00")
    assert result.value("total_amount") == Decimal("49728000.00")


def test_side_by_side_counterparties_bind_correctly(extractor: RuleBasedExtractor) -> None:
    """Two-column headers put both parties' STIRs on one line."""
    text = (
        'Yetkazib beruvchi: "OLTIN VODIY" MChJ      Xaridor: "AGROMASH" MChJ\n'
        "STIR: 302145879      STIR: 205673412\n"
        "Jami: 1 000 000,00\n"
    )
    result = extractor.extract(text, ExtractionContext())
    assert result.value("vendor_tin") == "302145879"
    assert result.value("buyer_tin") == "205673412"


def test_missing_total_is_derived_from_subtotal_and_vat(extractor: RuleBasedExtractor) -> None:
    text = "HISOB-FAKTURA\nRaqami: 5\nSana: 01.01.2026\nJami: 1 000 000,00\nQQS (12%): 120 000,00\n"
    result = extractor.extract(text, ExtractionContext())
    assert result.value("total_amount") == Decimal("1120000.00")
    # A derived value is explicitly less trusted than a printed one.
    assert result.get("total_amount").confidence < 0.85
    assert "derived" in result.get("total_amount").source


def test_detect_document_type() -> None:
    assert detect_document_type(["HISOB-FAKTURA", "Raqami: 1"]) == "invoice"
    assert detect_document_type(["СЧЁТ-ФАКТУРА № 5"]) == "invoice"
    assert detect_document_type(["ТОВАРНО-ТРАНСПОРТНАЯ НАКЛАДНАЯ"]) == "waybill"
    assert detect_document_type(["SHARTNOMA № 12"]) == "contract"
    assert detect_document_type(["random text"]) == "unknown"


def test_merge_numeric_tokens_rejoins_space_separated_thousands() -> None:
    assert merge_numeric_tokens(["12", "1", "250", "000,00"]) == ["12", "1 250 000,00"]
    assert merge_numeric_tokens(["3,5", "8", "400", "000,00"]) == ["3,5", "8 400 000,00"]
    # A two-digit token is not a thousands group and must stay separate.
    assert merge_numeric_tokens(["5", "12"]) == ["5", "12"]


def test_split_row_handles_delimiters() -> None:
    assert split_row("1 | Sement | tonna | 12") == ["1", "Sement", "tonna", "12"]
    assert split_row("1    Sement M-400    tonna    12") == ["1", "Sement M-400", "tonna", "12"]


def test_scan_labels_finds_repeated_labels_on_one_line() -> None:
    matches = scan_labels("STIR: 302145879      STIR: 205673412")
    tins = [match for match in matches if match.field == "tin"]
    assert len(tins) == 2
    assert tins[0].value.startswith("302145879")
    assert tins[1].value.startswith("205673412")


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("layout", LAYOUTS)
def test_extracts_every_style_and_layout(style: str, layout: str) -> None:
    """Regression guard across the full matrix of scripts and layouts."""
    extractor = RuleBasedExtractor()
    for offset in range(4):
        spec = random_invoice(seed=500 + offset, style=style, layout=layout)
        result = extractor.extract(render_text(spec, seed=500 + offset), ExtractionContext())
        expected = spec.expected_fields()

        assert str(result.value("invoice_number")) == expected["invoice_number"]
        assert str(result.value("invoice_date")) == expected["invoice_date"]
        assert str(result.value("vendor_tin")) == expected["vendor_tin"]
        assert str(result.value("buyer_tin")) == expected["buyer_tin"]
        assert Decimal(str(result.value("total_amount"))) == Decimal(expected["total_amount"])


def test_garbage_input_does_not_crash(extractor: RuleBasedExtractor) -> None:
    for text in ["", "   \n\n  ", "!!!???", "\x00\x01binary", "a" * 5000]:
        result = extractor.extract(text, ExtractionContext())
        assert result.overall_confidence >= 0.0
