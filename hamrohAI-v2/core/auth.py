"""Session helpers and route guards (Module A).

Flask's signed-cookie session (backed by `SECRET_KEY`) is the whole session
store — no server-side session table needed at this scale. `current_user()`
is the single place that reads the session and loads the row; every
ownership/role check in later modules (B-G) builds on top of it, so a
"shifokor faqat o'z bemorini ko'rsin" check is always `current_user()` plus
one join, never a second source of truth.
"""

from functools import wraps

from flask import redirect, request, session, url_for

from core.errors import AppError
from repos import doctor_repo, user_repo

SESSION_KEY = "user_id"


class Unauthorized(AppError):
    code = "unauthorized"
    status = 401
    message = "Tizimga kirish kerak."


class Forbidden(AppError):
    code = "forbidden"
    status = 403
    message = "Bu amal uchun ruxsat yo'q."


class ProfileIncomplete(AppError):
    code = "profile_incomplete"
    status = 403
    message = "Avval profilni to'ldiring."


def login_user(user_id):
    session[SESSION_KEY] = user_id


def logout_user():
    session.pop(SESSION_KEY, None)


def current_user():
    user_id = session.get(SESSION_KEY)
    if user_id is None:
        return None
    return user_repo.get(user_id)


def _is_api_request():
    return (request.path or "").startswith("/api/")


def login_required(fn):
    """Page routes redirect to /auth/login; /api/* routes get the envelope."""

    @wraps(fn)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            if _is_api_request():
                raise Unauthorized()
            return redirect(url_for("auth_pages.login"))
        return fn(*args, **kwargs)

    return wrapped


def role_required(role):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user()["role"] != role:
                raise Forbidden()
            return fn(*args, **kwargs)

        return wrapped

    return decorator


def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user()["is_admin"]:
            raise Forbidden()
        return fn(*args, **kwargs)

    return wrapped


def can_access_patient(user, patient):
    """The Module A rule made concrete: a patient sees only themselves, a
    doctor only their own linked patients. Checked here, at the one place
    every route (Module E onward) that touches a specific patient's medical
    data calls into — never left to the UI to hide."""
    if user["role"] == "patient":
        return patient["user_id"] == user["id"]
    if user["role"] == "doctor":
        doctor = doctor_repo.get_by_user(user["id"])
        return doctor is not None and patient["doctor_id"] == doctor["id"]
    return False


def require_patient_access(patient):
    user = current_user()
    if user is None:
        raise Unauthorized()
    if not can_access_patient(user, patient):
        raise Forbidden()
    return user


def doctor_profile_required(fn):
    """role == doctor AND their profile is complete — the gate every
    doctor-only route from Module C onward sits behind (Module B's own
    completion criterion: can't reach the rest of the system otherwise)."""

    @wraps(fn)
    @role_required("doctor")
    def wrapped(*args, **kwargs):
        doctor = doctor_repo.get_by_user(current_user()["id"])
        if doctor is None or not doctor["profile_completed"]:
            if _is_api_request():
                raise ProfileIncomplete()
            return redirect(url_for("doctor_profile_pages.profile_form"))
        return fn(*args, **kwargs)

    return wrapped
