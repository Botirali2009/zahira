"""SQL for the `diagnosis_files` table."""

from core import db


def get(file_id):
    return db.query_one("SELECT * FROM diagnosis_files WHERE id = ?", (file_id,))


def create(diagnosis_id, file_path, original_filename, content_type):
    return db.execute(
        """
        INSERT INTO diagnosis_files (diagnosis_id, file_path, original_filename, content_type)
        VALUES (?, ?, ?, ?)
        """,
        (diagnosis_id, file_path, original_filename, content_type),
    )


def list_for_diagnosis(diagnosis_id):
    return db.query_all(
        "SELECT * FROM diagnosis_files WHERE diagnosis_id = ? ORDER BY id",
        (diagnosis_id,),
    )


def mark_analyzed(file_id):
    """Unused until an AI file-analyzer extension point exists — kept ready
    so that addition never needs a schema change."""
    db.execute("UPDATE diagnosis_files SET analyzed = 1 WHERE id = ?", (file_id,))
