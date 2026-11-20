"""Risk-score trend — the auth-gated counterpart of the existing
unauthenticated doctor-side `/api/v1/patients/<pid>/trend` (Module F: the
patient couldn't see this before, only the doctor could)."""

from flask import Blueprint

from core.auth import login_required, require_patient_access
from core.errors import NotFound
from core.responses import ok
from repos import patient_repo
from services import doctor_service

bp = Blueprint("trend_api", __name__)


@bp.get("/<int:pid>/trend")
@login_required
def trend(pid):
    patient = patient_repo.get(pid)
    if patient is None:
        raise NotFound("Bemor topilmadi.")
    require_patient_access(patient)
    return ok(doctor_service.get_trend(pid))
