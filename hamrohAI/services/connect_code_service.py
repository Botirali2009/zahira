"""A doctor's reusable, expiring connect code (Module D).

Deliberately not shared with `invite_code_service.py` even though the
character-safety trick is identical — the two are conceptually different
(one-time & pre-linked vs. reusable & time-limited) and the doc explicitly
warns against conflating them. Redeeming this code only ever *links* an
already-existing patient to a doctor; it never creates or overwrites data,
unlike Module C's code.
"""

import secrets
from datetime import datetime, timedelta

from core.errors import AppError, ValidationError
from repos import doctor_repo, patient_repo

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
VALIDITY_DAYS = 90
MAX_GENERATION_ATTEMPTS = 10


def _generate_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def _as_dict(row):
    return {k: row[k] for k in row.keys()}


def _is_expired(doctor):
    if not doctor["connect_code_expires_at"]:
        return True
    return datetime.now() > datetime.fromisoformat(doctor["connect_code_expires_at"])


def get_or_create(doctor):
    """The code a doctor sees on their own profile page — generated once,
    reused until it expires or they explicitly regenerate it."""
    if doctor["connect_code"] and not _is_expired(doctor):
        return doctor["connect_code"], doctor["connect_code_expires_at"]
    return regenerate(doctor["id"])


def regenerate(doctor_id):
    expires_at = (datetime.now() + timedelta(days=VALIDITY_DAYS)).isoformat(timespec="seconds")
    for attempt in range(MAX_GENERATION_ATTEMPTS):
        code = _generate_code()
        try:
            doctor_repo.set_connect_code(doctor_id, code, expires_at)
            return code, expires_at
        except Exception:
            if attempt == MAX_GENERATION_ATTEMPTS - 1:
                raise AppError("Kod yaratib bo'lmadi. Qayta urinib ko'ring.",
                                code="code_generation_failed", status=500)
            continue


def link_patient(patient, raw_code):
    code = (raw_code or "").strip().upper().replace(" ", "").replace("-", "")
    if not code:
        raise ValidationError("Kod kiritilishi shart.")

    doctor = doctor_repo.get_by_connect_code(code)
    if doctor is None:
        raise AppError("Kod topilmadi. Qaytadan tekshirib kiriting.",
                        code="not_found", status=404)
    if _is_expired(doctor):
        raise AppError("Bu kodning muddati o'tgan. Shifokordan yangisini so'rang.",
                        code="code_expired", status=409)

    patient_repo.set_doctor_id(patient["id"], doctor["id"])
    return _as_dict(patient_repo.get(patient["id"]))


def unlink(patient):
    patient_repo.set_doctor_id(patient["id"], None)
    return _as_dict(patient_repo.get(patient["id"]))
