"""Shared medication + diagnosis view (Module E's UI, hung off the entry
points Modules C/D create). One page, two authors — a doctor viewing their
linked patient and the patient themself land on the exact same page and
call the exact same `/api/v1/care/...` endpoints from Module E.

Adding a diagnosis needs a file upload, so that one action is a plain HTML
form posting here (page route -> service -> redirect) rather than a fetch
call — the JSON API stays a pure JSON API, never redirecting."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from core.auth import current_user, login_required, require_patient_access
from core.errors import AppError, NotFound
from repos import patient_repo
from services import diagnosis_service

bp = Blueprint("care_pages", __name__, url_prefix="/care")


def _get_patient(pid):
    patient = patient_repo.get(pid)
    if patient is None:
        raise NotFound("Bemor topilmadi.")
    return patient


@bp.get("/patients/<int:pid>")
@login_required
def patient_care(pid):
    patient = _get_patient(pid)
    require_patient_access(patient)
    return render_template(
        "patient_care.html", patient=patient, viewer_role=current_user()["role"])


@bp.post("/patients/<int:pid>/diagnoses")
@login_required
def add_diagnosis(pid):
    patient = _get_patient(pid)
    user = require_patient_access(patient)
    try:
        diagnosis_service.add(
            pid, user["role"], user["id"],
            request.form.get("text"), request.files.getlist("files"))
    except AppError as exc:
        flash(exc.message)
    return redirect(url_for("care_pages.patient_care", pid=pid))
