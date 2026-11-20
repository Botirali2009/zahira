"""Medication schedule endpoints. HTTP only. Both doctor and patient may
write here — `core.auth.require_patient_access` is the only gate."""

from flask import Blueprint, request

from core.auth import login_required, require_patient_access
from core.errors import NotFound
from core.responses import ok
from repos import patient_repo
from services import medication_service

bp = Blueprint("medication_api", __name__)


def _get_patient(pid):
    patient = patient_repo.get(pid)
    if patient is None:
        raise NotFound("Bemor topilmadi.")
    return patient


@bp.get("/<int:pid>/medications")
@login_required
def list_medications(pid):
    patient = _get_patient(pid)
    require_patient_access(patient)
    active_only = request.args.get("active_only") == "1"
    return ok({"medications": medication_service.list_for_patient(pid, active_only=active_only)})


@bp.post("/<int:pid>/medications")
@login_required
def add_medication(pid):
    patient = _get_patient(pid)
    user = require_patient_access(patient)
    payload = request.get_json(silent=True) or {}
    medication = medication_service.add(
        pid, user["role"], user["id"],
        payload.get("drug_name"), payload.get("dose"),
        payload.get("times") or [], payload.get("start_date"), payload.get("end_date"),
    )
    return ok({"medication": medication})


@bp.post("/<int:pid>/medications/<int:mid>")
@login_required
def update_medication(pid, mid):
    patient = _get_patient(pid)
    require_patient_access(patient)
    payload = request.get_json(silent=True) or {}
    medication = medication_service.update(
        mid, payload.get("drug_name"), payload.get("dose"),
        payload.get("times") or [], payload.get("start_date"), payload.get("end_date"),
    )
    return ok({"medication": medication})


@bp.post("/<int:pid>/medications/<int:mid>/stop")
@login_required
def stop_medication(pid, mid):
    patient = _get_patient(pid)
    require_patient_access(patient)
    return ok({"medication": medication_service.stop(mid)})


@bp.post("/<int:pid>/medications/<int:mid>/resume")
@login_required
def resume_medication(pid, mid):
    patient = _get_patient(pid)
    require_patient_access(patient)
    return ok({"medication": medication_service.resume(mid)})
