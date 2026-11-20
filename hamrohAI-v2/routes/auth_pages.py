"""Login, role selection, logout. HTML pages + OAuth redirect targets.

Not under /api/v1 — these are browser redirect flows (Google, the Telegram
widget), not JSON endpoints.
"""

import secrets

from flask import (Blueprint, current_app, flash, redirect, render_template,
                    request, session, url_for)

from config import Config, features
from core.auth import current_user, login_required, login_user, logout_user
from identity_providers import dmed, google, telegram
from identity_providers.base import ProviderUnavailable
from repos import doctor_repo
from services import auth_service

bp = Blueprint("auth_pages", __name__, url_prefix="/auth")


def _post_login_redirect(user):
    if not user["role"]:
        return redirect(url_for("auth_pages.role"))
    return redirect(url_for("auth_pages.app_home"))


@bp.get("/login")
def login():
    if current_user() is not None:
        return _post_login_redirect(current_user())
    return render_template(
        "auth_login.html",
        google_enabled=google.is_configured(),
        telegram_enabled=telegram.is_configured(),
        telegram_bot_username=Config.TELEGRAM_BOT_USERNAME,
        dmed_enabled=features.enabled("dmed_auth"),
    )


@bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth_pages.login"))


# --- Google -----------------------------------------------------------

@bp.get("/google/start")
def google_start():
    if not google.is_configured():
        flash("Google orqali kirish hozircha sozlanmagan.")
        return redirect(url_for("auth_pages.login"))
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    return redirect(google.authorize_url(state))


@bp.get("/google/callback")
def google_callback():
    expected_state = session.pop("oauth_state", None)
    state = request.args.get("state")
    code = request.args.get("code")
    if not code or not state or state != expected_state:
        flash("Google orqali kirish muvaffaqiyatsiz tugadi. Qayta urinib ko'ring.")
        return redirect(url_for("auth_pages.login"))

    try:
        profile = google.fetch_profile(code)
    except google.GoogleAuthError:
        current_app.logger.exception("google login failed")
        flash("Google orqali kirish muvaffaqiyatsiz tugadi. Qayta urinib ko'ring.")
        return redirect(url_for("auth_pages.login"))

    user, _is_new = auth_service.login_or_create(profile)
    auth_service.sync_admin_flag(user)
    login_user(user["id"])
    return _post_login_redirect(user)


# --- Telegram -----------------------------------------------------------

@bp.get("/telegram/callback")
def telegram_callback():
    try:
        profile = telegram.verify_widget_payload(request.args.to_dict())
    except telegram.TelegramAuthError:
        current_app.logger.exception("telegram login failed")
        flash("Telegram orqali kirish muvaffaqiyatsiz tugadi. Qayta urinib ko'ring.")
        return redirect(url_for("auth_pages.login"))

    user, _is_new = auth_service.login_or_create(profile)
    auth_service.sync_admin_flag(user)
    login_user(user["id"])
    return _post_login_redirect(user)


# --- dmed (stub) ----------------------------------------------------------

@bp.get("/dmed/start")
def dmed_start():
    try:
        dmed.fetch_profile()
    except ProviderUnavailable as exc:
        flash(str(exc))
    return redirect(url_for("auth_pages.login"))


# --- Role selection + authenticated home ----------------------------------

@bp.get("/role")
@login_required
def role():
    user = current_user()
    if user["role"]:
        return redirect(url_for("auth_pages.app_home"))
    return render_template("auth_role.html", user=user)


@bp.post("/role")
@login_required
def set_role():
    role_value = request.form.get("role")
    auth_service.set_role(current_user()["id"], role_value)
    # Doctors already get bounced to /doctor/profile by app_home's own gate;
    # patients aren't gated (Module D), but still land on their profile
    # first thing so there's somewhere to fill in name/phone/diagnosis.
    if role_value == "patient":
        return redirect(url_for("patient_profile_pages.profile_form"))
    return redirect(url_for("auth_pages.app_home"))


@bp.get("/app")
@login_required
def app_home():
    user = current_user()
    if not user["role"]:
        return redirect(url_for("auth_pages.role"))
    if user["role"] == "doctor":
        doctor = doctor_repo.get_by_user(user["id"])
        if doctor is None or not doctor["profile_completed"]:
            return redirect(url_for("doctor_profile_pages.profile_form"))
    return render_template("app_home.html", user=user)
