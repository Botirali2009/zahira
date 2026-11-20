"""One-time doctor consultation requests — patient and doctor sides."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from core.auth import current_user, doctor_profile_required, role_required
from core.errors import AppError
from repos import doctor_repo, specialty_repo
from services import consultation_service, patient_profile_service

bp = Blueprint("consultation_pages", __name__)


@bp.get("/patient/consultations")
@role_required("patient")
def patient_list():
    patient = patient_profile_service.get_or_create_for_user(current_user())
    return render_template(
        "patient_consultations.html",
        consultations=consultation_service.list_for_patient(patient["id"]),
        all_specialties=specialty_repo.list_all(),
    )


@bp.post("/patient/consultations")
@role_required("patient")
def patient_request():
    patient = patient_profile_service.get_or_create_for_user(current_user())
    try:
        consultation_service.request(
            patient, request.form.get("specialty_id"), request.form.get("question"))
    except AppError as exc:
        flash(exc.message)
    else:
        flash("So'rovingiz yuborildi. Shifokor javob berganda xabar olasiz.")
    return redirect(url_for("consultation_pages.patient_list"))


def _current_doctor():
    return doctor_repo.get_by_user(current_user()["id"])


@bp.get("/doctor/consultations")
@doctor_profile_required
def doctor_list():
    doctor = _current_doctor()
    return render_template(
        "doctor_consultations.html",
        doctor=doctor,
        open_consultations=consultation_service.list_open_for_doctor(doctor),
        my_consultations=consultation_service.list_accepted_for_doctor(doctor["id"]),
    )


@bp.post("/doctor/consultations/<int:consultation_id>/accept")
@doctor_profile_required
def doctor_accept(consultation_id):
    doctor = _current_doctor()
    try:
        consultation_service.accept(doctor, consultation_id)
    except AppError as exc:
        flash(exc.message)
    return redirect(url_for("consultation_pages.doctor_list"))


@bp.post("/doctor/consultations/<int:consultation_id>/answer")
@doctor_profile_required
def doctor_answer(consultation_id):
    doctor = _current_doctor()
    try:
        consultation_service.answer(doctor, consultation_id, request.form.get("answer"))
    except AppError as exc:
        flash(exc.message)
    else:
        flash("Javobingiz yuborildi.")
    return redirect(url_for("consultation_pages.doctor_list"))
