"""SQL for the `consultations` table."""

from core import db


def get(consultation_id):
    return db.query_one("SELECT * FROM consultations WHERE id = ?", (consultation_id,))


def create(patient_id, specialty_id, question, snapshot_json):
    return db.execute(
        """
        INSERT INTO consultations (patient_id, specialty_id, question, snapshot_json)
        VALUES (?, ?, ?, ?)
        """,
        (patient_id, specialty_id, question, snapshot_json),
    )


def list_open_for_specialty(specialty_id):
    return db.query_all(
        """
        SELECT * FROM consultations
         WHERE specialty_id = ? AND status = 'open'
         ORDER BY id
        """,
        (specialty_id,),
    )


def try_accept(consultation_id, doctor_id):
    """Atomic 'first to accept wins': the WHERE clause only matches a row
    still `open`, so a losing concurrent accept touches zero rows."""
    rowcount = db.execute_rowcount(
        """
        UPDATE consultations
           SET status = 'accepted', accepted_by_doctor_id = ?, accepted_at = datetime('now')
         WHERE id = ? AND status = 'open'
        """,
        (doctor_id, consultation_id),
    )
    return rowcount > 0


def set_answer(consultation_id, answer_text):
    db.execute(
        """
        UPDATE consultations
           SET status = 'answered', answer_text = ?, answered_at = datetime('now')
         WHERE id = ?
        """,
        (answer_text, consultation_id),
    )


def list_for_patient(patient_id):
    return db.query_all(
        "SELECT * FROM consultations WHERE patient_id = ? ORDER BY id DESC",
        (patient_id,),
    )


def list_accepted_for_doctor(doctor_id):
    return db.query_all(
        """
        SELECT * FROM consultations
         WHERE accepted_by_doctor_id = ?
         ORDER BY id DESC
        """,
        (doctor_id,),
    )
