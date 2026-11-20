"""One-time doctor consultation requests (Module G).

`request()` freezes a snapshot of the patient's active diagnoses and active
medications into the consultation row at the moment it's asked — the doctor
who eventually answers sees exactly what was true then, not whatever the
patient's record has drifted to by the time someone accepts. Everything
after that is a state machine: open -> accepted (first doctor to try wins
the race, see `repos/consultation_repo.try_accept`) -> answered. There is
no persistent thread; a second question is a second, brand-new consultation.
"""

import json

from config import features
from core import events
from core.auth import Forbidden
from core.errors import AppError, FeatureDisabled, NotFound, ValidationError
from repos import consultation_repo, diagnosis_repo, medication_repo, specialty_repo

MAX_QUESTION_LENGTH = 2000


def _as_dict(row):
    return {k: row[k] for k in row.keys()}


def _build_snapshot(patient):
    diagnoses = [
        d["text"] for d in diagnosis_repo.list_for_patient(patient["id"])
        if d["status"] == "active"
    ]
    medications = [
        {"drug_name": m["drug_name"], "dose": m["dose"],
         "times": json.loads(m["times_json"] or "[]")}
        for m in medication_repo.list_for_patient(patient["id"], active_only=True)
    ]
    return {
        "full_name": patient["full_name"],
        "diagnosis_texts": diagnoses,
        "active_medications": medications,
    }


def request(patient, specialty_id, question_text):
    if not features.enabled("consultation"):
        raise FeatureDisabled("Konsultatsiya xizmati hozircha o'chirilgan.")

    question = (question_text or "").strip()
    if not question:
        raise ValidationError("Savol matni bo'sh bo'lmasligi kerak.")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValidationError("Savol juda uzun.")

    try:
        specialty_id = int(specialty_id)
    except (TypeError, ValueError):
        raise ValidationError("Mutaxassislik tanlanishi shart.")
    if not any(s["id"] == specialty_id for s in specialty_repo.list_all()):
        raise ValidationError("Mutaxassislik tanlanishi shart.")

    snapshot = _build_snapshot(patient)
    consultation_id = consultation_repo.create(
        patient["id"], specialty_id, question,
        json.dumps(snapshot, ensure_ascii=False, default=str),
    )

    events.emit(
        events.CONSULTATION_REQUESTED,
        consultation_id=consultation_id,
        specialty_id=specialty_id,
    )
    return _detail(consultation_id)


def _detail(consultation_id):
    row = consultation_repo.get(consultation_id)
    if row is None:
        raise NotFound("So'rov topilmadi.")
    item = _as_dict(row)
    try:
        item["snapshot"] = json.loads(item.pop("snapshot_json") or "{}")
    except (TypeError, ValueError):
        item["snapshot"] = {}
    return item


def list_for_patient(patient_id):
    return [_detail(r["id"]) for r in consultation_repo.list_for_patient(patient_id)]


def list_open_for_doctor(doctor):
    """Every currently-open request in a specialty this doctor serves —
    shown regardless of their own availability toggle, so turning it back
    on doesn't hide requests that arrived while they were off."""
    specialty_ids = {s["id"] for s in specialty_repo.list_for_doctor(doctor["id"])}
    items = []
    for specialty_id in specialty_ids:
        for row in consultation_repo.list_open_for_specialty(specialty_id):
            items.append(_detail(row["id"]))
    items.sort(key=lambda c: c["id"], reverse=True)
    return items


def list_accepted_for_doctor(doctor_id):
    return [_detail(r["id"]) for r in consultation_repo.list_accepted_for_doctor(doctor_id)]


def accept(doctor, consultation_id):
    consultation = consultation_repo.get(consultation_id)
    if consultation is None:
        raise NotFound("So'rov topilmadi.")
    if consultation["status"] != "open":
        raise AppError("Bu so'rov allaqachon qabul qilingan.",
                        code="already_accepted", status=409)

    doctor_specialty_ids = {s["id"] for s in specialty_repo.list_for_doctor(doctor["id"])}
    if not doctor["verified"] or not doctor["consultation_available"] \
            or consultation["specialty_id"] not in doctor_specialty_ids:
        raise Forbidden()

    won = consultation_repo.try_accept(consultation_id, doctor["id"])
    if not won:
        raise AppError("Bu so'rovni boshqa shifokor allaqachon qabul qildi.",
                        code="already_accepted", status=409)
    return _detail(consultation_id)


def answer(doctor, consultation_id, answer_text):
    consultation = consultation_repo.get(consultation_id)
    if consultation is None:
        raise NotFound("So'rov topilmadi.")
    if consultation["accepted_by_doctor_id"] != doctor["id"]:
        raise Forbidden()
    if consultation["status"] != "accepted":
        raise AppError("Bu so'rovga allaqachon javob berilgan.",
                        code="already_answered", status=409)

    text = (answer_text or "").strip()
    if not text:
        raise ValidationError("Javob matni bo'sh bo'lmasligi kerak.")

    consultation_repo.set_answer(consultation_id, text)
    events.emit(
        events.CONSULTATION_ANSWERED,
        consultation_id=consultation_id,
        patient_id=consultation["patient_id"],
    )
    return _detail(consultation_id)
