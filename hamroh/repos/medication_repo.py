"""SQL for the `medication_schedules` table."""

from core import db


def get(schedule_id):
    return db.query_one("SELECT * FROM medication_schedules WHERE id = ?", (schedule_id,))


def create(patient_id, drug_name, dose, times_json, start_date, end_date,
           created_by, created_by_user_id):
    return db.execute(
        """
        INSERT INTO medication_schedules
            (patient_id, drug_name, dose, times_json, start_date, end_date,
             created_by, created_by_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (patient_id, drug_name, dose, times_json, start_date, end_date,
         created_by, created_by_user_id),
    )


def list_for_patient(patient_id, active_only=False):
    if active_only:
        return db.query_all(
            """
            SELECT * FROM medication_schedules
             WHERE patient_id = ? AND active = 1
             ORDER BY id DESC
            """,
            (patient_id,),
        )
    return db.query_all(
        "SELECT * FROM medication_schedules WHERE patient_id = ? ORDER BY id DESC",
        (patient_id,),
    )


def update(schedule_id, drug_name, dose, times_json, start_date, end_date):
    db.execute(
        """
        UPDATE medication_schedules
           SET drug_name = ?, dose = ?, times_json = ?, start_date = ?,
               end_date = ?, updated_at = datetime('now')
         WHERE id = ?
        """,
        (drug_name, dose, times_json, start_date, end_date, schedule_id),
    )


def set_active(schedule_id, active):
    db.execute(
        "UPDATE medication_schedules SET active = ?, updated_at = datetime('now') WHERE id = ?",
        (1 if active else 0, schedule_id),
    )


def list_active():
    """Every currently-active schedule — what the reminder scheduler scans
    each tick."""
    return db.query_all("SELECT * FROM medication_schedules WHERE active = 1")
