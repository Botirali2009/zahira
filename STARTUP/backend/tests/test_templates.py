"""Counterparty registry and template learning tests."""

from __future__ import annotations

from app.services.extract.base import ExtractionResult, FieldValue
from app.services.templates import KnownParty, apply_known_parties, similarity

VENDOR_TIN = "302145879"


def build_result(name: str, tin: str = VENDOR_TIN) -> ExtractionResult:
    result = ExtractionResult()
    result.set("vendor_name", FieldValue(value=name, confidence=0.95, source="label:yetkazib beruvchi"))
    result.set("vendor_tin", FieldValue(value=tin, confidence=0.95, source="label:stir"))
    return result


def registry(*names: str) -> dict[str, KnownParty]:
    return {VENDOR_TIN: KnownParty(tin=VENDOR_TIN, name=names[0], aliases=list(names), seen_count=8)}


def test_repairs_ocr_damaged_vendor_name() -> None:
    """`МЕБЕЛ` for `МЕБЕЛЬ` is a dropped character, not a different company."""
    result = build_result('ООО "СИФАТ МЕБЕЛ"')
    repairs = apply_known_parties(result, registry('ООО "СИФАТ МЕБЕЛЬ"'))

    assert result.value("vendor_name") == 'ООО "СИФАТ МЕБЕЛЬ"'
    assert repairs[0]["reason"] == "ocr_repair"


def test_matches_the_right_script_variant() -> None:
    """The same supplier invoices in Latin one month and Cyrillic the next."""
    latin = '"OLTIN VODIY SAVDO" MChJ'
    cyrillic = '"ОЛТИН ВОДИЙ САВДО" МЧЖ'

    result = build_result('"OLTIN VODIY SAVD0" MChJ')  # digit-for-letter OCR damage
    apply_known_parties(result, registry(latin, cyrillic))
    assert result.value("vendor_name") == latin

    result = build_result('"ОЛТИН ВОДИЙ САВД" МЧЖ')
    apply_known_parties(result, registry(latin, cyrillic))
    assert result.value("vendor_name") == cyrillic


def test_normalises_homoglyph_noise_to_the_stored_spelling() -> None:
    """Identical after folding: keep one spelling so 1C sees one counterparty."""
    result = build_result('ООО "АГРОМАШ CЕРВИС"')  # Latin C
    repairs = apply_known_parties(result, registry('ООО "АГРОМАШ СЕРВИС"'))

    assert result.value("vendor_name") == 'ООО "АГРОМАШ СЕРВИС"'
    assert repairs[0]["reason"] == "normalized"


def test_flags_a_genuinely_different_name_instead_of_overwriting() -> None:
    """Same STIR, unrelated name: a human decides, the machine does not guess."""
    result = build_result('ООО "СОВЕРШЕННО ДРУГАЯ КОМПАНИЯ"')
    repairs = apply_known_parties(result, registry('ООО "СИФАТ МЕБЕЛЬ"'))

    assert result.value("vendor_name") == 'ООО "СОВЕРШЕННО ДРУГАЯ КОМПАНИЯ"'
    assert result.get("vendor_name").confidence < 0.85
    assert repairs[0]["reason"] == "conflict"


def test_fills_a_missing_name_from_the_registry() -> None:
    result = ExtractionResult()
    result.set("vendor_tin", FieldValue(value=VENDOR_TIN, confidence=0.95))
    apply_known_parties(result, registry('ООО "СИФАТ МЕБЕЛЬ"'))

    assert result.value("vendor_name") == 'ООО "СИФАТ МЕБЕЛЬ"'


def test_unknown_tin_is_left_alone() -> None:
    result = build_result("Some New Supplier LLC", tin="999888777")
    repairs = apply_known_parties(result, registry('ООО "СИФАТ МЕБЕЛЬ"'))

    assert result.value("vendor_name") == "Some New Supplier LLC"
    assert repairs == []


def test_invalid_tin_never_triggers_a_repair() -> None:
    """A malformed STIR must not be used as a key into the registry."""
    result = build_result("Whatever", tin="123")
    assert apply_known_parties(result, registry('ООО "СИФАТ МЕБЕЛЬ"')) == []


def test_similarity_is_script_and_case_insensitive() -> None:
    assert similarity('ООО "АГРОМАШ"', 'ооо "агромаш"') == 1.0
    assert similarity("ABC Company", "XYZ Holdings") < 0.5


def test_learning_registers_vendor_and_activates_after_threshold(db_session) -> None:
    from app.core.config import settings
    from app.db.models import Company, Document, Extraction, VendorTemplate
    from app.services.templates import record_accepted_extraction

    company = Company(name="Test co")
    db_session.add(company)
    db_session.flush()

    for index in range(settings.template_learning_threshold):
        document = Document(
            company_id=company.id, original_filename=f"{index}.pdf", mime_type="application/pdf",
            size_bytes=10, sha256=f"{index:064d}", storage_key=f"k{index}",
        )
        db_session.add(document)
        db_session.flush()
        extraction = Extraction(
            document_id=document.id, version=1, strategy="rules",
            fields={
                "vendor_tin": {"value": VENDOR_TIN, "confidence": 1.0, "source": "human"},
                "vendor_name": {"value": '"OLTIN VODIY" MChJ', "confidence": 1.0,
                                "source": "label:yetkazib beruvchi"},
            },
            is_accepted=True,
        )
        db_session.add(extraction)
        db_session.flush()
        record_accepted_extraction(db_session, company.id, extraction)

    db_session.commit()
    template = db_session.query(VendorTemplate).filter_by(
        company_id=company.id, vendor_tin=VENDOR_TIN
    ).one()

    assert template.sample_count == settings.template_learning_threshold
    assert template.is_active is True
    assert '"OLTIN VODIY" MChJ' in template.hints["aliases"]
    # The labels that worked for this vendor are remembered for the next invoice.
    assert "yetkazib beruvchi" in template.hints["vendor_name"]["labels"]
