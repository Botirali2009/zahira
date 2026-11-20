"""Module D — patient self-signup + linking to a doctor via connect code."""

import io
import urllib.parse
from datetime import datetime, timedelta

import pytest

from config import Config
from tests.test_smoke import app, client  # noqa: F401  (fixture reuse)


@pytest.fixture(autouse=True)
def _isolate_uploads(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "UPLOAD_DIR", str(tmp_path))


def _login_google(client, monkeypatch, sub, email, name):
    from identity_providers import google

    monkeypatch.setattr(Config, "GOOGLE_CLIENT_ID", "test-id")
    monkeypatch.setattr(Config, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(Config, "GOOGLE_REDIRECT_URI", "http://localhost/auth/google/callback")

    class FakeTokenResponse:
        def json(self):
            return {"access_token": "tok"}

    class FakeProfileResponse:
        def json(self):
            return {"sub": sub, "name": name, "email": email}

    monkeypatch.setattr(google.requests, "post", lambda *a, **k: FakeTokenResponse())
    monkeypatch.setattr(google.requests, "get", lambda *a, **k: FakeProfileResponse())

    start = client.get("/auth/google/start")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(start.headers["Location"]).query)["state"][0]
    client.get("/auth/google/callback?state=%s&code=whatever" % state)


def _login_completed_doctor(client, monkeypatch, sub="google-doc-1", email="doc@example.com",
                             name="Dr. Aziza"):
    _login_google(client, monkeypatch, sub, email, name)
    client.post("/auth/role", data={"role": "doctor"})
    client.post("/doctor/profile", data={
        "full_name": name, "birth_date": "1980-01-01", "phone": "+998900000000",
        "specialties": ["1"], "experience_years": "5",
        "documents": [(io.BytesIO(b"%PDF-1.4 x"), "diplom.pdf")],
    }, content_type="multipart/form-data")


def _login_selfsignup_patient(client, monkeypatch, sub, email, name):
    _login_google(client, monkeypatch, sub, email, name)
    # A real browser follows the redirect straight to /patient/profile,
    # which is what lazily creates the patient row (get_or_create_for_user).
    client.post("/auth/role", data={"role": "patient"}, follow_redirects=True)


def test_new_patient_reaches_app_home_without_a_gate(client, monkeypatch):
    _login_selfsignup_patient(client, monkeypatch, "google-pat-1", "p1@example.com", "Bemor 1")
    resp = client.get("/auth/app")
    assert resp.status_code == 200  # unlike doctors, patients aren't blocked


def test_patient_can_edit_own_profile(client, monkeypatch):
    _login_selfsignup_patient(client, monkeypatch, "google-pat-1", "p1@example.com", "Bemor 1")
    resp = client.post("/patient/profile", data={
        "full_name": "Bemor Yangilangan", "phone": "+998911112233",
    }, follow_redirects=True)
    assert "Bemor Yangilangan" in resp.get_data(as_text=True)


def test_doctor_connect_code_is_stable_until_regenerated(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch)
    page1 = client.get("/doctor/profile").get_data(as_text=True)
    page2 = client.get("/doctor/profile").get_data(as_text=True)

    import re
    code1 = re.search(r"font-mono font-semibold tracking-widest text-teal-700\">([A-Z0-9]{8})<", page1).group(1)
    code2 = re.search(r"font-mono font-semibold tracking-widest text-teal-700\">([A-Z0-9]{8})<", page2).group(1)
    assert code1 == code2
    assert not set(code1) & set("0O1IL")


def test_regenerating_code_invalidates_the_old_one(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch)
    page = client.get("/doctor/profile").get_data(as_text=True)
    import re
    old_code = re.search(r"font-mono font-semibold tracking-widest text-teal-700\">([A-Z0-9]{8})<", page).group(1)

    client.post("/doctor/profile/regenerate-code")
    new_page = client.get("/doctor/profile").get_data(as_text=True)
    new_code = re.search(r"font-mono font-semibold tracking-widest text-teal-700\">([A-Z0-9]{8})<", new_page).group(1)
    assert new_code != old_code

    client.post("/auth/logout")
    _login_selfsignup_patient(client, monkeypatch, "google-pat-x", "px@example.com", "X")
    resp = client.post("/patient/connect", data={"code": old_code}, follow_redirects=True)
    assert "Kod topilmadi" in resp.get_data(as_text=True)


def test_patient_links_to_doctor_without_losing_existing_data(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch)
    page = client.get("/doctor/profile").get_data(as_text=True)
    import re
    doctor_code = re.search(r"font-mono font-semibold tracking-widest text-teal-700\">([A-Z0-9]{8})<", page).group(1)
    client.post("/auth/logout")

    _login_selfsignup_patient(client, monkeypatch, "google-pat-1", "p1@example.com", "Ozod Karimov")

    # the patient enters their own diagnosis before ever connecting to a doctor
    from repos import patient_repo, user_identity_repo
    with client.application.app_context():
        identity = user_identity_repo.find("google", "google-pat-1")
        patient = patient_repo.get_by_user(identity["user_id"])
        patient_id = patient["id"]
        assert patient["doctor_id"] is None

    client.post("/care/patients/%d/diagnoses" % patient_id, data={"text": "O'zim kiritgan tashxis"},
                content_type="multipart/form-data")

    connect = client.post("/patient/connect", data={"code": doctor_code})
    assert connect.status_code == 302

    with client.application.app_context():
        patient = patient_repo.get(patient_id)
        assert patient["doctor_id"] is not None

    diagnoses = client.get("/api/v1/care/patients/%d/diagnoses" % patient_id)
    items = diagnoses.get_json()["data"]["diagnoses"]
    assert any(d["diagnosis"]["text"] == "O'zim kiritgan tashxis" for d in items)


def test_doctor_can_now_see_and_edit_the_connected_patient(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch, sub="google-doc-2", email="doc2@example.com",
                             name="Dr. Bek")
    page = client.get("/doctor/profile").get_data(as_text=True)
    import re
    doctor_code = re.search(r"font-mono font-semibold tracking-widest text-teal-700\">([A-Z0-9]{8})<", page).group(1)
    client.post("/auth/logout")

    _login_selfsignup_patient(client, monkeypatch, "google-pat-2", "p2@example.com", "Kimdir")
    client.post("/patient/connect", data={"code": doctor_code})

    from repos import patient_repo, user_identity_repo
    with client.application.app_context():
        identity = user_identity_repo.find("google", "google-pat-2")
        patient_id = patient_repo.get_by_user(identity["user_id"])["id"]

    client.post("/auth/logout")
    _login_google(client, monkeypatch, "google-doc-2", "doc2@example.com", "Dr. Bek")

    med = client.post("/api/v1/care/patients/%d/medications" % patient_id, json={
        "drug_name": "Metformin", "times": ["08:00"], "start_date": "2026-01-01",
    })
    assert med.status_code == 200


def test_unlinked_doctor_cannot_see_selfsignup_patient(client, monkeypatch):
    _login_selfsignup_patient(client, monkeypatch, "google-pat-3", "p3@example.com", "Biri")
    from repos import patient_repo, user_identity_repo
    with client.application.app_context():
        identity = user_identity_repo.find("google", "google-pat-3")
        patient_id = patient_repo.get_by_user(identity["user_id"])["id"]
    client.post("/auth/logout")

    _login_completed_doctor(client, monkeypatch, sub="google-doc-3", email="doc3@example.com",
                             name="Dr. Boshqa")
    resp = client.get("/care/patients/%d" % patient_id)
    assert resp.status_code == 403


def test_patient_can_disconnect_and_keep_history(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch, sub="google-doc-4", email="doc4@example.com",
                             name="Dr. To'rt")
    page = client.get("/doctor/profile").get_data(as_text=True)
    import re
    doctor_code = re.search(r"font-mono font-semibold tracking-widest text-teal-700\">([A-Z0-9]{8})<", page).group(1)
    client.post("/auth/logout")

    _login_selfsignup_patient(client, monkeypatch, "google-pat-4", "p4@example.com", "To'rtinchi")
    client.post("/patient/connect", data={"code": doctor_code})

    from repos import patient_repo, user_identity_repo
    with client.application.app_context():
        identity = user_identity_repo.find("google", "google-pat-4")
        patient_id = patient_repo.get_by_user(identity["user_id"])["id"]
        assert patient_repo.get(patient_id)["doctor_id"] is not None

    client.post("/care/patients/%d/diagnoses" % patient_id, data={"text": "Tarixiy tashxis"},
                content_type="multipart/form-data")

    client.post("/patient/disconnect")
    with client.application.app_context():
        assert patient_repo.get(patient_id)["doctor_id"] is None

    diagnoses = client.get("/api/v1/care/patients/%d/diagnoses" % patient_id)
    items = diagnoses.get_json()["data"]["diagnoses"]
    assert any(d["diagnosis"]["text"] == "Tarixiy tashxis" for d in items)


def test_expired_connect_code_is_rejected(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch, sub="google-doc-5", email="doc5@example.com",
                             name="Dr. Besh")
    from repos import doctor_repo, user_identity_repo

    with client.application.app_context():
        identity = user_identity_repo.find("google", "google-doc-5")
        doctor = doctor_repo.get_by_user(identity["user_id"])
        expired = (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")
        doctor_repo.set_connect_code(doctor["id"], "EXPIREDX", expired)

    client.post("/auth/logout")
    _login_selfsignup_patient(client, monkeypatch, "google-pat-5", "p5@example.com", "Beshinchi")
    resp = client.post("/patient/connect", data={"code": "EXPIREDX"}, follow_redirects=True)
    assert "muddati" in resp.get_data(as_text=True)  # apostrophe is HTML-escaped by Jinja
