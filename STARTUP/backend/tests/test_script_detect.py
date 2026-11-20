"""Script and language detection tests — the product's core differentiator."""

from __future__ import annotations

from app.services.script_detect import (
    LANG_RUSSIAN,
    LANG_UZBEK_CYRILLIC,
    LANG_UZBEK_LATIN,
    SCRIPT_CYRILLIC,
    SCRIPT_LATIN,
    fold_confusables,
    lower_preserving_length,
    normalize_uzbek_latin,
    profile_text,
    summarize_blocks,
)


def test_detects_uzbek_latin() -> None:
    profile = profile_text("Yetkazib beruvchi: OLTIN VODIY SAVDO MChJ")
    assert profile.dominant == SCRIPT_LATIN
    assert profile.language == LANG_UZBEK_LATIN


def test_distinguishes_uzbek_cyrillic_from_russian() -> None:
    """Uzbek Cyrillic has ў, қ, ғ, ҳ; Russian does not. That is the whole test."""
    uzbek = profile_text("Ўлчов бирлиги ва ҳисоб-фактура рақами")
    russian = profile_text("Единица измерения и номер счета-фактуры")
    assert uzbek.dominant == SCRIPT_CYRILLIC
    assert uzbek.language == LANG_UZBEK_CYRILLIC
    assert russian.dominant == SCRIPT_CYRILLIC
    assert russian.language == LANG_RUSSIAN


def test_flags_mixed_script_blocks() -> None:
    mixed = profile_text("Поставщик: OLTIN VODIY SAVDO MChJ")
    assert mixed.mixed is True

    single = profile_text("Yetkazib beruvchi kompaniyasi")
    assert single.mixed is False


def test_apostrophe_variants_normalise_together() -> None:
    """`oʻ`, `o'` and `o‘` are the same letter as far as matching is concerned."""
    variants = ["oʻlchov", "o'lchov", "o‘lchov", "o`lchov"]
    normalised = {normalize_uzbek_latin(variant) for variant in variants}
    assert len(normalised) == 1


def test_confusable_folding_is_length_preserving() -> None:
    """Label offsets are computed on folded text, so length must not change."""
    for text in ["Поставщик: OLTIN", "СЧЁТ-ФАКТУРА № 12", "İstanbul", "straße", "ҚҚС (12%)"]:
        assert len(fold_confusables(text)) == len(text)
        assert len(lower_preserving_length(text)) == len(text)


def test_confusable_folding_maps_lookalikes_together() -> None:
    """Cyrillic С and Latin C are the same glyph; OCR picks whichever it likes."""
    cyrillic = fold_confusables(lower_preserving_length("СЕРВИС"))
    latin_mix = fold_confusables(lower_preserving_length("CЕРВИC"))
    assert cyrillic == latin_mix


def test_summarize_blocks_reports_language_mix() -> None:
    blocks = [
        {"text": "HISOB-FAKTURA", "language": LANG_UZBEK_LATIN},
        {"text": "Поставщик: ООО РОМАШКА", "language": LANG_RUSSIAN},
        {"text": "Ўлчов бирлиги", "language": LANG_UZBEK_CYRILLIC},
    ]
    summary = summarize_blocks(blocks)
    assert summary["mixed"] is True
    assert summary["script_count"] == 2
    assert set(summary["languages"]) == {LANG_UZBEK_LATIN, LANG_RUSSIAN, LANG_UZBEK_CYRILLIC}


def test_empty_text_is_safe() -> None:
    profile = profile_text("")
    assert profile.dominant in ("other", "digits")
    assert profile.mixed is False
