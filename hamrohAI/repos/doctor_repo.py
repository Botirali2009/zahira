"""SQL for the `doctors` table."""

from core import db


def get(doctor_id):
    return db.query_one("SELECT * FROM doctors WHERE id = ?", (doctor_id,))


def get_by_user(user_id):
    return db.query_one("SELECT * FROM doctors WHERE user_id = ?", (user_id,))


def list_all():
    return db.query_all("SELECT * FROM doctors ORDER BY id")


def list_pending_verification():
    return db.query_all(
        """
        SELECT * FROM doctors
         WHERE profile_completed = 1 AND verified = 0
         ORDER BY id
        """
    )


def create(full_name, clinic_name, phone_sim=None):
    return db.execute(
        "INSERT INTO doctors (full_name, clinic_name, phone_sim) VALUES (?, ?, ?)",
        (full_name, clinic_name, phone_sim),
    )


def create_for_user(user_id):
    """Bare row created the moment someone picks the doctor role — everything
    else is filled in by the profile-completion form."""
    return db.execute(
        "INSERT INTO doctors (full_name, clinic_name, user_id) VALUES ('', '', ?)",
        (user_id,),
    )


def update_profile(doctor_id, full_name, birth_date, phone_sim, experience_years,
                    workplace):
    db.execute(
        """
        UPDATE doctors
           SET full_name = ?, birth_date = ?, phone_sim = ?,
               experience_years = ?, workplace = ?
         WHERE id = ?
        """,
        (full_name, birth_date, phone_sim, experience_years, workplace, doctor_id),
    )


def mark_profile_completed(doctor_id):
    db.execute("UPDATE doctors SET profile_completed = 1 WHERE id = ?", (doctor_id,))


def mark_verified(doctor_id):
    db.execute("UPDATE doctors SET verified = 1 WHERE id = ?", (doctor_id,))


def get_by_connect_code(code):
    return db.query_one("SELECT * FROM doctors WHERE connect_code = ?", (code,))


def set_connect_code(doctor_id, code, expires_at):
    db.execute(
        "UPDATE doctors SET connect_code = ?, connect_code_expires_at = ? WHERE id = ?",
        (code, expires_at, doctor_id),
    )


def set_consultation_available(doctor_id, available):
    db.execute(
        "UPDATE doctors SET consultation_available = ? WHERE id = ?",
        (1 if available else 0, doctor_id),
    )


def list_available_for_specialty(specialty_id):
    """Verified doctors, registered under this specialty (Module B), who
    currently want consultation requests — the Module G matching rule."""
    return db.query_all(
        """
        SELECT d.* FROM doctors d
          JOIN doctor_specialties ds ON ds.doctor_id = d.id
         WHERE ds.specialty_id = ?
           AND d.verified = 1
           AND d.consultation_available = 1
        """,
        (specialty_id,),
    )
