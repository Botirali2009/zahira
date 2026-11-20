"""1C:Enterprise 8.3 export in CommerceML 2.08 format.

CommerceML is the format 1C:Buxgalteriya actually imports through
"Загрузка из CommerceML" — no external processor, no COM connection, no per-site
custom development. That choice is the whole reason the MVP can ship to many
different 1C installations without a consultant visit for each one (deep-dive
risk #3).

Two details decide whether an import is clean or creates a mess:

* **Stable `Ид` values.** 1C keys counterparties and goods on the identifier in
  the file. Random GUIDs on every export produce a duplicate supplier each time.
  Every identifier here is a UUID5 derived from stable business data, so
  re-importing the same invoice updates one record instead of creating another.
* **OKEI unit codes.** 1C resolves units of measure by classifier code, not by
  the free-text label. Sending `dona` without code 796 leaves the unit blank on
  every posted line.
"""

from __future__ import annotations

import datetime as dt
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.core.logging import get_logger
from app.services.extract.base import ExtractionResult
from app.services.extract.parsers import format_amount

logger = get_logger(__name__)

SCHEMA_VERSION = "2.08"

# Namespace for deterministic identifiers. Fixed forever — changing it would
# make every previously exported counterparty look new to 1C.
_NAMESPACE = uuid.UUID("6f1a9c4e-6b2f-5c8a-9d3e-1a7b4c5d6e7f")

# OKEI (ОКЕИ) classifier codes. 1C matches units of measure on these.
OKEI_CODES: dict[str, tuple[str, str]] = {
    "dona": ("796", "Штука"), "шт": ("796", "Штука"), "штука": ("796", "Штука"),
    "kg": ("166", "Килограмм"), "кг": ("166", "Килограмм"),
    "tonna": ("168", "Тонна"), "тонна": ("168", "Тонна"),
    "litr": ("112", "Литр"), "литр": ("112", "Литр"),
    "metr": ("006", "Метр"), "метр": ("006", "Метр"),
    "m2": ("055", "Квадратный метр"), "м2": ("055", "Квадратный метр"),
    "m3": ("113", "Кубический метр"), "м3": ("113", "Кубический метр"),
    "soat": ("356", "Час"), "час": ("356", "Час"),
    "kun": ("359", "Сутки"), "день": ("359", "Сутки"),
    "oy": ("362", "Месяц"), "месяц": ("362", "Месяц"),
    "quti": ("778", "Упаковка"), "упак": ("778", "Упаковка"),
    "komplekt": ("839", "Комплект"), "компл": ("839", "Комплект"),
    "xizmat": ("796", "Штука"), "услуга": ("796", "Штука"),
}

DEFAULT_UNIT = ("796", "Штука")


class ExportError(ValueError):
    """The extraction cannot produce a valid 1C document."""


@dataclass
class Counterparty:
    name: str
    tin: str | None = None
    address: str | None = None
    role: str = "Продавец"

    @property
    def identifier(self) -> str:
        # Keyed on the STIR when we have one: the taxpayer number is the stable
        # identity of a company, its printed name is not.
        key = f"party:{self.tin}" if self.tin else f"party-name:{self.name.strip().casefold()}"
        return str(uuid.uuid5(_NAMESPACE, key))


@dataclass
class ExportLineItem:
    index: int
    name: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    unit: str | None = None
    vat_amount: Decimal | None = None
    vat_rate: Decimal | None = None

    @property
    def identifier(self) -> str:
        return str(uuid.uuid5(_NAMESPACE, f"good:{self.name.strip().casefold()}"))


@dataclass
class ExportDocument:
    number: str
    date: dt.date
    seller: Counterparty
    buyer: Counterparty
    total_amount: Decimal
    line_items: list[ExportLineItem] = field(default_factory=list)
    vat_amount: Decimal | None = None
    subtotal: Decimal | None = None
    currency: str = "UZS"
    operation: str = "Счет на оплату"
    comment: str | None = None
    source_document_id: int | None = None

    @property
    def identifier(self) -> str:
        return str(uuid.uuid5(
            _NAMESPACE,
            f"doc:{self.seller.tin or self.seller.name}:{self.number}:{self.date.isoformat()}",
        ))


def build_export_document(
    result: ExtractionResult,
    company_config: dict[str, Any] | None = None,
    document_id: int | None = None,
) -> ExportDocument:
    """Convert an extraction into a 1C-ready document, or explain why it cannot."""
    config = company_config or {}

    number = _text(result, "invoice_number")
    date = _date(result, "invoice_date")
    seller_name = _text(result, "vendor_name")
    total = _amount(result, "total_amount")

    missing = [
        name for name, value in (
            ("invoice_number", number),
            ("invoice_date", date),
            ("vendor_name", seller_name),
            ("total_amount", total),
        ) if value in (None, "")
    ]
    if missing:
        raise ExportError(
            "Cannot build a 1C document without: " + ", ".join(missing)
            + ". Fill these in on the review screen first."
        )

    seller = Counterparty(
        name=str(seller_name),
        tin=_text(result, "vendor_tin"),
        address=_text(result, "vendor_address"),
        role="Продавец",
    )
    buyer = Counterparty(
        name=_text(result, "buyer_name") or config.get("organization_name") or "Покупатель",
        tin=_text(result, "buyer_tin") or config.get("organization_tin"),
        address=_text(result, "buyer_address"),
        role="Покупатель",
    )

    items: list[ExportLineItem] = []
    for item in result.line_items:
        if item.amount is None or not item.description:
            continue
        quantity = item.quantity if item.quantity is not None else Decimal("1")
        unit_price = item.unit_price
        if unit_price is None:
            unit_price = (item.amount / quantity) if quantity else item.amount
        items.append(ExportLineItem(
            index=item.index,
            name=item.description,
            quantity=Decimal(str(quantity)),
            unit_price=Decimal(str(unit_price)),
            amount=Decimal(str(item.amount)),
            unit=item.unit,
            vat_amount=item.vat_amount,
            vat_rate=item.vat_rate,
        ))

    if not items:
        # 1C will not post a document with no goods rows. A single summary row
        # keeps the import valid and is what an accountant would type by hand.
        items.append(ExportLineItem(
            index=1,
            name=config.get("fallback_line_name", "Товары и услуги по счету"),
            quantity=Decimal("1"),
            unit_price=Decimal(str(total)),
            amount=Decimal(str(total)),
            unit=None,
        ))

    return ExportDocument(
        number=str(number),
        date=date,
        seller=seller,
        buyer=buyer,
        total_amount=Decimal(str(total)),
        subtotal=_amount(result, "subtotal"),
        vat_amount=_amount(result, "vat_amount"),
        currency=_text(result, "currency") or "UZS",
        line_items=items,
        operation=config.get("operation", "Счет на оплату"),
        source_document_id=document_id,
    )


def build_commerceml(documents: list[ExportDocument], generated_at: dt.datetime | None = None) -> str:
    """Render one or more documents as a CommerceML 2.08 XML string."""
    if not documents:
        raise ExportError("Nothing to export")

    generated_at = generated_at or dt.datetime.now()
    root = ET.Element("КоммерческаяИнформация", {
        "ВерсияСхемы": SCHEMA_VERSION,
        "ДатаФормирования": generated_at.strftime("%Y-%m-%dT%H:%M:%S"),
    })

    for document in documents:
        root.append(_document_element(document))

    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def _document_element(document: ExportDocument) -> ET.Element:
    element = ET.Element("Документ")
    _sub(element, "Ид", document.identifier)
    _sub(element, "Номер", document.number)
    _sub(element, "Дата", document.date.isoformat())
    _sub(element, "ХозОперация", document.operation)
    _sub(element, "Роль", "Продавец")
    _sub(element, "Валюта", document.currency)
    _sub(element, "Курс", "1")
    _sub(element, "Сумма", format_amount(document.total_amount))

    counterparties = ET.SubElement(element, "Контрагенты")
    counterparties.append(_counterparty_element(document.seller))
    counterparties.append(_counterparty_element(document.buyer))

    goods = ET.SubElement(element, "Товары")
    for item in document.line_items:
        goods.append(_good_element(item))

    if document.vat_amount is not None:
        taxes = ET.SubElement(element, "Налоги")
        tax = ET.SubElement(taxes, "Налог")
        _sub(tax, "Наименование", "НДС")
        # The grand total already includes VAT, which is how these invoices are
        # printed; telling 1C otherwise double-counts the tax.
        _sub(tax, "УчтеноВСумме", "true")
        _sub(tax, "Сумма", format_amount(document.vat_amount))

    if document.source_document_id is not None:
        properties = ET.SubElement(element, "ЗначенияРеквизитов")
        prop = ET.SubElement(properties, "ЗначениеРеквизита")
        _sub(prop, "Наименование", "HujjatAI ID")
        _sub(prop, "Значение", str(document.source_document_id))

    return element


def _counterparty_element(party: Counterparty) -> ET.Element:
    element = ET.Element("Контрагент")
    _sub(element, "Ид", party.identifier)
    _sub(element, "Наименование", party.name)
    _sub(element, "ОфициальноеНаименование", party.name)
    if party.tin:
        _sub(element, "ИНН", party.tin)
    _sub(element, "Роль", party.role)
    if party.address:
        address = ET.SubElement(element, "Адрес")
        _sub(address, "Представление", party.address)
    return element


def _good_element(item: ExportLineItem) -> ET.Element:
    element = ET.Element("Товар")
    _sub(element, "Ид", item.identifier)
    _sub(element, "Наименование", item.name)

    code, full_name = OKEI_CODES.get((item.unit or "").strip().casefold(), DEFAULT_UNIT)
    unit = ET.SubElement(element, "БазоваяЕдиница", {
        "Код": code,
        "НаименованиеПолное": full_name,
        "МеждународноеСокращение": "",
    })
    unit.text = item.unit or full_name

    _sub(element, "ЦенаЗаЕдиницу", format_amount(item.unit_price))
    _sub(element, "Количество", format_amount(item.quantity, decimals=3))
    _sub(element, "Сумма", format_amount(item.amount))

    if item.vat_amount is not None:
        taxes = ET.SubElement(element, "Налоги")
        tax = ET.SubElement(taxes, "Налог")
        _sub(tax, "Наименование", "НДС")
        if item.vat_rate is not None:
            _sub(tax, "Ставка", format_amount(item.vat_rate, decimals=0))
        _sub(tax, "УчтеноВСумме", "true")
        _sub(tax, "Сумма", format_amount(item.vat_amount))
    return element


def _sub(parent: ET.Element, tag: str, text: str) -> ET.Element:
    element = ET.SubElement(parent, tag)
    element.text = text
    return element


def validate_commerceml(xml_text: str) -> list[str]:
    """Re-parse the generated file and check what 1C requires. Returns problems.

    Cheap insurance: a malformed export is discovered here, not by an accountant
    watching 1C reject a file in front of their director.
    """
    problems: list[str] = []
    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError as exc:
        return [f"XML is not well-formed: {exc}"]

    if root.tag != "КоммерческаяИнформация":
        problems.append(f"Root element must be КоммерческаяИнформация, found {root.tag}")
    if root.get("ВерсияСхемы") != SCHEMA_VERSION:
        problems.append(f"ВерсияСхемы must be {SCHEMA_VERSION}")

    documents = root.findall("Документ")
    if not documents:
        problems.append("File contains no Документ elements")

    for index, document in enumerate(documents, start=1):
        for tag in ("Ид", "Номер", "Дата", "Валюта", "Сумма"):
            if document.findtext(tag) in (None, ""):
                problems.append(f"Document {index}: missing required element {tag}")

        roles = [party.findtext("Роль") for party in document.iterfind("Контрагенты/Контрагент")]
        if "Продавец" not in roles:
            problems.append(f"Document {index}: no counterparty with Роль=Продавец")

        goods = document.findall("Товары/Товар")
        if not goods:
            problems.append(f"Document {index}: no Товар rows")

        total = document.findtext("Сумма")
        goods_sum = Decimal("0")
        for good in goods:
            amount = good.findtext("Сумма")
            if amount:
                try:
                    goods_sum += Decimal(amount)
                except Exception:
                    problems.append(f"Document {index}: unparseable Товар/Сумма '{amount}'")
        vat = document.findtext("Налоги/Налог/Сумма")
        if total:
            try:
                declared = Decimal(total)
            except Exception:
                problems.append(f"Document {index}: unparseable Сумма '{total}'")
            else:
                expected = goods_sum + (Decimal(vat) if vat else Decimal("0"))
                if abs(expected - declared) > Decimal("1.00"):
                    problems.append(
                        f"Document {index}: goods ({goods_sum}) + VAT ({vat or 0}) = {expected} "
                        f"does not match Сумма {declared}"
                    )
    return problems


def export_extractions(
    results: list[tuple[ExtractionResult, int | None]],
    company_config: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    """Build and self-check a CommerceML file for a batch of extractions."""
    documents = [
        build_export_document(result, company_config, document_id)
        for result, document_id in results
    ]
    xml_text = build_commerceml(documents)
    problems = validate_commerceml(xml_text)
    if problems:
        logger.warning("1C export self-check found problems", extra={"problems": problems})
    return xml_text, problems


# --- helpers ----------------------------------------------------------------

def _text(result: ExtractionResult, name: str) -> str | None:
    entry = result.get(name)
    if not entry.is_present:
        return None
    return str(entry.value).strip() or None


def _amount(result: ExtractionResult, name: str) -> Decimal | None:
    entry = result.get(name)
    if not entry.is_present:
        return None
    try:
        return Decimal(str(entry.value))
    except Exception:
        return None


def _date(result: ExtractionResult, name: str) -> dt.date | None:
    entry = result.get(name)
    if not entry.is_present:
        return None
    value = entry.value
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        return None
