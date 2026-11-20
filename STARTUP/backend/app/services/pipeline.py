"""Document processing pipeline.

    upload -> preprocess -> OCR -> script detection -> extraction ->
    counterparty registry -> validation -> stored extraction -> review

Every stage is recorded on the document so a support engineer can answer "why
did document 4821 come out wrong" from the database alone, without re-running
anything.
"""

from __future__ import annotations

import datetime as dt
import time
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import document_id_var, get_logger
from app.db.models import (
    Correction,
    Document,
    DocumentStatus,
    Extraction,
    OcrResult,
)
from app.services import templates as template_service
from app.services.extract.base import (
    INVOICE_FIELDS,
    ExtractionContext,
    ExtractionResult,
    FieldValue,
)
from app.services.extract.registry import extract_fields
from app.services.ocr.base import OcrError
from app.services.ocr.registry import run_ocr
from app.services.preprocess import is_image, page_count_of_pdf, preprocess_image
from app.services.script_detect import annotate_blocks, summarize_blocks
from app.services.storage import get_storage
from app.services.validate import validate_extraction

logger = get_logger(__name__)

# A document whose overall confidence is below this lands in "needs review"
# rather than "ready", so the accountant's queue is sorted by where their
# attention is actually needed.
REVIEW_THRESHOLD = 0.85


def process_document(db: Session, document_id: int) -> Document:
    """Run the full pipeline for one uploaded document."""
    token = document_id_var.set(document_id)
    started = time.perf_counter()
    document = db.get(Document, document_id)
    if document is None:
        document_id_var.reset(token)
        raise ValueError(f"Document {document_id} not found")

    document.status = DocumentStatus.PROCESSING
    document.processing_started_at = dt.datetime.now(dt.UTC)
    document.error_message = None
    db.commit()

    try:
        ocr_result = _run_ocr_stage(db, document)
        extraction = _run_extraction_stage(db, document, ocr_result)

        document.doc_type = extraction.fields.get("_doc_type", {}).get("value", document.doc_type) \
            if isinstance(extraction.fields.get("_doc_type"), dict) else document.doc_type
        document.status = (
            DocumentStatus.READY
            if extraction.overall_confidence >= REVIEW_THRESHOLD
            and not (extraction.validation or {}).get("errors")
            else DocumentStatus.NEEDS_REVIEW
        )
    except OcrError as exc:
        document.status = DocumentStatus.FAILED
        document.error_message = str(exc)
        logger.warning("document failed at OCR", extra={"error": str(exc)})
    except Exception as exc:
        document.status = DocumentStatus.FAILED
        document.error_message = f"Processing failed: {exc}"
        logger.exception("document processing crashed")
    finally:
        document.processing_finished_at = dt.datetime.now(dt.UTC)
        document.processing_ms = int((time.perf_counter() - started) * 1000)
        db.commit()
        db.refresh(document)
        document_id_var.reset(token)

    logger.info(
        "document processed",
        extra={"status": document.status, "processing_ms": document.processing_ms},
    )
    return document


def _run_ocr_stage(db: Session, document: Document) -> OcrResult:
    """OCR the document, reusing a cached result for identical file content."""
    cached = db.scalar(
        select(OcrResult)
        .join(Document, OcrResult.document_id == Document.id)
        .where(
            Document.company_id == document.company_id,
            Document.sha256 == document.sha256,
            Document.id != document.id,
        )
        .order_by(OcrResult.id.desc())
        .limit(1)
    )
    if cached is not None:
        # The same scan uploaded twice must not be paid for twice.
        logger.info("reusing cached OCR result", extra={"source_ocr_id": cached.id})
        reused = OcrResult(
            document_id=document.id,
            provider=cached.provider,
            raw_text=cached.raw_text,
            blocks=cached.blocks,
            script_summary=cached.script_summary,
            mean_confidence=cached.mean_confidence,
            duration_ms=0,
            from_cache=True,
        )
        db.add(reused)
        db.commit()
        db.refresh(reused)
        return reused

    data = get_storage().load(document.storage_key)
    if is_image(document.mime_type):
        data = preprocess_image(data)
    elif document.mime_type == "application/pdf" and document.page_count is None:
        document.page_count = page_count_of_pdf(data)

    output = run_ocr(data, document.mime_type)
    blocks = annotate_blocks([block.to_dict() for block in output.blocks])
    summary = summarize_blocks(blocks)

    result = OcrResult(
        document_id=document.id,
        provider=output.provider,
        raw_text=output.text,
        blocks=blocks,
        script_summary=summary,
        mean_confidence=output.mean_confidence,
        duration_ms=output.duration_ms,
        from_cache=False,
    )
    if document.page_count is None and output.page_count:
        document.page_count = output.page_count

    db.add(result)
    db.commit()
    db.refresh(result)
    logger.info(
        "ocr complete",
        extra={"provider": output.provider, "blocks": len(blocks),
               "mixed_script": summary.get("mixed"), "duration_ms": output.duration_ms},
    )
    return result


def _run_extraction_stage(db: Session, document: Document, ocr_result: OcrResult) -> Extraction:
    known = template_service.load_known_parties(db, document.company_id)
    context = ExtractionContext(
        blocks=ocr_result.blocks or [],
        script_summary=ocr_result.script_summary or {},
        default_currency=settings.default_currency,
        vat_rate_percent=settings.vat_rate_percent,
        company_tin=document.company.tin if document.company else None,
    )

    result = extract_fields(ocr_result.raw_text, context)
    repairs = template_service.apply_known_parties(result, known)
    report = validate_extraction(result, vat_rate_percent=settings.vat_rate_percent)

    validation = report.to_dict()
    if repairs:
        validation["registry_repairs"] = repairs
    if result.warnings:
        validation["warnings"] = validation.get("warnings", []) + [
            {"code": "extractor_warning", "message": warning, "fields": []}
            for warning in result.warnings
        ]

    extraction = Extraction(
        document_id=document.id,
        version=_next_version(db, document.id),
        strategy=result.strategy,
        model_name=result.model_name,
        fields=_serialize_fields(result),
        line_items=result.line_items_to_dict(),
        validation=validation,
        overall_confidence=result.overall_confidence,
        total_amount=_decimal_or_none(result, "total_amount"),
        currency=str(result.value("currency") or settings.default_currency),
        vendor_tin=str(result.value("vendor_tin")) if result.get("vendor_tin").is_present else None,
        duration_ms=result.duration_ms,
        cost_usd=result.cost_usd,
    )
    db.add(extraction)
    if result.doc_type and result.doc_type != "unknown":
        document.doc_type = result.doc_type
    db.commit()
    db.refresh(extraction)

    logger.info(
        "extraction complete",
        extra={"strategy": result.strategy, "confidence": result.overall_confidence,
               "errors": len(report.errors), "warnings": len(report.warnings),
               "cost_usd": result.cost_usd},
    )
    return extraction


def apply_review(
    db: Session,
    extraction: Extraction,
    edits: dict[str, Any],
    line_items: list[dict[str, Any]] | None,
    user_id: int | None,
    accept: bool = True,
) -> Extraction:
    """Store a reviewed version of an extraction and learn from the differences.

    The machine's version is never overwritten. A new version is written with
    the human's values, and one Correction row is recorded per changed field —
    those rows are the labelled training data the whole data strategy rests on.
    """
    document = db.get(Document, extraction.document_id)
    if document is None:
        raise ValueError("Extraction has no document")

    previous_fields = dict(extraction.fields or {})
    new_fields = dict(previous_fields)
    corrections: list[Correction] = []

    for name, raw_value in (edits or {}).items():
        if name not in INVOICE_FIELDS:
            continue
        old_entry = previous_fields.get(name) or {}
        old_value = old_entry.get("value")
        new_value = _normalize_edit(name, raw_value)
        if _same_value(old_value, new_value):
            continue

        new_fields[name] = {
            "value": new_value,
            # A human typed it: this is ground truth, not an estimate.
            "confidence": 1.0,
            "source": "human",
            "raw_text": old_entry.get("raw_text"),
            "page": old_entry.get("page"),
            "bbox": old_entry.get("bbox"),
        }
        corrections.append(Correction(
            user_id=user_id,
            field_path=name,
            old_value=None if old_value is None else str(old_value),
            new_value=None if new_value is None else str(new_value),
            old_confidence=old_entry.get("confidence"),
        ))

    reviewed = Extraction(
        document_id=extraction.document_id,
        version=_next_version(db, extraction.document_id),
        strategy="human" if corrections else f"{extraction.strategy}+confirmed",
        model_name=extraction.model_name,
        fields=new_fields,
        line_items=line_items if line_items is not None else list(extraction.line_items or []),
        validation=dict(extraction.validation or {}),
        overall_confidence=1.0 if accept else extraction.overall_confidence,
        total_amount=_decimal_from_payload(new_fields.get("total_amount")),
        currency=str((new_fields.get("currency") or {}).get("value") or extraction.currency),
        vendor_tin=(new_fields.get("vendor_tin") or {}).get("value"),
        duration_ms=0,
        cost_usd=0.0,
        is_accepted=accept,
    )
    db.add(reviewed)
    db.flush()

    for correction in corrections:
        correction.extraction_id = reviewed.id
        db.add(correction)

    if accept:
        document.status = DocumentStatus.CONFIRMED
        template_service.record_accepted_extraction(db, document.company_id, reviewed)

    db.commit()
    db.refresh(reviewed)
    logger.info(
        "review applied",
        extra={"document_id": document.id, "corrections": len(corrections), "accepted": accept},
    )
    return reviewed


# --- helpers ----------------------------------------------------------------

def _next_version(db: Session, document_id: int) -> int:
    current = db.scalar(
        select(Extraction.version)
        .where(Extraction.document_id == document_id)
        .order_by(Extraction.version.desc())
        .limit(1)
    )
    return (current or 0) + 1


def _serialize_fields(result: ExtractionResult) -> dict[str, Any]:
    allowed = set(INVOICE_FIELDS) | {"vat_rate"}
    return {name: entry.to_dict() for name, entry in result.fields.items() if name in allowed}


def _decimal_or_none(result: ExtractionResult, name: str) -> Decimal | None:
    entry = result.get(name)
    if not entry.is_present:
        return None
    try:
        return Decimal(str(entry.value))
    except Exception:
        return None


def _decimal_from_payload(payload: dict[str, Any] | None) -> Decimal | None:
    if not payload:
        return None
    try:
        return Decimal(str(payload.get("value")))
    except Exception:
        return None


def _normalize_edit(name: str, value: Any) -> Any:
    if value is None or value == "":
        return None
    if name == "invoice_date":
        if isinstance(value, dt.date):
            return value.isoformat()
        return str(value)
    return str(value).strip() if isinstance(value, str) else value


def _same_value(old: Any, new: Any) -> bool:
    if old is None and new is None:
        return True
    return str(old) == str(new)


def result_from_extraction(extraction: Extraction) -> ExtractionResult:
    """Rebuild an in-memory result from a stored row (for export)."""
    return ExtractionResult(
        fields={
            name: FieldValue.from_dict(payload)
            for name, payload in (extraction.fields or {}).items()
        },
        line_items=ExtractionResult.from_stored({}, extraction.line_items or []).line_items,
        strategy=extraction.strategy,
    )
