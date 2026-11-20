"""Upload, list, inspect, review and re-process documents."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select

from app.api.deps import CompanyDocument, CurrentUser, DbSession
from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import Document, DocumentStatus, Extraction, OcrResult
from app.db.session import session_scope
from app.schemas import (
    DocumentDetail,
    DocumentListResponse,
    DocumentOut,
    ExtractionOut,
    ReviewRequest,
    UploadResult,
)
from app.services import pipeline
from app.services.storage import build_storage_key, compute_sha256, get_storage

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger(__name__)


def _enqueue(document_id: int, background: BackgroundTasks) -> None:
    """Hand a document to the worker.

    `inline` runs it in a FastAPI background task with its own session, which is
    enough for pilot volume. `celery` is the production path.
    """
    if settings.queue_backend == "celery":
        from app.workers.tasks import process_document_task  # noqa: PLC0415

        process_document_task.delay(document_id)
        return

    def _run() -> None:
        with session_scope() as db:
            pipeline.process_document(db, document_id)

    background.add_task(_run)


@router.post("/upload", response_model=UploadResult, status_code=status.HTTP_202_ACCEPTED)
def upload_documents(
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
) -> UploadResult:
    """Accept a batch of scans and queue them for processing.

    Partial success is deliberate: one oversized file in a batch of twenty must
    not reject the other nineteen, because the accountant scanned them all in
    one pass and will not know which one to remove.
    """
    if len(files) > settings.max_batch_files:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"At most {settings.max_batch_files} files per upload",
        )

    accepted: list[Document] = []
    rejected: list[dict[str, str]] = []
    storage = get_storage()

    for upload in files:
        filename = upload.filename or "document"
        data = upload.file.read()

        if not data:
            rejected.append({"filename": filename, "reason": "File is empty"})
            continue
        if len(data) > settings.max_upload_bytes:
            rejected.append({
                "filename": filename,
                "reason": f"File is larger than {settings.max_upload_mb} MB",
            })
            continue

        mime_type = upload.content_type or "application/octet-stream"
        if mime_type not in settings.allowed_mime_list:
            rejected.append({
                "filename": filename,
                "reason": f"Unsupported file type {mime_type}. Upload PDF, JPG, PNG or TIFF.",
            })
            continue

        sha256 = compute_sha256(data)
        storage_key = build_storage_key(user.company_id, sha256, filename)
        try:
            storage.save(storage_key, data)
        except Exception as exc:
            logger.exception("failed to store upload", extra={"filename": filename})
            rejected.append({"filename": filename, "reason": f"Could not store file: {exc}"})
            continue

        document = Document(
            company_id=user.company_id,
            uploaded_by_id=user.id,
            original_filename=filename[:500],
            mime_type=mime_type,
            size_bytes=len(data),
            sha256=sha256,
            storage_key=storage_key,
            status=DocumentStatus.PENDING,
        )
        db.add(document)
        accepted.append(document)

    db.commit()
    for document in accepted:
        db.refresh(document)
        _enqueue(document.id, background)

    logger.info(
        "upload received",
        extra={"company_id": user.company_id, "accepted": len(accepted), "rejected": len(rejected)},
    )
    return UploadResult(
        accepted=[DocumentOut.model_validate(document) for document in accepted],
        rejected=rejected,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    user: CurrentUser,
    db: DbSession,
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> DocumentListResponse:
    query = select(Document).where(Document.company_id == user.company_id)
    count_query = select(func.count(Document.id)).where(Document.company_id == user.company_id)

    if status_filter:
        if status_filter not in DocumentStatus.ALL:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"status must be one of {DocumentStatus.ALL}",
            )
        query = query.where(Document.status == status_filter)
        count_query = count_query.where(Document.status == status_filter)

    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(func.lower(Document.original_filename).like(pattern))
        count_query = count_query.where(func.lower(Document.original_filename).like(pattern))

    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(Document.created_at.desc(), Document.id.desc()).limit(limit).offset(offset)
    ).all()

    return DocumentListResponse(
        items=[DocumentOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document: CompanyDocument, db: DbSession) -> DocumentDetail:
    extraction = _latest_extraction(db, document.id)
    ocr = db.scalar(
        select(OcrResult)
        .where(OcrResult.document_id == document.id)
        .order_by(OcrResult.id.desc())
        .limit(1)
    )
    detail = DocumentDetail.model_validate(document)
    detail.extraction = ExtractionOut.model_validate(extraction) if extraction else None
    detail.script_summary = ocr.script_summary if ocr else None
    detail.ocr_provider = ocr.provider if ocr else None
    return detail


@router.get("/{document_id}/file")
def download_original(document: CompanyDocument) -> Response:
    """Serve the original scan for the side-by-side review screen."""
    try:
        data = get_storage().load(document.storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stored file is missing"
        ) from exc
    return Response(
        content=data,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{document.original_filename}"',
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.get("/{document_id}/text")
def get_ocr_text(document: CompanyDocument, db: DbSession) -> dict:
    """Raw OCR output — the ground truth when debugging a bad extraction."""
    ocr = db.scalar(
        select(OcrResult)
        .where(OcrResult.document_id == document.id)
        .order_by(OcrResult.id.desc())
        .limit(1)
    )
    if ocr is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="This document has not been processed yet"
        )
    return {
        "provider": ocr.provider,
        "text": ocr.raw_text,
        "blocks": ocr.blocks,
        "script_summary": ocr.script_summary,
        "mean_confidence": ocr.mean_confidence,
        "from_cache": ocr.from_cache,
    }


@router.get("/{document_id}/extractions", response_model=list[ExtractionOut])
def list_extractions(document: CompanyDocument, db: DbSession) -> list[Extraction]:
    """Full version history: what the machine said, then what the human said."""
    return list(
        db.scalars(
            select(Extraction)
            .where(Extraction.document_id == document.id)
            .order_by(Extraction.version)
        ).all()
    )


@router.post("/{document_id}/review", response_model=ExtractionOut)
def review_document(
    payload: ReviewRequest, document: CompanyDocument, user: CurrentUser, db: DbSession
) -> Extraction:
    """Save the accountant's corrections and confirm the document."""
    extraction = _latest_extraction(db, document.id)
    if extraction is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document has no extraction to review yet",
        )
    return pipeline.apply_review(
        db,
        extraction,
        edits=payload.fields,
        line_items=payload.line_items,
        user_id=user.id,
        accept=payload.accept,
    )


@router.post("/{document_id}/reprocess", response_model=DocumentOut,
             status_code=status.HTTP_202_ACCEPTED)
def reprocess_document(
    document: CompanyDocument, db: DbSession, background: BackgroundTasks
) -> Document:
    """Re-run the pipeline, e.g. after a lexicon or template improvement."""
    document.status = DocumentStatus.PENDING
    document.error_message = None
    db.commit()
    db.refresh(document)
    _enqueue(document.id, background)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document: CompanyDocument, db: DbSession) -> Response:
    """Delete a document and its stored image.

    Uzbek tax rules require records to be kept for five years, so this is for
    mistakes (wrong file uploaded), not routine cleanup — the audit trail of
    what was exported to 1C lives in export_logs and is unaffected.
    """
    try:
        get_storage().delete(document.storage_key)
    except Exception as exc:
        logger.warning("could not delete stored file", extra={"error": str(exc)})
    db.delete(document)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _latest_extraction(db, document_id: int) -> Extraction | None:
    return db.scalar(
        select(Extraction)
        .where(Extraction.document_id == document_id)
        .order_by(Extraction.version.desc())
        .limit(1)
    )


def _month_start() -> dt.datetime:
    now = dt.datetime.now(dt.UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
