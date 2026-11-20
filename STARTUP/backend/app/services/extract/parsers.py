"""Value parsers for Uzbek/Russian business documents.

Everything here is deliberately defensive: OCR output is noisy, and an invoice
amount misread by a factor of 1,000 is exactly the kind of error that produces
the tax penalties this product exists to prevent. Parsers return `None` rather
than guessing when the input is ambiguous — a blank field the accountant fills
in is cheap, a confidently wrong number is not.
"""

from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal, InvalidOperation

# Space characters that appear as thousands separators in UZ/RU documents,
# including the non-breaking and narrow no-break spaces Word likes to emit.
_SPACE_SEPARATORS = "     "
_APOSTROPHE_SEPARATORS = "'’ʼ`"

TIN_LENGTH = 9          # STIR / ИНН for legal entities
PINFL_LENGTH = 14       # personal identification number

_TIN_PATTERN = re.compile(r"(?<!\d)(\d{9})(?!\d)")
_PINFL_PATTERN = re.compile(r"(?<!\d)(\d{14})(?!\d)")

_NUMERIC_TOKEN = re.compile(
    r"[-+]?\d[\d" + re.escape(_SPACE_SEPARATORS + _APOSTROPHE_SEPARATORS) + r".,]*\d|\d"
)

UZBEK_MONTHS = {
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6,
    "iyul": 7, "avgust": 8, "sentabr": 9, "sentyabr": 9, "oktabr": 10,
    "oktyabr": 10, "noyabr": 11, "dekabr": 12,
}

RUSSIAN_MONTHS = {
    "января": 1, "январь": 1, "февраля": 2, "февраль": 2, "марта": 3, "март": 3,
    "апреля": 4, "апрель": 4, "мая": 5, "май": 5, "июня": 6, "июнь": 6,
    "июля": 7, "июль": 7, "августа": 8, "август": 8, "сентября": 9, "сентябрь": 9,
    "октября": 10, "октябрь": 10, "ноября": 11, "ноябрь": 11, "декабря": 12,
    "декабрь": 12,
}

UZBEK_CYRILLIC_MONTHS = {
    "январ": 1, "феврал": 2, "март": 3, "апрел": 4, "май": 5, "июн": 6,
    "июл": 7, "август": 8, "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12,
}

_ALL_MONTHS = {**UZBEK_MONTHS, **RUSSIAN_MONTHS, **UZBEK_CYRILLIC_MONTHS}

_DATE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)"), "ymd"),
    (re.compile(r"(?<!\d)(\d{1,2})[./](\d{1,2})[./](\d{4})(?!\d)"), "dmy"),
    (re.compile(r"(?<!\d)(\d{1,2})[./](\d{1,2})[./](\d{2})(?!\d)"), "dmy2"),
)

_TEXT_DATE = re.compile(r"(?<!\d)(\d{1,2})\s*[-\s]\s*([A-Za-zА-Яа-яЎўҚқҒғҲҳ]{3,12})\.?\s*(\d{4})")

# Currency spellings seen on real invoices, mapped to ISO codes.
_CURRENCY_TOKENS = {
    "uzs": "UZS", "soʻm": "UZS", "so'm": "UZS", "som": "UZS", "sum": "UZS",
    "сум": "UZS", "сўм": "UZS", "сумм": "UZS",
    "usd": "USD", "$": "USD", "доллар": "USD", "dollar": "USD",
    "eur": "EUR", "€": "EUR", "evro": "EUR", "евро": "EUR",
    "rub": "RUB", "руб": "RUB",
}


# Letters OCR emits in place of digits. Repair is only safe where the field is
# known to be numeric — never apply this to free text such as a product name.
_DIGIT_REPAIRS = {
    "O": "0", "o": "0", "О": "0", "о": "0", "D": "0", "Q": "0",
    "l": "1", "I": "1", "|": "1", "i": "1",
    "Z": "2", "z": "2",
    "З": "3", "з": "3",
    "A": "4",
    "S": "5", "s": "5", "Ѕ": "5",
    "b": "6", "б": "6", "G": "6",
    "T": "7",
    "B": "8", "В": "8", "в": "8",
    "g": "9", "q": "9",
}


def repair_numeric_text(text: str) -> str | None:
    """Replace OCR letter-for-digit substitutions inside a numeric field.

    Returns None unless the token really is a mangled number: at least two real
    digits, and every non-separator character either a digit or a known
    confusable. `1 25O 000,OO` becomes `1 250 000,00`; `Sement M-400` is
    rejected, which is the point.
    """
    if not text:
        return None
    stripped = str(text).strip()
    if not stripped:
        return None

    digits = 0
    repaired: list[str] = []
    for char in stripped:
        if char.isdigit():
            digits += 1
            repaired.append(char)
        elif char in _DIGIT_REPAIRS:
            repaired.append(_DIGIT_REPAIRS[char])
        elif char in _SPACE_SEPARATORS + _APOSTROPHE_SEPARATORS + ".,-+()%":
            repaired.append(char)
        else:
            return None

    if digits < 2:
        return None
    return "".join(repaired)


def parse_amount(raw: str | None, repair: bool = False) -> Decimal | None:
    """Parse a monetary amount written in any of the local conventions.

    Handles `1 250 000,00`, `1,250,000.00`, `1'250'000`, `1250000` and the
    non-breaking-space variants. Returns None when the separator layout is
    genuinely ambiguous.

    With `repair=True`, OCR letter-for-digit damage is corrected first. Callers
    that enable it must lower the field's confidence — a repaired value is a
    guess about what the scanner saw, and a human should confirm it.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None

    if repair:
        repaired = repair_numeric_text(text)
        if repaired is not None:
            text = repaired

    match = _NUMERIC_TOKEN.search(text)
    if not match:
        return None
    token = match.group(0)

    # Accounting negatives are written as (1 234,00) — the parentheses have to
    # wrap this number, not merely appear somewhere on the line, or a label like
    # "QQS (12%): 74 814 000,00" flips sign.
    start, end = match.span()
    wrapped = text[:start].rstrip().endswith("(") and text[end:].lstrip().startswith(")")
    negative = token.startswith("-") or wrapped
    token = token.lstrip("+-")

    for char in _SPACE_SEPARATORS + _APOSTROPHE_SEPARATORS:
        token = token.replace(char, "")

    has_comma, has_dot = "," in token, "." in token
    if has_comma and has_dot:
        # Whichever appears last is the decimal separator.
        decimal_sep = "," if token.rfind(",") > token.rfind(".") else "."
        thousands_sep = "." if decimal_sep == "," else ","
        token = token.replace(thousands_sep, "").replace(decimal_sep, ".")
    elif has_comma or has_dot:
        sep = "," if has_comma else "."
        parts = token.split(sep)
        tail = parts[-1]
        if len(parts) > 2 or len(tail) == 3 and len(parts[0]) <= 3 and sep == ",":
            # 1,250,000 or 1.250.000 — grouping, not decimals.
            token = token.replace(sep, "")
        elif len(tail) in (1, 2):
            token = token.replace(sep, ".")
        elif len(tail) == 3:
            # A single separator with exactly 3 trailing digits: grouping is far
            # more common than milli-units on an invoice.
            token = token.replace(sep, "")
        else:
            token = token.replace(sep, "")

    if not token or not token.replace(".", "").isdigit():
        return None
    try:
        value = Decimal(token)
    except InvalidOperation:
        return None
    return -value if negative else value


def parse_quantity(raw: str | None) -> Decimal | None:
    """Quantities may be fractional (3,5 tonna). Same rules as amounts."""
    return parse_amount(raw)


def parse_date(raw: str | None, today: dt.date | None = None) -> dt.date | None:
    """Parse a date in numeric or spelled-out UZ/RU form. Returns a date object."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None

    for pattern, kind in _DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        try:
            if kind == "ymd":
                year, month, day = (int(group) for group in match.groups())
            elif kind == "dmy":
                day, month, year = (int(group) for group in match.groups())
            else:
                day, month, short_year = (int(group) for group in match.groups())
                year = 2000 + short_year if short_year < 70 else 1900 + short_year
            return dt.date(year, month, day)
        except ValueError:
            continue

    match = _TEXT_DATE.search(text)
    if match:
        day_text, month_text, year_text = match.groups()
        month = _lookup_month(month_text.lower())
        if month:
            try:
                return dt.date(int(year_text), month, int(day_text))
            except ValueError:
                return None
    return None


def _lookup_month(name: str) -> int | None:
    name = name.strip(".")
    if name in _ALL_MONTHS:
        return _ALL_MONTHS[name]
    # Uzbek Cyrillic months are often written without the final soft sign.
    for key, value in _ALL_MONTHS.items():
        if key.startswith(name) and len(name) >= 3:
            return value
    return None


def parse_tin(raw: str | None, repair: bool = False) -> str | None:
    """Extract a 9-digit STIR/ИНН.

    Uzbekistan publishes no open checksum algorithm for the STIR, so this
    validates length and digit-only composition and nothing more. Claiming a
    checksum we cannot verify would reject valid taxpayer numbers.
    """
    if raw is None:
        return None
    text = str(raw)
    match = _TIN_PATTERN.search(text.replace(" ", "").replace("-", ""))
    if match:
        return match.group(1)
    match = _TIN_PATTERN.search(text)
    if match:
        return match.group(1)

    if repair:
        # A 9-character token of digits and digit-confusables is a damaged TIN.
        for token in re.split(r"[\s,;:]+", text):
            candidate = repair_numeric_text(token)
            if candidate and len(candidate) == TIN_LENGTH and candidate.isdigit():
                return candidate
    return None


def parse_pinfl(raw: str | None) -> str | None:
    if raw is None:
        return None
    match = _PINFL_PATTERN.search(str(raw).replace(" ", ""))
    return match.group(1) if match else None


def is_valid_tin(value: str | None) -> bool:
    return bool(value) and len(str(value)) == TIN_LENGTH and str(value).isdigit()


def parse_currency(raw: str | None, default: str = "UZS") -> str:
    if not raw:
        return default
    lowered = str(raw).lower()
    for token, code in _CURRENCY_TOKENS.items():
        if token in lowered:
            return code
    return default


def clean_party_name(raw: str | None) -> str | None:
    """Tidy a counterparty name without changing its content.

    Strips trailing separators and collapses whitespace. The legal form
    (MChJ / ООО / AJ / QK) is deliberately preserved — 1C matches counterparties
    on the full legal name.
    """
    if raw is None:
        return None
    text = re.sub(r"\s+", " ", str(raw)).strip()
    # Strips any of these separator characters from both ends, which is the
    # intent — vendors pad names with different punctuation on every layout.
    text = text.strip(" :;,-–—–")  # noqa: B005
    # Drop a trailing label that bled in from the next column, e.g. "… STIR".
    text = re.sub(r"\s+(STIR|ИНН|INN|СТИР)\s*:?\s*$", "", text, flags=re.IGNORECASE)
    return text or None


def extract_numbers(text: str) -> list[Decimal]:
    """All numeric tokens in a line, in order — used for table row parsing."""
    values: list[Decimal] = []
    for match in _NUMERIC_TOKEN.finditer(text):
        value = parse_amount(match.group(0))
        if value is not None:
            values.append(value)
    return values


def format_amount(value: Decimal | float | int | None, decimals: int = 2) -> str:
    if value is None:
        return ""
    quantized = Decimal(str(value)).quantize(Decimal(10) ** -decimals)
    return f"{quantized:.{decimals}f}"
