"""Doctor's own patient list + adding a new patient with an invite code."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from core.auth import current_user, doctor_profile_required
from core.errors import AppError
from repos import doctor_repo, patient_repo
from services import invite_code_service

bp = Blueprint("doctor_patients_pages", __name__, url_prefix="/doctor/patients")


def _current_doctor():
    return doctor_repo.get_by_user(current_user()["id"])


@bp.get("")
@doctor_profile_required
def list_patients():
    doctor = _current_doctor()
    return render_template(
        "doctor_patients.html",
        patients=patient_repo.list_by_doctor(doctor["id"]),
        codes=invite_code_service.list_for_doctor(doctor["id"]),
    )


@bp.get("/add")
@doctor_profile_required
def add_form():
    return render_template("doctor_patient_add.html")


@bp.post("/add")
@doctor_profile_required
def add_submit():
    doctor = _current_doctor()
    try:
        result = invite_code_service.create_for_new_patient(
            doctor,
            request.form.get("full_name"),
            request.form.get("phone"),
            request.form.get("diagnosis"),
            request.files.getlist("files"),
        )
    except AppError as exc:
        flash(exc.message)
        return redirect(url_for("doctor_patients_pages.add_form"))

    return render_template(
        "doctor_patient_added.html", patient=result["patient"], code=result["code"])
