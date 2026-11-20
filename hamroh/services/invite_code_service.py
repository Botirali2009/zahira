"""Doctor-issued one-time invite codes (Module C).

`create_for_new_patient` does three things in one call: creates the patient
row (pre-linked to the issuing doctor, no user yet), attaches whatever the
doctor already knows (diagnosis text + files) through Module E's own
`diagnosis_service` — nothing here re-implements file handling — and mints
the code. `redeem` is the mirror image: a brand-new user hands back the
code and inherits that same patient row, verbatim, without retyping any of
it.
"""

import secrets

from core.errors import AppError, NotFound, ValidationError
from repos import invite_code_repo, patient_repo
from services import auth_service, diagnosis_service

# 0/O and 1/I (and L, which looks like 1 in some fonts) dropped so a code
# read aloud over the phone can't be misheard into the wrong character.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 7
MAX_GENERATION_ATTEMPTS = 10

DEFAULT_PERSONA_KEY = "general"  # no scripted check-in plan; see PLAN.md 12.4


def _generate_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def _as_dict(row):
    return {k: row[k] for k in row.keys()}


def create_for_new_patient(doctor, full_name, phone, diagnosis_text, uploaded_files=None):
    full_name = (full_name or "").strip()
    if not full_name:
        raise ValidationError("Bemor ismi kiritilishi shart.")
    phone = (phone or "").strip() or None
    diagnosis_text = (diagnosis_text or "").strip() or None

    patient_id = patient_repo.create(
        full_name, DEFAULT_PERSONA_KEY, doctor["id"],
        diagnosis=diagnosis_text, phone_sim=phone,
    )

    if diagnosis_text:
        diagnosis_service.add(
            patient_id, "doctor", doctor["user_id"], diagnosis_text, uploaded_files)

    for attempt in range(MAX_GENERATION_ATTEMPTS):
        code = _generate_code()
        try:
            invite_code_repo.create(code, patient_id, doctor["id"])
            break
        except Exception:
            if attempt == MAX_GENERATION_ATTEMPTS - 1:
                raise AppError("Kod yaratib bo'lmadi. Qayta urinib ko'ring.",
                                code="code_generation_failed", status=500)
            continue

    return {"patient": _as_dict(patient_repo.get(patient_id)), "code": code}


def list_for_doctor(doctor_id):
    return [_as_dict(r) for r in invite_code_repo.list_for_doctor(doctor_id)]


def redeem(user, raw_code):
    if user["role"] is not None:
        raise AppError("Sizda allaqachon profil mavjud.", code="already_has_profile", status=409)

    code = (raw_code or "").strip().upper().replace(" ", "").replace("-", "")
    if not code:
        raise ValidationError("Kod kiritilishi shart.")

    invite = invite_code_repo.find_by_code(code)
    if invite is None:
        raise NotFound("Kod topilmadi. Qaytadan tekshirib kiriting.")
    if invite["used"]:
        raise AppError("Bu kod allaqachon ishlatilgan.", code="code_already_used", status=409)

    patient_repo.set_user_id(invite["patient_id"], user["id"])
    invite_code_repo.mark_used(invite["id"], user["id"])
    auth_service.set_role(user["id"], "patient")

    return _as_dict(patient_repo.get(invite["patient_id"]))
