"""Usage dashboard.

The numbers here are not vanity metrics: the chief accountant has to justify the
subscription to their director every renewal (deep-dive §1, step 4 of the
decision process). "Documents processed" and "hours saved" are the two figures
that argument is made with, so they are computed from real activity, not
estimated.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.db.models import (
    Company,
    Correction,
    Document,
    DocumentStatus,
    Extraction,
    VendorTemplate,
)
from app.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Baseline from the customer research: 15-20 minutes of manual entry per
# document (executive summary). The conservative end is used deliberately —
# an inflated saving figure is the first thing a sceptical director attacks.
MINUTES_SAVED_PER_DOCUMENT = 15


def _month_start() -> dt.datetime:
    now = dt.datetime.now(dt.UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@router.get("", response_model=DashboardStats)
def get_dashboard(user: CurrentUser, db: DbSession) -> DashboardStats:
    company_id = user.company_id
    since = _month_start()

    def count_documents(*conditions) -> int:
        return db.scalar(
            select(func.count(Document.id)).where(Document.company_id == company_id, *conditions)
        ) or 0

    documents_total = count_documents()
    documents_this_month = count_documents(Document.created_at >= since)
    confirmed_this_month = count_documents(
        Document.created_at >= since, Document.status == DocumentStatus.CONFIRMED
    )
    needs_review = count_documents(Document.status == DocumentStatus.NEEDS_REVIEW)
    failed_this_month = count_documents(
        Document.created_at >= since, Document.status == DocumentStatus.FAILED
    )

    average_confidence = db.scalar(
        select(func.avg(Extraction.overall_confidence))
        .join(Document, Extraction.document_id == Document.id)
        .where(Document.company_id == company_id, Extraction.created_at >= since)
    ) or 0.0

    average_processing = db.scalar(
        select(func.avg(Document.processing_ms)).where(
            Document.company_id == company_id,
            Document.created_at >= since,
            Document.processing_ms.isnot(None),
        )
    )

    api_cost = db.scalar(
        select(func.sum(Extraction.cost_usd))
        .join(Document, Extraction.document_id == Document.id)
        .where(Document.company_id == company_id, Extraction.created_at >= since)
    ) or 0.0

    corrections_this_month = db.scalar(
        select(func.count(Correction.id))
        .join(Extraction, Correction.extraction_id == Extraction.id)
        .join(Document, Extraction.document_id == Document.id)
        .where(Document.company_id == company_id, Correction.created_at >= since)
    ) or 0

    known_vendors = db.scalar(
        select(func.count(VendorTemplate.id)).where(VendorTemplate.company_id == company_id)
    ) or 0

    top_vendors = [
        {"vendor_tin": row.vendor_tin, "vendor_name": row.vendor_name,
         "documents": row.sample_count, "template_active": row.is_active}
        for row in db.execute(
            select(VendorTemplate)
            .where(VendorTemplate.company_id == company_id)
            .order_by(VendorTemplate.sample_count.desc())
            .limit(5)
        ).scalars()
    ]

    company = db.get(Company, company_id)
    quota = company.monthly_document_quota if company else 0

    processed_this_month = documents_this_month - failed_this_month
    return DashboardStats(
        documents_this_month=documents_this_month,
        documents_total=documents_total,
        confirmed_this_month=confirmed_this_month,
        needs_review=needs_review,
        failed_this_month=failed_this_month,
        average_confidence=round(float(average_confidence), 4),
        average_processing_ms=int(average_processing) if average_processing else None,
        minutes_saved_this_month=max(processed_this_month, 0) * MINUTES_SAVED_PER_DOCUMENT,
        api_cost_usd_this_month=round(float(api_cost), 4),
        quota=quota,
        quota_used_percent=round(documents_this_month / quota * 100, 1) if quota else 0.0,
        known_vendors=known_vendors,
        top_vendors=top_vendors,
        # Correction rate is the honest accuracy signal from production: the
        # share of confirmed documents the human had to change.
        corrections_this_month=corrections_this_month,
        correction_rate=round(corrections_this_month / confirmed_this_month, 4)
        if confirmed_this_month else 0.0,
    )
