"""Password hashing and JWT issuance."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]

# bcrypt truncates silently at 72 bytes; reject longer input rather than let two
# different passwords hash to the same value.
MAX_PASSWORD_BYTES = 72


class TokenError(Exception):
    """Raised when a token is missing, expired, malformed or of the wrong type."""


def hash_password(password: str) -> str:
    _check_password_length(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _check_password_length(password: str) -> None:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be at most {MAX_PASSWORD_BYTES} bytes when UTF-8 encoded"
        )


def create_token(
    subject: str | int,
    token_type: TokenType = "access",
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = dt.datetime.now(dt.UTC)
    if token_type == "access":
        expires = now + dt.timedelta(minutes=settings.access_token_ttl_minutes)
    else:
        expires = now + dt.timedelta(days=settings.refresh_token_ttl_days)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: TokenType = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise TokenError("Token is invalid") from exc

    if payload.get("type") != expected_type:
        raise TokenError(f"Expected a {expected_type} token")
    if not payload.get("sub"):
        raise TokenError("Token has no subject")
    return payload
