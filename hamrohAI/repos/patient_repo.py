"""SQL for the `patients` table."""

from core import db


def get(patient_id):
    return db.query_one("SELECT * FROM patients WHERE id = ?", (patient_id,))


def get_by_user(user_id):
    return db.query_one("SELECT * FROM patients WHERE user_id = ?", (user_id,))


def list_all():
    return db.query_all("SELECT * FROM patients ORDER BY id")


def list_by_doctor(doctor_id):
    """Patients of one doctor, with their last activity — dashboard list."""
    return db.query_all(
        """
        SELECT p.*,
               (SELECT MAX(created_at) FROM messages m
                 WHERE m.patient_id = p.id)            AS last_message_at,
               (SELECT COUNT(*) FROM alerts a
                 WHERE a.patient_id = p.id
                   AND a.status = 'new')               AS open_alerts
          FROM patients p
         WHERE p.doctor_id = ?
         ORDER BY p.id
        """,
        (doctor_id,),
    )


def create(full_name, persona_key, doctor_id, diagnosis=None,
           discharge_date=None, phone_sim=None, meta_json="{}"):
    return db.execute(
        """
        INSERT INTO patients (full_name, persona_key, diagnosis, discharge_date,
                              phone_sim, doctor_id, meta_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (full_name, persona_key, diagnosis, discharge_date, phone_sim,
         doctor_id, meta_json),
    )


def set_current_day(patient_id, day_number):
    db.execute(
        "UPDATE patients SET current_day = ? WHERE id = ?",
        (day_number, patient_id),
    )


def set_risk_level(patient_id, risk_level):
    db.execute(
        "UPDATE patients SET risk_level = ? WHERE id = ?",
        (risk_level, patient_id),
    )


def set_meta_json(patient_id, meta_json):
    db.execute(
        "UPDATE patients SET meta_json = ? WHERE id = ?",
        (meta_json, patient_id),
    )


def set_user_id(patient_id, user_id):
    db.execute(
        "UPDATE patients SET user_id = ? WHERE id = ?",
        (user_id, patient_id),
    )


def set_doctor_id(patient_id, doctor_id):
    db.execute(
        "UPDATE patients SET doctor_id = ? WHERE id = ?",
        (doctor_id, patient_id),
    )


def create_for_user(user_id, full_name):
    """Bare self-signup patient row (Module D) — no doctor yet, filled in
    the rest of the way by the patient themself via /patient/profile."""
    return db.execute(
        "INSERT INTO patients (full_name, persona_key, user_id) VALUES (?, 'general', ?)",
        (full_name, user_id),
    )


def update_profile(patient_id, full_name, phone_sim):
    db.execute(
        "UPDATE patients SET full_name = ?, phone_sim = ? WHERE id = ?",
        (full_name, phone_sim, patient_id),
    )
