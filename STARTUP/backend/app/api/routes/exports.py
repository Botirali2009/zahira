"""1C export endpoints."""

from __future__ import annotations

import datetime as dt
import hashlib
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.logging import get_logger
from app.db.models import Company, Document, ExportLog, Extraction
from app.schemas import ExportPreview, ExportRequest
from app.services.export_1c import ExportError, export_extractions
from app.services.pipeline import result_from_extraction

router = APIRouter(prefix="/exports", tags=["exports"])
logger = get_logger(__name__)


def _collect(db, user, document_ids: list[int]) -> tuple[list[tuple], Company]:
    company = db.get(Company, user.company_id)
    documents = db.scalars(
        select(Document).where(
            Document.id.in_(document_ids), Document.company_id == user.company_id
        )
    ).all()

    found = {document.id for document in documents}
    missing = [document_id for document_id in document_ids if document_id not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documents not found: {missing}",
        )

    results = []
    for document in documents:
        extraction = db.scalar(
            select(Extraction)
            .where(Extraction.document_id == document.id)
            .order_by(Extraction.version.desc())
            .limit(1)
        )
        if extraction is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Document {document.id} ({document.original_filename}) "
                       "has not been processed yet",
            )
        results.append((result_from_extraction(extraction), document.id))
    return results, company


@router.post("/preview", response_model=ExportPreview)
def preview_export(payload: ExportRequest, user: CurrentUser, db: DbSession) -> ExportPreview:
    """Build the file and report any problems without recording an export.

    Lets the UI warn "3 of these 12 documents are missing a supplier STIR"
    before the accountant walks over to the machine running 1C.
    """
    results, company = _collect(db, user, payload.document_ids)
    try:
        xml_text, problems = export_extractions(results, company.onec_config if company else {})
    except ExportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    total = sum(
        (Decimal(str(result.value("total_amount"))) for result, _ in results
         if result.get("total_amount").is_present),
        Decimal("0"),
    )
    return ExportPreview(
        xml=xml_text, document_count=len(results), problems=problems, total_amount=total
    )


@router.post("/commerceml")
def export_commerceml(payload: ExportRequest, user: CurrentUser, db: DbSession) -> Response:
    """Download a CommerceML 2.08 file for import into 1C:Buxgalteriya 8.3."""
    results, company = _collect(db, user, payload.document_ids)
    try:
        xml_text, problems = export_extractions(results, company.onec_config if company else {})
    except ExportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if problems:
        # A file 1C would reject is worse than no file: the accountant would
        # discover it mid-import with the document open in front of them.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Export failed self-validation", "problems": problems},
        )

    payload_bytes = xml_text.encode("utf-8")
    total = sum(
        (Decimal(str(result.value("total_amount"))) for result, _ in results
         if result.get("total_amount").is_present),
        Decimal("0"),
    )
    db.add(ExportLog(
        company_id=user.company_id,
        user_id=user.id,
        document_ids=list(payload.document_ids),
        export_format=payload.format,
        document_count=len(results),
        total_amount=total,
        checksum=hashlib.sha256(payload_bytes).hexdigest(),
    ))
    db.commit()

    filename = f"hujjatai-1c-{dt.date.today().isoformat()}-{len(results)}.xml"
    logger.info(
        "1C export generated",
        extra={"company_id": user.company_id, "documents": len(results)},
    )
    return Response(
        content=payload_bytes,
        media_type="application/xml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/history")
def export_history(user: CurrentUser, db: DbSession, limit: int = 50) -> list[dict]:
    """Audit trail: what was handed to 1C, when, by whom."""
    logs = db.scalars(
        select(ExportLog)
        .where(ExportLog.company_id == user.company_id)
        .order_by(ExportLog.created_at.desc())
        .limit(min(limit, 200))
    ).all()
    return [
        {
            "id": log.id,
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "document_ids": log.document_ids,
            "document_count": log.document_count,
            "total_amount": str(log.total_amount) if log.total_amount is not None else None,
            "format": log.export_format,
            "checksum": log.checksum,
        }
        for log in logs
    ]
