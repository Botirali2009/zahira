"""Diagnosis endpoints. HTTP only. Both doctor and patient may write here —
`core.auth.require_patient_access` is the only gate."""

from flask import Blueprint, request

from core.auth import login_required, require_patient_access
from core.errors import NotFound
from core.responses import ok
from repos import patient_repo
from services import diagnosis_service

bp = Blueprint("diagnosis_api", __name__)


def _get_patient(pid):
    patient = patient_repo.get(pid)
    if patient is None:
        raise NotFound("Bemor topilmadi.")
    return patient


@bp.get("/<int:pid>/diagnoses")
@login_required
def list_diagnoses(pid):
    patient = _get_patient(pid)
    require_patient_access(patient)
    return ok({"diagnoses": diagnosis_service.list_for_patient(pid)})


@bp.post("/<int:pid>/diagnoses")
@login_required
def add_diagnosis(pid):
    patient = _get_patient(pid)
    user = require_patient_access(patient)
    text = request.form.get("text")
    uploaded = request.files.getlist("files")
    diagnosis = diagnosis_service.add(pid, user["role"], user["id"], text, uploaded)
    return ok({"diagnosis": diagnosis})


@bp.post("/<int:pid>/diagnoses/<int:did>")
@login_required
def update_diagnosis(pid, did):
    patient = _get_patient(pid)
    require_patient_access(patient)
    payload = request.get_json(silent=True) or {}
    diagnosis = diagnosis_service.update_text(did, payload.get("text"))
    return ok({"diagnosis": diagnosis})


@bp.post("/<int:pid>/diagnoses/<int:did>/status")
@login_required
def set_diagnosis_status(pid, did):
    patient = _get_patient(pid)
    require_patient_access(patient)
    payload = request.get_json(silent=True) or {}
    diagnosis = diagnosis_service.set_status(did, payload.get("status"))
    return ok({"diagnosis": diagnosis})
