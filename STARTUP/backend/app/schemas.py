"""Pydantic request/response models."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import settings
from app.db.models import UserRole

# --- Auth -------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    company_name: str = Field(min_length=2, max_length=255)
    company_tin: str | None = None

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        if len(value) < settings.password_min_length:
            raise ValueError(
                f"Password must be at least {settings.password_min_length} characters"
            )
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes when UTF-8 encoded")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class InviteRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: str = UserRole.OPERATOR

    @field_validator("role")
    @classmethod
    def check_role(cls, value: str) -> str:
        if value not in UserRole.ALL:
            raise ValueError(f"role must be one of {UserRole.ALL}")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None
    role: str
    company_id: int
    is_active: bool


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    tin: str | None
    address: str | None
    locale: str
    plan: str
    monthly_document_quota: int
    onec_config: dict[str, Any]


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    tin: str | None = None
    address: str | None = None
    phone: str | None = None
    locale: str | None = None
    onec_config: dict[str, Any] | None = None

    @field_validator("locale")
    @classmethod
    def check_locale(cls, value: str | None) -> str | None:
        if value is not None and value not in ("uz", "uz-Cyrl", "ru"):
            raise ValueError("locale must be one of: uz, uz-Cyrl, ru")
        return value


# --- Documents --------------------------------------------------------------

class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    mime_type: str
    size_bytes: int
    page_count: int | None
    status: str
    doc_type: str
    error_message: str | None
    processing_ms: int | None
    created_at: dt.datetime


class DocumentDetail(DocumentOut):
    extraction: ExtractionOut | None = None
    script_summary: dict[str, Any] | None = None
    ocr_provider: str | None = None


class UploadResult(BaseModel):
    accepted: list[DocumentOut]
    rejected: list[dict[str, str]]


class DocumentListResponse(BaseModel):
    items: list[DocumentOut]
    total: int
    limit: int
    offset: int


# --- Extractions ------------------------------------------------------------

class FieldOut(BaseModel):
    value: Any = None
    confidence: float = 0.0
    source: str = "none"
    raw_text: str | None = None
    page: int | None = None
    bbox: list[float] | None = None


class LineItemOut(BaseModel):
    index: int
    description: str | None = None
    unit: str | None = None
    quantity: str | None = None
    unit_price: str | None = None
    amount: str | None = None
    vat_rate: str | None = None
    vat_amount: str | None = None
    confidence: float = 0.0
    raw_text: str | None = None


class ExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    version: int
    strategy: str
    model_name: str | None
    fields: dict[str, FieldOut]
    line_items: list[dict[str, Any]]
    validation: dict[str, Any]
    overall_confidence: float
    total_amount: Decimal | None
    currency: str | None
    is_accepted: bool
    created_at: dt.datetime


class ReviewRequest(BaseModel):
    """Corrected values from the review screen.

    Only changed fields need to be sent; unchanged fields are carried forward
    from the machine extraction.
    """

    fields: dict[str, Any] = Field(default_factory=dict)
    line_items: list[dict[str, Any]] | None = None
    accept: bool = True


# --- Export -----------------------------------------------------------------

class ExportRequest(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=200)
    format: str = "commerceml_208"

    @field_validator("format")
    @classmethod
    def check_format(cls, value: str) -> str:
        if value != "commerceml_208":
            raise ValueError("Only commerceml_208 is supported in the MVP")
        return value


class ExportPreview(BaseModel):
    xml: str
    document_count: int
    problems: list[str]
    total_amount: Decimal | None


# --- Dashboard --------------------------------------------------------------

class DashboardStats(BaseModel):
    documents_this_month: int
    documents_total: int
    confirmed_this_month: int
    needs_review: int
    failed_this_month: int
    average_confidence: float
    average_processing_ms: int | None
    minutes_saved_this_month: int
    api_cost_usd_this_month: float
    quota: int
    quota_used_percent: float
    known_vendors: int
    top_vendors: list[dict[str, Any]]
    corrections_this_month: int
    correction_rate: float


DocumentDetail.model_rebuild()
