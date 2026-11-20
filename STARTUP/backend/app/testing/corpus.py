"""Synthetic Uzbek invoice corpus with ground truth.

Purpose (deep-dive §6, "Training Data Acquisition — Phase 1"): before a single
real customer document exists, the extraction pipeline needs something to be
measured against. This module generates invoices that mirror the layouts,
scripts and number formats of real Uzbek `hisob-faktura` / `счёт-фактура`
documents, together with the exact ground truth for every field.

The renderers are written to look like the documents do, not like the parser
wants them to: three layout families, four script mixes, several number and date
formats, optional OCR-style noise. An accuracy number measured here is a lower
bound on a clean scan and an upper bound on a bad phone photo — real customer
documents remain the only ground truth that counts, which is why the beta in
Phase 2.7 exists.
"""

from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

VAT_RATE = Decimal("12")  # Uzbekistan standard rate since 2023

STYLE_UZ_LATIN = "uz_latin"
STYLE_UZ_CYRILLIC = "uz_cyrillic"
STYLE_RUSSIAN = "russian"
STYLE_MIXED = "mixed"
STYLES = (STYLE_UZ_LATIN, STYLE_UZ_CYRILLIC, STYLE_RUSSIAN, STYLE_MIXED)

LAYOUT_CLASSIC = "classic"     # one label per line, wide table
LAYOUT_COMPACT = "compact"     # number and date on the title line
LAYOUT_TWO_COLUMN = "two_col"  # vendor and buyer side by side
LAYOUTS = (LAYOUT_CLASSIC, LAYOUT_COMPACT, LAYOUT_TWO_COLUMN)

_VENDOR_NAMES = [
    ('"OLTIN VODIY SAVDO" MChJ', '"ОЛТИН ВОДИЙ САВДО" МЧЖ', 'ООО "ОЛТИН ВОДИЙ САВДО"'),
    ('"TOSHKENT QURILISH INVEST" MChJ', '"ТОШКЕНТ ҚУРИЛИШ ИНВЕСТ" МЧЖ', 'ООО "ТОШКЕНТ КУРИЛИШ ИНВЕСТ"'),
    ('"SAMARQAND AGRO EKSPORT" MChJ', '"САМАРҚАНД АГРО ЭКСПОРТ" МЧЖ', 'ООО "САМАРКАНД АГРО ЭКСПОРТ"'),
    ('"NAVRUZ LOGISTIKA" MChJ', '"НАВРУЗ ЛОГИСТИКА" МЧЖ', 'ООО "НАВРУЗ ЛОГИСТИКА"'),
    ('"BUXORO TEKSTIL GROUP" AJ', '"БУХОРО ТЕКСТИЛ ГРУП" АЖ', 'АО "БУХАРА ТЕКСТИЛЬ ГРУПП"'),
    ('"FARGONA OZIQ-OVQAT" MChJ', '"ФАРҒОНА ОЗИҚ-ОВҚАТ" МЧЖ', 'ООО "ФЕРГАНА ОЗИК-ОВКАТ"'),
    ('"ANDIJON MOTORS SERVIS" MChJ', '"АНДИЖОН МОТОРС СЕРВИС" МЧЖ', 'ООО "АНДИЖАН МОТОРС СЕРВИС"'),
    ('"XORAZM QISHLOQ XOJALIK" MChJ', '"ХОРАЗМ ҚИШЛОҚ ХЎЖАЛИК" МЧЖ', 'ООО "ХОРЕЗМ КИШЛОК ХУЖАЛИК"'),
]

_BUYER_NAMES = [
    ('"AGROMASH SERVIS" MChJ', '"АГРОМАШ СЕРВИС" МЧЖ', 'ООО "АГРОМАШ СЕРВИС"'),
    ('"MEGA BUILD" MChJ', '"МЕГА БИЛД" МЧЖ', 'ООО "МЕГА БИЛД"'),
    ('"UZTRANS EXPEDITSIYA" MChJ', '"УЗТРАНС ЭКСПЕДИЦИЯ" МЧЖ', 'ООО "УЗТРАНС ЭКСПЕДИЦИЯ"'),
    ('"SIFAT MEBEL" MChJ', '"СИФАТ МЕБЕЛ" МЧЖ', 'ООО "СИФАТ МЕБЕЛЬ"'),
    ('"YANGI ASR QURILISH" MChJ', '"ЯНГИ АСР ҚУРИЛИШ" МЧЖ', 'ООО "ЯНГИ АСР КУРИЛИШ"'),
]

_CITIES = [
    ("Toshkent sh., Chilonzor tumani, Bunyodkor ko'chasi", "Тошкент ш., Чилонзор тумани, Бунёдкор кўчаси", "г. Ташкент, Чиланзарский район, ул. Бунёдкор"),
    ("Samarqand sh., Registon ko'chasi", "Самарқанд ш., Регистон кўчаси", "г. Самарканд, ул. Регистан"),
    ("Buxoro sh., Mustaqillik ko'chasi", "Бухоро ш., Мустақиллик кўчаси", "г. Бухара, ул. Мустакиллик"),
    ("Andijon sh., Navoiy shoh ko'chasi", "Андижон ш., Навоий шоҳ кўчаси", "г. Андижан, пр. Навои"),
]

# (uz-Latn, uz-Cyrl, ru, unit_uz, unit_ru)
_PRODUCTS = [
    ("Sement M-400", "Цемент М-400", "Цемент М-400", "tonna", "тонна"),
    ("Armatura 12 mm", "Арматура 12 мм", "Арматура 12 мм", "tonna", "тонна"),
    ("G'isht M-100", "Ғишт М-100", "Кирпич М-100", "dona", "шт"),
    ("Bo'yoq emulsiya", "Бўёқ эмульсия", "Краска эмульсионная", "litr", "литр"),
    ("Kabel VVG 3x2.5", "Кабель ВВГ 3х2.5", "Кабель ВВГ 3х2.5", "metr", "метр"),
    ("Ofis qog'ozi A4", "Офис қоғози А4", "Бумага офисная А4", "quti", "упак"),
    ("Transport xizmati", "Транспорт хизмати", "Транспортные услуги", "xizmat", "услуга"),
    ("Konsalting xizmati", "Консалтинг хизмати", "Консалтинговые услуги", "soat", "час"),
    ("Un oliy nav", "Ун олий нав", "Мука высший сорт", "kg", "кг"),
    ("Paxta tolasi", "Пахта толаси", "Хлопковое волокно", "tonna", "тонна"),
    ("Polipropilen quvur", "Полипропилен қувур", "Полипропиленовая труба", "metr", "метр"),
    ("Kompyuter monitori", "Компьютер монитори", "Монитор компьютерный", "dona", "шт"),
]


def tin_for_party(role: str, index: int) -> str:
    """Stable STIR per company.

    A real counterparty has exactly one taxpayer number across every invoice it
    ever issues. Randomising it per document would make the vendor registry
    untestable — and the registry is what repairs OCR-damaged names.
    """
    base = 301_000_000 if role == "vendor" else 205_000_000
    return str(base + index * 7_919 + 137)


def known_parties() -> dict[str, tuple[str, str, str]]:
    """Every counterparty in the corpus keyed by STIR, in all three scripts.

    Stands in for the confirmed supplier list a real customer accumulates.
    """
    registry: dict[str, tuple[str, str, str]] = {}
    for index, names in enumerate(_VENDOR_NAMES):
        registry[tin_for_party("vendor", index)] = names
    for index, names in enumerate(_BUYER_NAMES):
        registry[tin_for_party("buyer", index)] = names
    return registry


@dataclass
class GroundTruthLineItem:
    index: int
    description: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal


@dataclass
class InvoiceSpec:
    """Ground truth for one generated invoice."""

    invoice_number: str
    invoice_date: dt.date
    vendor_name: str
    vendor_tin: str
    vendor_address: str
    buyer_name: str
    buyer_tin: str
    buyer_address: str
    contract_number: str
    contract_date: dt.date
    line_items: list[GroundTruthLineItem]
    subtotal: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    currency: str = "UZS"
    style: str = STYLE_UZ_LATIN
    layout: str = LAYOUT_CLASSIC
    metadata: dict[str, Any] = field(default_factory=dict)

    def expected_fields(self) -> dict[str, Any]:
        """Ground truth in the same shape the extractor produces."""
        return {
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date.isoformat(),
            "vendor_name": self.vendor_name,
            "vendor_tin": self.vendor_tin,
            "buyer_name": self.buyer_name,
            "buyer_tin": self.buyer_tin,
            "subtotal": str(self.subtotal),
            "vat_amount": str(self.vat_amount),
            "total_amount": str(self.total_amount),
            "currency": self.currency,
        }


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_amount(value: Decimal, style: str, rng: random.Random) -> str:
    """Render an amount the way local software does.

    `1 250 000,00` (space groups, comma decimals) dominates in UZ/RU documents;
    `1,250,000.00` shows up in exports from English-locale systems.
    """
    text = f"{value:,.2f}"
    if style == "western":
        return text
    return text.replace(",", " ").replace(".", ",")


def _format_date(value: dt.date, style: str, rng: random.Random) -> str:
    choice = rng.random()
    if choice < 0.6:
        return value.strftime("%d.%m.%Y")
    if choice < 0.75:
        return value.strftime("%d/%m/%Y")
    if choice < 0.85:
        return value.strftime("%Y-%m-%d")
    if style in (STYLE_RUSSIAN, STYLE_UZ_CYRILLIC):
        months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
                  "августа", "сентября", "октября", "ноября", "декабря"]
        return f"{value.day} {months[value.month - 1]} {value.year}"
    months_uz = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
                 "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
    return f"{value.day} {months_uz[value.month - 1]} {value.year}"


def random_invoice(seed: int | None = None, style: str | None = None,
                   layout: str | None = None) -> InvoiceSpec:
    rng = random.Random(seed)
    style = style or rng.choice(STYLES)
    layout = layout or rng.choice(LAYOUTS)

    vendor = rng.choice(_VENDOR_NAMES)
    buyer = rng.choice(_BUYER_NAMES)
    vendor_city = rng.choice(_CITIES)
    buyer_city = rng.choice(_CITIES)
    variant = {STYLE_UZ_LATIN: 0, STYLE_UZ_CYRILLIC: 1, STYLE_RUSSIAN: 2}.get(style, 0)
    party_variant = variant if style != STYLE_MIXED else rng.choice([0, 1, 2])

    item_count = rng.randint(1, 5)
    items: list[GroundTruthLineItem] = []
    for index in range(1, item_count + 1):
        product = rng.choice(_PRODUCTS)
        quantity = Decimal(str(rng.choice([1, 2, 3, 5, 10, 12, 25, 100, 250, 500])))
        if rng.random() < 0.2:
            quantity += Decimal("0.5")
        unit_price = Decimal(rng.randrange(15_000, 15_000_000, 500))
        amount = _money(quantity * unit_price)
        description = product[0] if party_variant == 0 else (product[1] if party_variant == 1 else product[2])
        unit = product[3] if party_variant < 2 else product[4]
        items.append(GroundTruthLineItem(index, description, unit, quantity, unit_price, amount))

    subtotal = _money(sum((item.amount for item in items), Decimal("0")))
    vat_amount = _money(subtotal * VAT_RATE / Decimal("100"))
    total = _money(subtotal + vat_amount)

    invoice_date = dt.date(2026, rng.randint(1, 8), rng.randint(1, 28))
    contract_date = invoice_date - dt.timedelta(days=rng.randint(15, 300))

    return InvoiceSpec(
        invoice_number=str(rng.randint(100, 9999)) if rng.random() < 0.7
        else f"{rng.randint(1, 99)}-{rng.choice('ABKM')}{rng.randint(10, 99)}",
        invoice_date=invoice_date,
        vendor_name=vendor[party_variant],
        vendor_tin=tin_for_party("vendor", _VENDOR_NAMES.index(vendor)),
        vendor_address=f"{vendor_city[party_variant]} {rng.randint(1, 120)}",
        buyer_name=buyer[party_variant],
        buyer_tin=tin_for_party("buyer", _BUYER_NAMES.index(buyer)),
        buyer_address=f"{buyer_city[party_variant]} {rng.randint(1, 120)}",
        contract_number=str(rng.randint(10, 999)),
        contract_date=contract_date,
        line_items=items,
        subtotal=subtotal,
        vat_amount=vat_amount,
        total_amount=total,
        style=style,
        layout=layout,
        metadata={"seed": seed},
    )


# --- Text rendering ---------------------------------------------------------

_LABELS: dict[str, dict[str, str]] = {
    STYLE_UZ_LATIN: {
        "title": "HISOB-FAKTURA", "number": "Raqami", "date": "Sana",
        "vendor": "Yetkazib beruvchi", "buyer": "Xaridor", "tin": "STIR",
        "address": "Manzil", "contract": "Shartnoma", "col_index": "№",
        "col_desc": "Tovar (xizmat) nomi", "col_unit": "O'lchov birligi",
        "col_qty": "Soni", "col_price": "Narxi", "col_amount": "Summa",
        "subtotal": "Jami", "vat": "QQS", "total": "Jami QQS bilan",
        "currency": "so'm", "director": "Direktor", "accountant": "Bosh hisobchi",
    },
    STYLE_UZ_CYRILLIC: {
        "title": "ҲИСОБ-ФАКТУРА", "number": "Рақами", "date": "Сана",
        "vendor": "Етказиб берувчи", "buyer": "Харидор", "tin": "СТИР",
        "address": "Манзил", "contract": "Шартнома", "col_index": "№",
        "col_desc": "Товар (хизмат) номи", "col_unit": "Ўлчов бирлиги",
        "col_qty": "Сони", "col_price": "Нархи", "col_amount": "Сумма",
        "subtotal": "Жами", "vat": "ҚҚС", "total": "Жами ҚҚС билан",
        "currency": "сўм", "director": "Директор", "accountant": "Бош ҳисобчи",
    },
    STYLE_RUSSIAN: {
        "title": "СЧЁТ-ФАКТУРА", "number": "Номер", "date": "Дата",
        "vendor": "Поставщик", "buyer": "Покупатель", "tin": "ИНН",
        "address": "Адрес", "contract": "Договор", "col_index": "№",
        "col_desc": "Наименование товара", "col_unit": "Ед.изм",
        "col_qty": "Кол-во", "col_price": "Цена", "col_amount": "Сумма",
        "subtotal": "Итого", "vat": "НДС", "total": "Всего к оплате",
        "currency": "сум", "director": "Директор", "accountant": "Главный бухгалтер",
    },
}


def _labels_for(style: str, rng: random.Random) -> dict[str, str]:
    if style != STYLE_MIXED:
        return _LABELS[style]
    # A genuinely mixed document: each label block drawn from a different script,
    # which is exactly the case that breaks single-language OCR products.
    mixed: dict[str, str] = {}
    for key in _LABELS[STYLE_UZ_LATIN]:
        source = rng.choice([STYLE_UZ_LATIN, STYLE_UZ_CYRILLIC, STYLE_RUSSIAN])
        mixed[key] = _LABELS[source][key]
    return mixed


def render_text(spec: InvoiceSpec, seed: int | None = None) -> str:
    """Render the invoice as plain text (what OCR would hand the extractor)."""
    rng = random.Random(seed if seed is not None else hash(spec.invoice_number) & 0xFFFF)
    labels = _labels_for(spec.style, rng)
    number_style = "western" if rng.random() < 0.15 else "local"

    def amount(value: Decimal) -> str:
        return _format_amount(value, number_style, rng)

    lines: list[str] = []
    date_text = _format_date(spec.invoice_date, spec.style, rng)

    if spec.layout == LAYOUT_COMPACT:
        lines.append(f"{labels['title']} № {spec.invoice_number} от {date_text}"
                     if spec.style == STYLE_RUSSIAN
                     else f"{labels['title']} № {spec.invoice_number}  {labels['date']}: {date_text}")
    else:
        lines.append(labels["title"])
        lines.append(f"{labels['number']}: {spec.invoice_number}")
        lines.append(f"{labels['date']}: {date_text}")
    lines.append("")

    contract_text = f"{labels['contract']}: № {spec.contract_number} " \
                    f"{'от' if spec.style == STYLE_RUSSIAN else 'dan'} " \
                    f"{_format_date(spec.contract_date, spec.style, rng)}"

    if spec.layout == LAYOUT_TWO_COLUMN:
        lines.append(f"{labels['vendor']}: {spec.vendor_name}"
                     f"{' ' * 6}{labels['buyer']}: {spec.buyer_name}")
        lines.append(f"{labels['tin']}: {spec.vendor_tin}"
                     f"{' ' * 6}{labels['tin']}: {spec.buyer_tin}")
        lines.append(f"{labels['address']}: {spec.vendor_address}")
        lines.append(contract_text)
    else:
        lines.append(f"{labels['vendor']}: {spec.vendor_name}")
        lines.append(f"{labels['tin']}: {spec.vendor_tin}")
        lines.append(f"{labels['address']}: {spec.vendor_address}")
        lines.append("")
        lines.append(f"{labels['buyer']}: {spec.buyer_name}")
        lines.append(f"{labels['tin']}: {spec.buyer_tin}")
        lines.append(f"{labels['address']}: {spec.buyer_address}")
        lines.append("")
        lines.append(contract_text)
    lines.append("")

    header = [
        labels["col_index"], labels["col_desc"], labels["col_unit"],
        labels["col_qty"], labels["col_price"], labels["col_amount"],
    ]
    widths = [4, 34, 14, 10, 18, 20]
    lines.append(_row(header, widths))
    lines.append("-" * (sum(widths) + 5))
    for item in spec.line_items:
        lines.append(_row(
            [
                str(item.index),
                item.description,
                item.unit,
                _format_quantity(item.quantity, number_style),
                amount(item.unit_price),
                amount(item.amount),
            ],
            widths,
        ))
    lines.append("")

    vat_label = f"{labels['vat']} ({int(VAT_RATE)}%)" if rng.random() < 0.7 else f"{labels['vat']} {int(VAT_RATE)}%"
    lines.append(f"{labels['subtotal']}: {amount(spec.subtotal)} {labels['currency']}")
    lines.append(f"{vat_label}: {amount(spec.vat_amount)} {labels['currency']}")
    lines.append(f"{labels['total']}: {amount(spec.total_amount)} {labels['currency']}")
    lines.append("")
    lines.append(f"{labels['director']}: ______________")
    lines.append(f"{labels['accountant']}: ______________")

    return "\n".join(lines)


def _format_quantity(value: Decimal, number_style: str) -> str:
    if value == value.to_integral_value():
        return str(int(value))
    text = f"{value:.1f}"
    return text if number_style == "western" else text.replace(".", ",")


def _row(cells: list[str], widths: list[int]) -> str:
    parts = []
    for cell, width in zip(cells, widths, strict=False):
        parts.append(cell.ljust(width) if len(cell) < width else cell + "  ")
    return "  ".join(part.rstrip() if index == len(parts) - 1 else part
                     for index, part in enumerate(parts)).rstrip()


def render_pdf(spec: InvoiceSpec, seed: int | None = None) -> bytes:
    """Render as a born-digital PDF, matching Uzbekistan's e-invoicing reality."""
    try:
        from reportlab.lib.pagesizes import A4  # noqa: PLC0415
        from reportlab.pdfbase import pdfmetrics  # noqa: PLC0415
        from reportlab.pdfbase.ttfonts import TTFont  # noqa: PLC0415
        from reportlab.pdfgen import canvas  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - dev-only dependency
        raise RuntimeError("reportlab is required for PDF rendering "
                           "(pip install -r requirements-dev.txt)") from exc

    import io  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    font_name = "Helvetica"
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/DejaVuSans.ttf",
    ):
        if Path(candidate).is_file():
            pdfmetrics.registerFont(TTFont("DejaVu", candidate))
            font_name = "DejaVu"
            break

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    pdf.setFont(font_name, 9)

    y = height - 50
    for line in render_text(spec, seed=seed).splitlines():
        if y < 50:
            pdf.showPage()
            pdf.setFont(font_name, 9)
            y = height - 50
        pdf.drawString(40, y, line)
        y -= 12

    pdf.setTitle(f"Hisob-faktura {spec.invoice_number}")
    pdf.save()
    return buffer.getvalue()


def generate_batch(count: int, seed: int = 0) -> list[InvoiceSpec]:
    return [random_invoice(seed=seed + index) for index in range(count)]


# --- OCR noise simulation ---------------------------------------------------

# Cyrillic/Latin homoglyph pairs. These are THE failure mode for mixed-script
# Uzbek documents: the glyphs are identical, so an OCR engine biased toward one
# alphabet silently emits the wrong codepoint and every downstream string
# comparison breaks while the text still looks correct to a human reviewer.
_HOMOGLYPHS: dict[str, str] = {
    "О": "O", "о": "o", "С": "C", "с": "c", "Р": "P", "р": "p", "А": "A", "а": "a",
    "Е": "E", "е": "e", "К": "K", "к": "k", "М": "M", "Т": "T", "В": "B", "Н": "H",
    "Х": "X", "х": "x", "У": "Y", "у": "y", "З": "3", "б": "6",
    "O": "О", "o": "о", "C": "С", "c": "с", "P": "Р", "p": "р", "A": "А", "a": "а",
    "E": "Е", "e": "е", "K": "К", "M": "М", "T": "Т", "B": "В", "H": "Н",
    "X": "Х", "x": "х", "Y": "У", "y": "у",
}

# Glyph confusions inside numbers — the expensive kind of OCR error.
_DIGIT_CONFUSIONS: dict[str, str] = {
    "0": "O", "1": "l", "5": "S", "6": "b", "8": "B", "9": "g", "3": "З", "7": "7",
}


def add_ocr_noise(text: str, rate: float = 0.02, seed: int | None = None) -> str:
    """Corrupt text the way an OCR engine does, at a given character error rate.

    Roughly: rate 0.01-0.02 is a clean 300 DPI scan, 0.05 a mediocre one, 0.10 a
    phone photo in bad light. Errors are weighted toward the confusions that
    actually happen (homoglyphs, digit/letter swaps, lost Uzbek apostrophes)
    rather than uniform random noise, so the resulting accuracy curve means
    something.
    """
    if rate <= 0:
        return text
    rng = random.Random(seed)
    out: list[str] = []

    for char in text:
        if rng.random() >= rate:
            out.append(char)
            continue

        roll = rng.random()
        if char in _HOMOGLYPHS and roll < 0.45:
            out.append(_HOMOGLYPHS[char])
        elif char.isdigit() and roll < 0.65:
            out.append(_DIGIT_CONFUSIONS.get(char, char))
        elif char in "ʻʼ'’`" and roll < 0.80:
            out.append("")                      # dropped Uzbek apostrophe
        elif roll < 0.88:
            out.append("")                      # dropped character
        elif roll < 0.94:
            out.append(char + char)             # duplicated character
        elif char == " ":
            out.append("")                      # lost word gap
        else:
            out.append(rng.choice("aeoнрс0189"))  # substitution
    return "".join(out)


def degrade_lines(text: str, merge_probability: float = 0.05, seed: int | None = None) -> str:
    """Merge adjacent lines, mimicking OCR losing a line break in a dense table."""
    rng = random.Random(seed)
    lines = text.splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        if index + 1 < len(lines) and lines[index].strip() and lines[index + 1].strip() \
                and rng.random() < merge_probability:
            out.append(lines[index] + "  " + lines[index + 1])
            index += 2
        else:
            out.append(lines[index])
            index += 1
    return "\n".join(out)
