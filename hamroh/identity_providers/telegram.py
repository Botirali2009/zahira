"""Telegram Login Widget verification.

No network call here — Telegram signs the payload itself and hands it back
as query parameters via a redirect, so "logging in" is just verifying that
signature (HMAC-SHA256 over the sorted fields, keyed by SHA256 of the bot
token — see https://core.telegram.org/widgets/login#checking-authorization)
and rejecting anything stale.
"""

import hashlib
import hmac
import sys
import time

from config import Config
from identity_providers.base import ExternalProfile, register

MAX_AUTH_AGE_SECONDS = 24 * 60 * 60


def is_configured():
    return bool(Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_BOT_USERNAME)


class TelegramAuthError(Exception):
    pass


def _data_check_string(fields):
    return "\n".join(
        "%s=%s" % (k, v) for k, v in sorted(fields.items()) if v is not None
    )


def verify_widget_payload(fields):
    """`fields` is the widget's redirect query string as a plain dict."""
    if not is_configured():
        raise TelegramAuthError("not_configured")

    fields = dict(fields)
    received_hash = fields.pop("hash", None)
    if not received_hash:
        raise TelegramAuthError("missing_hash")

    secret_key = hashlib.sha256(Config.TELEGRAM_BOT_TOKEN.encode()).digest()
    computed_hash = hmac.new(
        secret_key, _data_check_string(fields).encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        raise TelegramAuthError("bad_signature")

    try:
        auth_date = int(fields.get("auth_date", 0))
    except (TypeError, ValueError):
        raise TelegramAuthError("bad_auth_date")
    if time.time() - auth_date > MAX_AUTH_AGE_SECONDS:
        raise TelegramAuthError("expired")

    telegram_id = fields.get("id")
    if not telegram_id:
        raise TelegramAuthError("missing_id")

    full_name = " ".join(
        part for part in (fields.get("first_name"), fields.get("last_name")) if part
    ) or fields.get("username") or "Telegram user"

    return ExternalProfile(
        provider="telegram",
        external_id=str(telegram_id),
        full_name=full_name,
        phone=None,
        email=None,
        raw=fields,
    )


register("telegram", sys.modules[__name__])
