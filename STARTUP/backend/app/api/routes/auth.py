"""Registration, login, token refresh and team management."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    TokenError,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models import Company, User, UserRole
from app.schemas import (
    CompanyOut,
    CompanyUpdate,
    InviteRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


def _tokens_for(user: User) -> TokenResponse:
    claims = {"company_id": user.company_id, "role": user.role}
    return TokenResponse(
        access_token=create_token(user.id, "access", claims),
        refresh_token=create_token(user.id, "refresh"),
        expires_in=settings.access_token_ttl_minutes * 60,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    """Create a company workspace and its first (admin) user."""
    existing = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower()))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This email is already registered"
        )

    company = Company(name=payload.company_name, tin=payload.company_tin)
    db.add(company)
    db.flush()

    user = User(
        company_id=company.id,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("company registered", extra={"company_id": company.id, "user_id": user.id})
    return _tokens_for(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower()))
    # Same message and comparable work whether the email exists or not, so the
    # endpoint cannot be used to enumerate customers.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled")

    user.last_login_at = dt.datetime.now(dt.UTC)
    db.commit()
    return _tokens_for(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: DbSession) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return _tokens_for(user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


@router.get("/company", response_model=CompanyOut)
def get_company(user: CurrentUser, db: DbSession) -> Company:
    company = db.get(Company, user.company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.patch("/company", response_model=CompanyOut)
def update_company(payload: CompanyUpdate, user: AdminUser, db: DbSession) -> Company:
    company = db.get(Company, user.company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company


@router.get("/users", response_model=list[UserOut])
def list_users(user: CurrentUser, db: DbSession) -> list[User]:
    return list(db.scalars(select(User).where(User.company_id == user.company_id)).all())


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def invite_user(payload: InviteRequest, admin: AdminUser, db: DbSession) -> User:
    """Add a colleague to the workspace (Phase 2.6 "invite team member")."""
    if len(payload.password) < settings.password_min_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password must be at least {settings.password_min_length} characters",
        )
    existing = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower()))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This email is already registered"
        )

    user = User(
        company_id=admin.company_id,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
