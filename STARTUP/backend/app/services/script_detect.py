"""Per-block script detection for Uzbek Latin / Uzbek Cyrillic / Russian.

This is the technical core of the product wedge. Uzbek documents routinely mix
three writing systems on one page: a Cyrillic company stamp, a Latin body, and
Russian line items. Detecting script per *text block* (not per document) lets
the pipeline route each block to the right OCR model and lets the extractor
match labels in whichever script the vendor happened to use.

Distinguishing Uzbek Cyrillic from Russian matters because Uzbek Cyrillic uses
four letters Russian does not (ў, қ, ғ, ҳ); seeing any of them proves the block
is Uzbek rather than Russian.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

# Uzbek Latin uses the modifier letters ʻ (U+02BB) and ʼ (U+02BC) in oʻ, gʻ, ʼ.
# In the wild they are typed as ' (U+2018/U+2019) or a plain apostrophe, and OCR
# frequently confuses them, so all variants are treated as Uzbek Latin markers.
UZBEK_LATIN_MARKERS = {"ʻ", "ʼ", "‘", "’", "`", "'"}

# Letters present in Uzbek Cyrillic but absent from the Russian alphabet.
UZBEK_CYRILLIC_ONLY = set("ўқғҳЎҚҒҲ")

# Digraphs that are strong evidence of Uzbek Latin rather than English/other Latin.
UZBEK_LATIN_DIGRAPHS = ("oʻ", "gʻ", "o'", "g'", "sh", "ch", "ng")

SCRIPT_LATIN = "latin"
SCRIPT_CYRILLIC = "cyrillic"
SCRIPT_DIGITS = "digits"
SCRIPT_OTHER = "other"

LANG_UZBEK_LATIN = "uz-Latn"
LANG_UZBEK_CYRILLIC = "uz-Cyrl"
LANG_RUSSIAN = "ru"
LANG_UNKNOWN = "unknown"


@dataclass
class ScriptProfile:
    """Character-class breakdown of a piece of text."""

    latin: float = 0.0
    cyrillic: float = 0.0
    digits: float = 0.0
    other: float = 0.0
    dominant: str = SCRIPT_OTHER
    language: str = LANG_UNKNOWN
    mixed: bool = False
    counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "latin": round(self.latin, 4),
            "cyrillic": round(self.cyrillic, 4),
            "digits": round(self.digits, 4),
            "other": round(self.other, 4),
            "dominant": self.dominant,
            "language": self.language,
            "mixed": self.mixed,
            "counts": self.counts,
        }


def classify_char(char: str) -> str:
    if char.isdigit():
        return SCRIPT_DIGITS
    if not char.isalpha():
        return SCRIPT_OTHER
    try:
        name = unicodedata.name(char)
    except ValueError:  # unnamed / private use
        return SCRIPT_OTHER
    if "CYRILLIC" in name:
        return SCRIPT_CYRILLIC
    if "LATIN" in name:
        return SCRIPT_LATIN
    return SCRIPT_OTHER


def profile_text(text: str, mixed_threshold: float = 0.15) -> ScriptProfile:
    """Classify a text block.

    `mixed_threshold` is the share of letters in the minority script above which
    the block is flagged as genuinely mixed — below it, a stray character (an OCR
    error, or a single Cyrillic abbreviation) should not change routing.
    """
    counts = {SCRIPT_LATIN: 0, SCRIPT_CYRILLIC: 0, SCRIPT_DIGITS: 0, SCRIPT_OTHER: 0}
    for char in text:
        counts[classify_char(char)] += 1

    total = sum(counts.values())
    if total == 0:
        return ScriptProfile(counts=counts)

    letters = counts[SCRIPT_LATIN] + counts[SCRIPT_CYRILLIC]
    profile = ScriptProfile(
        latin=counts[SCRIPT_LATIN] / total,
        cyrillic=counts[SCRIPT_CYRILLIC] / total,
        digits=counts[SCRIPT_DIGITS] / total,
        other=counts[SCRIPT_OTHER] / total,
        counts=counts,
    )

    if letters == 0:
        profile.dominant = SCRIPT_DIGITS if counts[SCRIPT_DIGITS] else SCRIPT_OTHER
        profile.language = LANG_UNKNOWN
        return profile

    latin_share = counts[SCRIPT_LATIN] / letters
    profile.dominant = SCRIPT_LATIN if latin_share >= 0.5 else SCRIPT_CYRILLIC
    profile.mixed = min(latin_share, 1 - latin_share) >= mixed_threshold
    profile.language = detect_language(text, profile.dominant)
    return profile


def detect_language(text: str, dominant: str) -> str:
    """Guess the language of a block given its dominant script."""
    if dominant == SCRIPT_CYRILLIC:
        if any(char in UZBEK_CYRILLIC_ONLY for char in text):
            return LANG_UZBEK_CYRILLIC
        return LANG_RUSSIAN
    if dominant == SCRIPT_LATIN:
        lowered = text.lower()
        if any(marker in lowered for marker in UZBEK_LATIN_MARKERS):
            return LANG_UZBEK_LATIN
        if any(digraph in lowered for digraph in UZBEK_LATIN_DIGRAPHS):
            return LANG_UZBEK_LATIN
        return LANG_UZBEK_LATIN if _looks_uzbek(lowered) else LANG_UNKNOWN
    return LANG_UNKNOWN


_UZBEK_FUNCTION_WORDS = {
    "va", "uchun", "bilan", "jami", "soni", "narxi", "summa", "sana", "raqam",
    "hisob", "faktura", "yetkazib", "beruvchi", "xaridor", "tovar", "xizmat",
    "qqs", "stir", "manzil", "shartnoma", "birligi", "olchov", "boshqa",
}


def _looks_uzbek(lowered: str) -> bool:
    words = {word.strip(".,:;()[]") for word in lowered.split()}
    return bool(words & _UZBEK_FUNCTION_WORDS)


def summarize_blocks(blocks: list[dict[str, object]]) -> dict[str, object]:
    """Aggregate per-block profiles into a document-level summary."""
    joined = " ".join(str(block.get("text", "")) for block in blocks)
    profile = profile_text(joined)
    languages: dict[str, int] = {}
    for block in blocks:
        lang = str(block.get("language") or LANG_UNKNOWN)
        languages[lang] = languages.get(lang, 0) + 1

    summary = profile.to_dict()
    summary["languages"] = languages
    summary["script_count"] = len(
        [key for key in (SCRIPT_LATIN, SCRIPT_CYRILLIC) if profile.counts.get(key, 0) > 0]
    )
    return summary


def annotate_blocks(blocks: list[dict[str, object]]) -> list[dict[str, object]]:
    """Attach `script`, `language` and `mixed` to each block in place."""
    for block in blocks:
        profile = profile_text(str(block.get("text", "")))
        block["script"] = profile.dominant
        block["language"] = profile.language
        block["mixed"] = profile.mixed
    return blocks


# Cyrillic letters whose glyphs are identical to a Latin letter. OCR engines
# pick whichever alphabet their language model favours, so `Поставщик` comes
# back with a Latin `o`, or `Toshkent` with a Cyrillic `Т`. Folding both to one
# canonical form is what makes label matching survive mixed-script pages.
CONFUSABLE_TO_LATIN = {
    "А": "a", "а": "a", "В": "b", "в": "b", "Е": "e", "е": "e", "Ё": "e", "ё": "e",
    "К": "k", "к": "k", "М": "m", "м": "m", "Н": "h", "н": "h", "О": "o", "о": "o",
    "Р": "p", "р": "p", "С": "c", "с": "c", "Т": "t", "т": "t", "У": "y", "у": "y",
    "Х": "x", "х": "x", "І": "i", "і": "i", "Ј": "j", "ј": "j", "Ѕ": "s", "ѕ": "s",
}


# Every character involved in a look-alike pair, in both alphabets and both
# cases. Membership here means "this character could be the other alphabet's
# glyph", which is what identifies OCR substitution inside a word.
CONFUSABLE_CHARS: frozenset[str] = frozenset(
    set(CONFUSABLE_TO_LATIN)
    | set(CONFUSABLE_TO_LATIN.values())
    | {latin.upper() for latin in CONFUSABLE_TO_LATIN.values()}
)


def fold_confusables(text: str) -> str:
    """Map Cyrillic/Latin look-alike characters onto one canonical form.

    Length-preserving by construction: every substitution is one character for
    one character, so offsets computed on the folded string stay valid against
    the original.
    """
    return "".join(CONFUSABLE_TO_LATIN.get(char, char) for char in text)


def lower_preserving_length(text: str) -> str:
    """Lowercase without changing string length.

    `str.casefold()` expands some characters (İ -> i̇, ß -> ss), which would
    desynchronise label offsets from the original line.
    """
    result = []
    for char in text:
        lowered = char.lower()
        result.append(lowered if len(lowered) == 1 else char)
    return "".join(result)


def normalize_uzbek_latin(text: str) -> str:
    """Fold apostrophe variants so `oʻ`, `o'` and `o‘` compare equal.

    Applied to labels before matching, never to extracted values — the value the
    accountant sees must stay byte-identical to the document.
    """
    result = []
    for char in text:
        result.append("ʻ" if char in UZBEK_LATIN_MARKERS else char)
    return "".join(result)
