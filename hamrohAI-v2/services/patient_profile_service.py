"""Patient self-signup profile (Module D).

No hard completion gate like Module B's doctors — the doc only asks that
the patient can fill in what a doctor would otherwise have entered for
them (name, phone; diagnosis/medications go through Module E's own
services), not that they're blocked from the rest of the app until they do.
"""

from core.errors import NotFound, ValidationError
from repos import doctor_repo, patient_repo


def _as_dict(row):
    return {k: row[k] for k in row.keys()}


def get_or_create_for_user(user):
    patient = patient_repo.get_by_user(user["id"])
    if patient is None:
        patient_id = patient_repo.create_for_user(user["id"], user["full_name"] or "")
        patient = patient_repo.get(patient_id)
    return patient


def get_detail(patient_id):
    patient = patient_repo.get(patient_id)
    if patient is None:
        raise NotFound("Bemor topilmadi.")
    doctor = doctor_repo.get(patient["doctor_id"]) if patient["doctor_id"] else None
    return {"patient": _as_dict(patient), "doctor": _as_dict(doctor) if doctor else None}


def update_profile(patient_id, full_name, phone):
    full_name = (full_name or "").strip()
    if not full_name:
        raise ValidationError("Ism kiritilishi shart.")
    patient_repo.update_profile(patient_id, full_name, (phone or "").strip() or None)
    return get_detail(patient_id)
