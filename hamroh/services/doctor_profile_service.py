"""Doctor profile completion + admin verification (Module B).

`complete_profile` is the one gate: until it succeeds, `profile_completed`
stays 0 and `core.auth.doctor_profile_required` (used by every future
doctor-only route in modules C onward) keeps bouncing the doctor back here.
Verification is a separate, later step — a doctor can use the app with an
unverified profile, they just carry the badge and are invisible to
Module G's consultation matching.
"""

import os

from core import files
from core.errors import NotFound, ValidationError
from repos import doctor_document_repo, doctor_repo, specialty_repo

REQUIRED_DOC_MESSAGE = "Kamida bitta hujjat (diplom yoki litsenziya) yuklang."


def _as_dict(row):
    return {k: row[k] for k in row.keys()}


def get_or_create_for_user(user):
    doctor = doctor_repo.get_by_user(user["id"])
    if doctor is None:
        doctor_id = doctor_repo.create_for_user(user["id"])
        doctor = doctor_repo.get(doctor_id)
    return doctor


def get_detail(doctor_id):
    doctor = doctor_repo.get(doctor_id)
    if doctor is None:
        raise NotFound("Shifokor topilmadi.")
    return {
        "doctor": _as_dict(doctor),
        "specialties": [_as_dict(s) for s in specialty_repo.list_for_doctor(doctor_id)],
        "documents": [_as_dict(d) for d in doctor_document_repo.list_for_doctor(doctor_id)],
    }


def _clean_text(value):
    value = (value or "").strip()
    return value or None


def _parse_specialty_ids(raw_ids, valid_ids):
    try:
        ids = {int(i) for i in raw_ids}
    except (TypeError, ValueError):
        raise ValidationError("Mutaxassislik tanlovi noto'g'ri.")
    if not ids:
        raise ValidationError("Kamida bitta mutaxassislik tanlang.")
    if not ids.issubset(valid_ids):
        raise ValidationError("Mutaxassislik tanlovi noto'g'ri.")
    return ids


def _parse_experience_years(raw):
    try:
        years = int(raw)
    except (TypeError, ValueError):
        raise ValidationError("Tajriba yillari raqam bo'lishi kerak.")
    if years < 0 or years > 80:
        raise ValidationError("Tajriba yillari noto'g'ri.")
    return years


def complete_profile(doctor_id, form, uploaded_files):
    """`form` is a Werkzeug MultiDict, `uploaded_files` a list of FileStorage."""
    full_name = _clean_text(form.get("full_name"))
    birth_date = _clean_text(form.get("birth_date"))
    phone = _clean_text(form.get("phone"))
    workplace = _clean_text(form.get("workplace"))

    if not full_name:
        raise ValidationError("To'liq ism kiritilishi shart.")
    if not birth_date:
        raise ValidationError("Tug'ilgan sana kiritilishi shart.")
    if not phone:
        raise ValidationError("Telefon raqam kiritilishi shart.")

    valid_specialty_ids = {s["id"] for s in specialty_repo.list_all()}
    specialty_ids = _parse_specialty_ids(form.getlist("specialties"), valid_specialty_ids)
    experience_years = _parse_experience_years(form.get("experience_years"))

    for uploaded in uploaded_files:
        if uploaded is None or not uploaded.filename:
            continue
        relative_path, original_name, content_type = files.save_upload(
            uploaded, os.path.join("doctor_documents", str(doctor_id)))
        doctor_document_repo.create(
            doctor_id, relative_path, original_name, content_type)

    if not doctor_document_repo.list_for_doctor(doctor_id):
        raise ValidationError(REQUIRED_DOC_MESSAGE)

    doctor_repo.update_profile(
        doctor_id, full_name, birth_date, phone, experience_years, workplace)
    specialty_repo.set_for_doctor(doctor_id, specialty_ids)
    doctor_repo.mark_profile_completed(doctor_id)

    return get_detail(doctor_id)


def list_pending_for_admin():
    doctors = []
    for row in doctor_repo.list_pending_verification():
        doctors.append(get_detail(row["id"]))
    return doctors


def verify(doctor_id):
    doctor = doctor_repo.get(doctor_id)
    if doctor is None:
        raise NotFound("Shifokor topilmadi.")
    doctor_repo.mark_verified(doctor_id)
    return get_detail(doctor_id)
