"""Doctor profile completion + protected document downloads. HTML pages."""

from flask import (Blueprint, abort, flash, redirect, request,
                    render_template, send_from_directory, url_for)

from config import Config
from core.auth import Forbidden, current_user, role_required
from core.errors import AppError
from repos import doctor_document_repo, doctor_repo, specialty_repo
from services import connect_code_service, doctor_profile_service

bp = Blueprint("doctor_profile_pages", __name__)


@bp.get("/doctor/profile")
@role_required("doctor")
def profile_form():
    doctor = doctor_profile_service.get_or_create_for_user(current_user())
    detail = doctor_profile_service.get_detail(doctor["id"])

    connect_code = None
    if detail["doctor"]["profile_completed"]:
        connect_code, _expires = connect_code_service.get_or_create(doctor)

    return render_template(
        "doctor_profile_form.html",
        detail=detail,
        all_specialties=specialty_repo.list_all(),
        selected_ids={s["id"] for s in detail["specialties"]},
        connect_code=connect_code,
    )


@bp.post("/doctor/profile/regenerate-code")
@role_required("doctor")
def regenerate_connect_code():
    doctor = doctor_profile_service.get_or_create_for_user(current_user())
    connect_code_service.regenerate(doctor["id"])
    flash("Yangi ulanish kodi yaratildi.")
    return redirect(url_for("doctor_profile_pages.profile_form"))


@bp.post("/doctor/profile/consultation-toggle")
@role_required("doctor")
def toggle_consultation_available():
    doctor = doctor_profile_service.get_or_create_for_user(current_user())
    doctor_repo.set_consultation_available(doctor["id"], not doctor["consultation_available"])
    return redirect(url_for("doctor_profile_pages.profile_form"))


@bp.post("/doctor/profile")
@role_required("doctor")
def profile_submit():
    doctor = doctor_profile_service.get_or_create_for_user(current_user())
    try:
        doctor_profile_service.complete_profile(
            doctor["id"], request.form, request.files.getlist("documents"))
    except AppError as exc:
        flash(exc.message)
        return redirect(url_for("doctor_profile_pages.profile_form"))

    flash("Profil saqlandi.")
    return redirect(url_for("auth_pages.app_home"))


@bp.get("/files/doctor-documents/<int:document_id>")
def doctor_document(document_id):
    """Any logged-in doctor viewing their own document, or an admin, may
    fetch it — nobody else. Never served straight out of static/."""
    user = current_user()
    if user is None:
        abort(401)

    document = doctor_document_repo.get(document_id)
    if document is None:
        abort(404)

    owner_doctor = doctor_repo.get(document["doctor_id"])
    is_owner = owner_doctor is not None and owner_doctor["user_id"] == user["id"]
    if not is_owner and not user["is_admin"]:
        raise Forbidden()

    return send_from_directory(
        Config.UPLOAD_DIR,
        document["file_path"],
        mimetype=document["content_type"],
        download_name=document["original_filename"],
    )
