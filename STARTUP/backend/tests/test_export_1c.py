"""1C CommerceML export tests."""

from __future__ import annotations

import datetime as dt
import xml.etree.ElementTree as ET
from decimal import Decimal

import pytest

from app.services.export_1c import (
    ExportError,
    build_export_document,
    export_extractions,
    validate_commerceml,
)
from app.services.extract.base import ExtractionContext, ExtractionResult, FieldValue
from app.services.extract.rules import RuleBasedExtractor
from app.testing.corpus import random_invoice, render_text


def result_from_invoice(seed: int = 11) -> ExtractionResult:
    spec = random_invoice(seed=seed, style="uz_latin", layout="classic")
    return RuleBasedExtractor().extract(render_text(spec, seed=seed), ExtractionContext())


def test_export_produces_valid_commerceml() -> None:
    xml_text, problems = export_extractions([(result_from_invoice(), 1)])

    assert problems == []
    root = ET.fromstring(xml_text.encode("utf-8"))
    assert root.tag == "КоммерческаяИнформация"
    assert root.get("ВерсияСхемы") == "2.08"
    assert len(root.findall("Документ")) == 1


def test_export_includes_both_counterparties_with_roles() -> None:
    xml_text, _ = export_extractions([(result_from_invoice(), 1)])
    root = ET.fromstring(xml_text.encode("utf-8"))

    roles = [party.findtext("Роль") for party in root.iterfind("Документ/Контрагенты/Контрагент")]
    assert "Продавец" in roles
    assert "Покупатель" in roles


def test_identifiers_are_stable_across_exports() -> None:
    """1C keys records on Ид: re-exporting must update, not duplicate."""
    first, _ = export_extractions([(result_from_invoice(), 1)])
    second, _ = export_extractions([(result_from_invoice(), 1)])

    def ids(xml_text: str) -> list[str]:
        root = ET.fromstring(xml_text.encode("utf-8"))
        return [element.text for element in root.iter("Ид")]

    assert ids(first) == ids(second)


def test_units_map_to_okei_codes() -> None:
    """1C resolves units of measure by classifier code, not by the label text."""
    xml_text, _ = export_extractions([(result_from_invoice(), 1)])
    root = ET.fromstring(xml_text.encode("utf-8"))

    for unit in root.iter("БазоваяЕдиница"):
        assert unit.get("Код")
        assert unit.get("Код").isdigit()


def test_export_refuses_incomplete_extraction() -> None:
    """Better an explicit refusal than a file 1C rejects in front of a customer."""
    result = ExtractionResult()
    result.set("vendor_name", FieldValue(value="X", confidence=0.9))

    with pytest.raises(ExportError) as excinfo:
        build_export_document(result)

    message = str(excinfo.value)
    assert "invoice_number" in message and "total_amount" in message


def test_document_without_line_items_gets_a_summary_row() -> None:
    """1C will not post a document with no goods rows."""
    result = ExtractionResult()
    result.set("invoice_number", FieldValue(value="42", confidence=0.9))
    result.set("invoice_date", FieldValue(value=dt.date(2026, 3, 1), confidence=0.9))
    result.set("vendor_name", FieldValue(value='"OLTIN VODIY" MChJ', confidence=0.9))
    result.set("total_amount", FieldValue(value=Decimal("1120000.00"), confidence=0.9))

    document = build_export_document(result)
    assert len(document.line_items) == 1
    assert document.line_items[0].amount == Decimal("1120000.00")


def test_vat_is_marked_as_included_in_the_total() -> None:
    """Uzbek invoices print a VAT-inclusive grand total; 1C must not add it again."""
    xml_text, _ = export_extractions([(result_from_invoice(), 1)])
    root = ET.fromstring(xml_text.encode("utf-8"))

    tax = root.find("Документ/Налоги/Налог")
    assert tax is not None
    assert tax.findtext("Наименование") == "НДС"
    assert tax.findtext("УчтеноВСумме") == "true"


def test_validator_catches_broken_files() -> None:
    assert validate_commerceml("not xml at all")
    assert validate_commerceml("<Wrong/>")

    unbalanced = """<?xml version="1.0" encoding="UTF-8"?>
    <КоммерческаяИнформация ВерсияСхемы="2.08" ДатаФормирования="2026-01-01T00:00:00">
      <Документ>
        <Ид>x</Ид><Номер>1</Номер><Дата>2026-01-01</Дата>
        <Валюта>UZS</Валюта><Сумма>999999.00</Сумма>
        <Контрагенты><Контрагент><Роль>Продавец</Роль></Контрагент></Контрагенты>
        <Товары><Товар><Сумма>100.00</Сумма></Товар></Товары>
      </Документ>
    </КоммерческаяИнформация>"""
    problems = validate_commerceml(unbalanced)
    assert any("does not match" in problem for problem in problems)


def test_batch_export_contains_every_document() -> None:
    results = [(result_from_invoice(seed=seed), seed) for seed in (11, 12, 13)]
    xml_text, problems = export_extractions(results)

    assert problems == []
    root = ET.fromstring(xml_text.encode("utf-8"))
    assert len(root.findall("Документ")) == 3


def test_buyer_falls_back_to_company_configuration() -> None:
    """Many invoices name the supplier only; the buyer is always us."""
    result = ExtractionResult()
    result.set("invoice_number", FieldValue(value="42", confidence=0.9))
    result.set("invoice_date", FieldValue(value=dt.date(2026, 3, 1), confidence=0.9))
    result.set("vendor_name", FieldValue(value='"OLTIN VODIY" MChJ', confidence=0.9))
    result.set("total_amount", FieldValue(value=Decimal("100.00"), confidence=0.9))

    document = build_export_document(result, {
        "organization_name": '"AGROMASH SERVIS" MChJ',
        "organization_tin": "205000137",
    })
    assert document.buyer.name == '"AGROMASH SERVIS" MChJ'
    assert document.buyer.tin == "205000137"
