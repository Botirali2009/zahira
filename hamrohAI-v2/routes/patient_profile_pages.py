"""Patient self-signup profile + connecting to / disconnecting from a doctor."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from core.auth import current_user, role_required
from core.errors import AppError
from services import connect_code_service, patient_profile_service

bp = Blueprint("patient_profile_pages", __name__, url_prefix="/patient")


@bp.get("/profile")
@role_required("patient")
def profile_form():
    patient = patient_profile_service.get_or_create_for_user(current_user())
    return render_template(
        "patient_profile.html", detail=patient_profile_service.get_detail(patient["id"]))


@bp.post("/profile")
@role_required("patient")
def profile_submit():
    patient = patient_profile_service.get_or_create_for_user(current_user())
    try:
        patient_profile_service.update_profile(
            patient["id"], request.form.get("full_name"), request.form.get("phone"))
    except AppError as exc:
        flash(exc.message)
    else:
        flash("Profil saqlandi.")
    return redirect(url_for("patient_profile_pages.profile_form"))


@bp.post("/connect")
@role_required("patient")
def connect_doctor():
    patient = patient_profile_service.get_or_create_for_user(current_user())
    try:
        connect_code_service.link_patient(patient, request.form.get("code"))
    except AppError as exc:
        flash(exc.message)
    else:
        flash("Shifokorga muvaffaqiyatli ulandingiz.")
    return redirect(url_for("patient_profile_pages.profile_form"))


@bp.post("/disconnect")
@role_required("patient")
def disconnect_doctor():
    patient = patient_profile_service.get_or_create_for_user(current_user())
    connect_code_service.unlink(patient)
    flash("Shifokordan uzildingiz. Tarixiy ma'lumotlaringiz saqlanib qoldi.")
    return redirect(url_for("patient_profile_pages.profile_form"))
