"""Manual doctor verification. HTML pages, admin-only."""

from flask import Blueprint, flash, redirect, render_template, url_for

from core.auth import admin_required
from services import doctor_profile_service

bp = Blueprint("admin_pages", __name__, url_prefix="/admin")


@bp.get("/doctors")
@admin_required
def doctors():
    return render_template(
        "admin_doctors.html", pending=doctor_profile_service.list_pending_for_admin())


@bp.post("/doctors/<int:doctor_id>/verify")
@admin_required
def verify_doctor(doctor_id):
    doctor_profile_service.verify(doctor_id)
    flash("Shifokor tasdiqlandi.")
    return redirect(url_for("admin_pages.doctors"))
