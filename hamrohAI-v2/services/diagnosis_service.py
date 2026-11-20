"""Diagnosis + attached files — written by either side, read by both.

Access control (who may touch a given patient's records at all) is checked
by the route via `core.auth.require_patient_access` before any of this runs;
this module only enforces the shape of the data, never who's asking.
"""

import os

from core import files
from core.errors import NotFound, ValidationError
from repos import diagnosis_file_repo, diagnosis_repo

VALID_STATUSES = ("active", "closed")


def _as_dict(row):
    return {k: row[k] for k in row.keys()}


def _detail(diagnosis_id):
    diagnosis = diagnosis_repo.get(diagnosis_id)
    return {
        "diagnosis": _as_dict(diagnosis),
        "files": [_as_dict(f) for f in diagnosis_file_repo.list_for_diagnosis(diagnosis_id)],
    }


def add(patient_id, actor_role, actor_user_id, text, uploaded_files=None):
    text = (text or "").strip()
    if not text:
        raise ValidationError("Tashxis matni bo'sh bo'lmasligi kerak.")

    diagnosis_id = diagnosis_repo.create(patient_id, text, actor_role, actor_user_id)

    for uploaded in uploaded_files or []:
        if uploaded is None or not uploaded.filename:
            continue
        relative_path, original_name, content_type = files.save_upload(
            uploaded, os.path.join("diagnosis_files", str(patient_id)))
        diagnosis_file_repo.create(diagnosis_id, relative_path, original_name, content_type)

    return _detail(diagnosis_id)


def list_for_patient(patient_id):
    return [_detail(row["id"]) for row in diagnosis_repo.list_for_patient(patient_id)]


def _get_or_404(diagnosis_id):
    diagnosis = diagnosis_repo.get(diagnosis_id)
    if diagnosis is None:
        raise NotFound("Tashxis topilmadi.")
    return diagnosis


def update_text(diagnosis_id, text):
    _get_or_404(diagnosis_id)
    text = (text or "").strip()
    if not text:
        raise ValidationError("Tashxis matni bo'sh bo'lmasligi kerak.")
    diagnosis_repo.update_text(diagnosis_id, text)
    return _detail(diagnosis_id)


def set_status(diagnosis_id, status):
    _get_or_404(diagnosis_id)
    if status not in VALID_STATUSES:
        raise ValidationError("Tashxis holati noto'g'ri.")
    diagnosis_repo.set_status(diagnosis_id, status)
    return _detail(diagnosis_id)
