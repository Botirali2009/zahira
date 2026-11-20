"""SQLAlchemy models.

Design notes
------------
* A `Company` is the tenant boundary. Every document, extraction and template
  belongs to exactly one company; there is no cross-company read path.
* Extractions are versioned rather than mutated. Version 1 is what the machine
  produced; later versions record what the human accepted. Keeping both is what
  makes the correction feedback loop (and any future accuracy audit) possible.
* Money is stored as Numeric(18, 2). UZS amounts are large — a 2 billion soʻm
  invoice is ordinary — so 32-bit floats are not an option.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# JSONB on PostgreSQL (indexable, typed), plain JSON on SQLite for local dev.
JSONType = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# --- Enumerated values (kept as plain strings for painless migrations) -------

class DocumentStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    ALL = (PENDING, PROCESSING, READY, NEEDS_REVIEW, CONFIRMED, FAILED)


class DocumentType:
    INVOICE = "invoice"          # hisob-faktura / счёт-фактура
    WAYBILL = "waybill"          # TTN
    CONTRACT = "contract"
    TAX_FORM = "tax_form"
    BANK_STATEMENT = "bank_statement"
    UNKNOWN = "unknown"
    ALL = (INVOICE, WAYBILL, CONTRACT, TAX_FORM, BANK_STATEMENT, UNKNOWN)


class UserRole:
    ADMIN = "admin"
    OPERATOR = "operator"
    ALL = (ADMIN, OPERATOR)


# --- Tables -----------------------------------------------------------------

class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tin: Mapped[str | None] = mapped_column(String(20), index=True)
    address: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(50))

    # UI language for the workspace: "uz" (Latin), "uz-Cyrl" or "ru".
    locale: Mapped[str] = mapped_column(String(10), default="uz", nullable=False)
    plan: Mapped[str] = mapped_column(String(30), default="founding", nullable=False)
    monthly_document_quota: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)

    # Per-customer 1C mapping: configuration name, chart-of-accounts codes,
    # default warehouse/organisation. See services/export_1c.py.
    onec_config: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)

    users: Mapped[list[User]] = relationship(back_populates="company", cascade="all, delete-orphan")
    documents: Mapped[list[Document]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=UserRole.OPERATOR, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped[Company] = relationship(back_populates="users")

    __table_args__ = (
        CheckConstraint(f"role IN {UserRole.ALL}", name="ck_users_role"),
    )


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    # SHA-256 of the file bytes. Same hash inside a company means we can reuse
    # the OCR result instead of paying for the page again.
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[str] = mapped_column(
        String(20), default=DocumentStatus.PENDING, nullable=False, index=True
    )
    doc_type: Mapped[str] = mapped_column(String(30), default=DocumentType.UNKNOWN, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    processing_started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    processing_finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    processing_ms: Mapped[int | None] = mapped_column(Integer)

    company: Mapped[Company] = relationship(back_populates="documents")
    ocr_results: Mapped[list[OcrResult]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    extractions: Mapped[list[Extraction]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="Extraction.version"
    )

    __table_args__ = (
        CheckConstraint(f"status IN {DocumentStatus.ALL}", name="ck_documents_status"),
        Index("ix_documents_company_status", "company_id", "status"),
        Index("ix_documents_company_sha", "company_id", "sha256"),
    )

    @property
    def latest_extraction(self) -> Extraction | None:
        return self.extractions[-1] if self.extractions else None


class OcrResult(TimestampMixin, Base):
    __tablename__ = "ocr_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # [{text, page, bbox, script, confidence}, ...] in reading order.
    blocks: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list, nullable=False)
    # {"latin": 0.62, "cyrillic": 0.31, "digits": 0.07, "dominant": "latin", "mixed": true}
    script_summary: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    mean_confidence: Mapped[float | None] = mapped_column(Float)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    document: Mapped[Document] = relationship(back_populates="ocr_results")


class Extraction(TimestampMixin, Base):
    __tablename__ = "extractions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # "rules", "llm", "template:<id>" or "human" for a reviewer-accepted version.
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100))

    # {"vendor_name": {"value": ..., "confidence": 0.94, "source": "label:yetkazib beruvchi"}}
    fields: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    line_items: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list, nullable=False)
    # {"errors": [...], "warnings": [...], "checks": {...}}
    validation: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)

    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    vendor_tin: Mapped[str | None] = mapped_column(String(20), index=True)

    duration_ms: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    document: Mapped[Document] = relationship(back_populates="extractions")
    corrections: Mapped[list[Correction]] = relationship(
        back_populates="extraction", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_extraction_document_version"),
    )


class Correction(TimestampMixin, Base):
    """One human edit to one field. The training signal of the whole product."""

    __tablename__ = "corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    extraction_id: Mapped[int] = mapped_column(
        ForeignKey("extractions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # "vendor_name" or "line_items[2].quantity"
    field_path: Mapped[str] = mapped_column(String(120), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    old_confidence: Mapped[float | None] = mapped_column(Float)

    extraction: Mapped[Extraction] = relationship(back_populates="corrections")


class VendorTemplate(TimestampMixin, Base):
    """Learned layout for one vendor, built from accepted corrections.

    Once a vendor's template is confident enough the pipeline stops paying for
    LLM inference on that vendor's invoices — this is the margin story in the
    financial model, and the reason accuracy climbs with usage.
    """

    __tablename__ = "vendor_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_tin: Mapped[str] = mapped_column(String(20), nullable=False)
    vendor_name: Mapped[str | None] = mapped_column(String(255))

    # {"vendor_name": {"labels": ["yetkazib beruvchi"], "line_offset": 0}, ...}
    hints: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_accuracy: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint("company_id", "vendor_tin", name="uq_template_company_vendor"),
    )


class ExportLog(TimestampMixin, Base):
    """Audit trail of what was handed to 1C, for tax-dispute traceability."""

    __tablename__ = "export_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    document_ids: Mapped[list[int]] = mapped_column(JSONType, default=list, nullable=False)
    export_format: Mapped[str] = mapped_column(String(30), default="commerceml_208", nullable=False)
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    checksum: Mapped[str | None] = mapped_column(String(64))
