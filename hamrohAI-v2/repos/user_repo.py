"""SQL for the `users` table."""

from core import db


def get(user_id):
    return db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))


def create(role=None, full_name=None, phone=None, email=None):
    return db.execute(
        "INSERT INTO users (role, full_name, phone, email) VALUES (?, ?, ?, ?)",
        (role, full_name, phone, email),
    )


def set_role(user_id, role):
    db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))


def set_admin(user_id, is_admin):
    db.execute("UPDATE users SET is_admin = ? WHERE id = ?", (1 if is_admin else 0, user_id))


def update_profile(user_id, full_name=None, phone=None, email=None):
    db.execute(
        """
        UPDATE users
           SET full_name = COALESCE(?, full_name),
               phone     = COALESCE(?, phone),
               email     = COALESCE(?, email)
         WHERE id = ?
        """,
        (full_name, phone, email, user_id),
    )
