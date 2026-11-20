"""SQL for the `invite_codes` table."""

from core import db


def create(code, patient_id, doctor_id):
    return db.execute(
        "INSERT INTO invite_codes (code, patient_id, doctor_id) VALUES (?, ?, ?)",
        (code, patient_id, doctor_id),
    )


def find_by_code(code):
    return db.query_one("SELECT * FROM invite_codes WHERE code = ?", (code,))


def mark_used(code_id, user_id):
    db.execute(
        """
        UPDATE invite_codes
           SET used = 1, used_by_user_id = ?, used_at = datetime('now')
         WHERE id = ?
        """,
        (user_id, code_id),
    )


def list_for_doctor(doctor_id):
    return db.query_all(
        """
        SELECT ic.*, p.full_name AS patient_name
          FROM invite_codes ic
          JOIN patients p ON p.id = ic.patient_id
         WHERE ic.doctor_id = ?
         ORDER BY ic.id DESC
        """,
        (doctor_id,),
    )
