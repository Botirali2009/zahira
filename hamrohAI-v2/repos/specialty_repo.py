"""SQL for `specialties` and the `doctor_specialties` join table."""

from core import db


def list_all():
    return db.query_all("SELECT * FROM specialties ORDER BY label")


def list_for_doctor(doctor_id):
    return db.query_all(
        """
        SELECT s.* FROM specialties s
          JOIN doctor_specialties ds ON ds.specialty_id = s.id
         WHERE ds.doctor_id = ?
         ORDER BY s.label
        """,
        (doctor_id,),
    )


def set_for_doctor(doctor_id, specialty_ids):
    """Replace a doctor's specialty set."""
    db.execute("DELETE FROM doctor_specialties WHERE doctor_id = ?", (doctor_id,))
    if specialty_ids:
        db.execute_many(
            "INSERT INTO doctor_specialties (doctor_id, specialty_id) VALUES (?, ?)",
            [(doctor_id, sid) for sid in specialty_ids],
        )
