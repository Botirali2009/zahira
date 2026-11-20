"""SQL for the `doctor_documents` table."""

from core import db


def get(document_id):
    return db.query_one("SELECT * FROM doctor_documents WHERE id = ?", (document_id,))


def create(doctor_id, file_path, original_filename, content_type, doc_type="diploma"):
    return db.execute(
        """
        INSERT INTO doctor_documents
            (doctor_id, doc_type, file_path, original_filename, content_type)
        VALUES (?, ?, ?, ?, ?)
        """,
        (doctor_id, doc_type, file_path, original_filename, content_type),
    )


def list_for_doctor(doctor_id):
    return db.query_all(
        "SELECT * FROM doctor_documents WHERE doctor_id = ? ORDER BY id",
        (doctor_id,),
    )
