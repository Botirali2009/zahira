"""Protected diagnosis-file downloads. Not under /api/v1/care — it needs a
path shape (`/files/...`) with no patient id in it, since the file id alone
identifies the diagnosis, and therefore the patient, to check access against.
"""

from flask import Blueprint, abort, send_from_directory

from config import Config
from core.auth import Forbidden, can_access_patient, current_user
from repos import diagnosis_file_repo, diagnosis_repo, patient_repo

bp = Blueprint("diagnosis_files", __name__)


@bp.get("/files/diagnosis-files/<int:file_id>")
def diagnosis_file(file_id):
    user = current_user()
    if user is None:
        abort(401)

    document = diagnosis_file_repo.get(file_id)
    if document is None:
        abort(404)

    diagnosis = diagnosis_repo.get(document["diagnosis_id"])
    patient = patient_repo.get(diagnosis["patient_id"]) if diagnosis else None
    if patient is None or not can_access_patient(user, patient):
        raise Forbidden()

    return send_from_directory(
        Config.UPLOAD_DIR,
        document["file_path"],
        mimetype=document["content_type"],
        download_name=document["original_filename"],
    )
