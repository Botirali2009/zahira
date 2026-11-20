"""SQL for the `diagnoses` table."""

from core import db


def get(diagnosis_id):
    return db.query_one("SELECT * FROM diagnoses WHERE id = ?", (diagnosis_id,))


def create(patient_id, text, created_by, created_by_user_id):
    return db.execute(
        """
        INSERT INTO diagnoses (patient_id, text, created_by, created_by_user_id)
        VALUES (?, ?, ?, ?)
        """,
        (patient_id, text, created_by, created_by_user_id),
    )


def list_for_patient(patient_id):
    return db.query_all(
        "SELECT * FROM diagnoses WHERE patient_id = ? ORDER BY id DESC",
        (patient_id,),
    )


def update_text(diagnosis_id, text):
    db.execute(
        "UPDATE diagnoses SET text = ?, updated_at = datetime('now') WHERE id = ?",
        (text, diagnosis_id),
    )


def set_status(diagnosis_id, status):
    db.execute(
        "UPDATE diagnoses SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, diagnosis_id),
    )
