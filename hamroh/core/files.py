"""Validated upload storage.

Doesn't know what a "doctor document" or "diagnosis file" is — just: given a
werkzeug `FileStorage` and a subdirectory, validate extension/size, write it
under `Config.UPLOAD_DIR` with a collision-proof name, and hand back the
relative path callers store in their own table. Files never live under
`static/` — nothing here is reachable without going through a route that
checks ownership first (see routes/doctor_profile_pages.py).
"""

import os
import uuid

from werkzeug.utils import secure_filename

from config import Config
from core.errors import ValidationError

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def save_upload(file_storage, subdir):
    """Returns (relative_path, original_filename, content_type)."""
    if file_storage is None or not file_storage.filename:
        raise ValidationError("Fayl tanlanmagan.")

    original = secure_filename(file_storage.filename)
    ext = os.path.splitext(original)[1].lower()
    if ext not in CONTENT_TYPES:
        raise ValidationError("Faqat PDF, JPG yoki PNG fayllar qabul qilinadi.")

    dest_dir = os.path.join(Config.UPLOAD_DIR, subdir)
    os.makedirs(dest_dir, exist_ok=True)
    stored_name = uuid.uuid4().hex + ext
    file_storage.save(os.path.join(dest_dir, stored_name))

    return os.path.join(subdir, stored_name), original, CONTENT_TYPES[ext]


def absolute_path(relative_path):
    return os.path.join(Config.UPLOAD_DIR, relative_path)
