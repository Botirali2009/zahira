"""Turning a provider's `ExternalProfile` into a session.

`login_or_create` is the one place that decides "have we seen this identity
before": known -> load its user; unknown -> create a new user (role unset,
chosen next on /auth/role) plus the identity row that will match it next
time this same provider+external_id comes back.
"""

import json

from config import Config
from core.errors import ValidationError
from repos import user_identity_repo, user_repo

VALID_ROLES = ("patient", "doctor")


def _as_dict(row):
    return {k: row[k] for k in row.keys()}


def login_or_create(profile):
    """profile: identity_providers.base.ExternalProfile.

    Returns (user, is_new_user).
    """
    raw_json = json.dumps(profile.raw, ensure_ascii=False, default=str)

    identity = user_identity_repo.find(profile.provider, profile.external_id)
    if identity is not None:
        user_identity_repo.update_raw_profile(identity["id"], raw_json)
        return _as_dict(user_repo.get(identity["user_id"])), False

    user_id = user_repo.create(
        role=None, full_name=profile.full_name, phone=profile.phone,
        email=profile.email,
    )
    user_identity_repo.create(
        user_id, profile.provider, profile.external_id, raw_profile_json=raw_json,
    )
    return _as_dict(user_repo.get(user_id)), True


def set_role(user_id, role):
    if role not in VALID_ROLES:
        raise ValidationError("Rol noto'g'ri.")
    user_repo.set_role(user_id, role)


def sync_admin_flag(user):
    """Email-allowlist admin bootstrap (Module B) — no admin UI grants this,
    it's re-checked on every login against ADMIN_EMAILS in .env."""
    if not user.get("email"):
        return
    admin_emails = {
        e.strip().lower() for e in Config.ADMIN_EMAILS.split(",") if e.strip()
    }
    should_be_admin = user["email"].lower() in admin_emails
    if bool(user.get("is_admin")) != should_be_admin:
        user_repo.set_admin(user["id"], should_be_admin)
