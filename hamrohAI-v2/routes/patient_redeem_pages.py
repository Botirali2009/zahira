"""A brand-new user redeeming a doctor's one-time invite code (Module C)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from core.auth import current_user, login_required
from core.errors import AppError
from services import invite_code_service

bp = Blueprint("patient_redeem_pages", __name__)


@bp.get("/patient/redeem-code")
@login_required
def redeem_form():
    return render_template("patient_redeem_code.html")


@bp.post("/patient/redeem-code")
@login_required
def redeem_submit():
    user = current_user()
    try:
        invite_code_service.redeem(user, request.form.get("code"))
    except AppError as exc:
        flash(exc.message)
        return redirect(url_for("patient_redeem_pages.redeem_form"))

    return redirect(url_for("auth_pages.app_home"))
