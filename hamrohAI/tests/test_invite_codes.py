"""Module C — doctor-added patient + one-time invite code redemption."""

import io
import re
import urllib.parse

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


def _add_patient(client, full_name="Yangi Bemor", diagnosis="2-tur diabet"):
    resp = client.post("/doctor/patients/add", data={
        "full_name": full_name, "phone": "+998901112233", "diagnosis": diagnosis,
        "files": [(io.BytesIO(b"%PDF-1.4 x"), "natija.pdf")],
    }, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    match = re.search(r'font-mono font-semibold tracking-widest[^>]*>([A-Z0-9]{7})<', body)
    assert match, body
    return match.group(1)


def test_code_uses_only_dictation_safe_characters(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch)
    code = _add_patient(client)
    assert len(code) == 7
    assert not set(code) & set("0O1IL")


def test_doctor_patients_page_lists_new_patient_and_code(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch)
    code = _add_patient(client, full_name="Kamola Yusupova")
    page = client.get("/doctor/patients").get_data(as_text=True)
    assert "Kamola Yusupova" in page
    assert code in page
    assert "Kutilmoqda" in page


def test_new_user_redeems_code_and_inherits_prepared_profile(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch)
    code = _add_patient(client, full_name="Aziz Rahimov", diagnosis="Gipertoniya")

    from repos import invite_code_repo
    with client.application.app_context():
        patient_id = invite_code_repo.find_by_code(code)["patient_id"]

    client.post("/auth/logout")

    _login_google(client, monkeypatch, sub="google-pat-1", email="pat@example.com",
                  name="Aziz Rahimov")
    resp = client.post("/patient/redeem-code", data={"code": code})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/app")

    home = client.get("/auth/app")
    assert home.status_code == 200
    assert "Bemor" in home.get_data(as_text=True)

    diagnoses = client.get("/api/v1/care/patients/%d/diagnoses" % patient_id)
    assert diagnoses.status_code == 200
    items = diagnoses.get_json()["data"]["diagnoses"]
    assert any(d["diagnosis"]["text"] == "Gipertoniya" for d in items)


def test_code_is_case_and_dash_insensitive(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch)
    code = _add_patient(client)
    client.post("/auth/logout")

    _login_google(client, monkeypatch, sub="google-pat-2", email="pat2@example.com", name="X")
    lowered = code[:3].lower() + "-" + code[3:].lower()
    resp = client.post("/patient/redeem-code", data={"code": lowered})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/app")


def test_code_cannot_be_redeemed_twice(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch)
    code = _add_patient(client)
    client.post("/auth/logout")

    _login_google(client, monkeypatch, sub="google-pat-a", email="a@example.com", name="A")
    client.post("/patient/redeem-code", data={"code": code})
    client.post("/auth/logout")

    _login_google(client, monkeypatch, sub="google-pat-b", email="b@example.com", name="B")
    resp = client.post("/patient/redeem-code", data={"code": code}, follow_redirects=True)
    assert "allaqachon ishlatilgan" in resp.get_data(as_text=True)


def test_unknown_code_gives_clear_error(client, monkeypatch):
    _login_google(client, monkeypatch, sub="google-pat-z", email="z@example.com", name="Z")
    resp = client.post("/patient/redeem-code", data={"code": "ZZZZZZZ"}, follow_redirects=True)
    assert "Kod topilmadi" in resp.get_data(as_text=True)


def test_user_with_existing_role_cannot_redeem(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch)
    code = _add_patient(client)
    client.post("/auth/logout")

    _login_google(client, monkeypatch, sub="google-pat-c", email="c@example.com", name="C")
    client.post("/auth/role", data={"role": "patient"})  # already has a role

    resp = client.post("/patient/redeem-code", data={"code": code}, follow_redirects=True)
    assert "allaqachon profil mavjud" in resp.get_data(as_text=True)


def test_redeem_page_requires_login(client):
    resp = client.get("/patient/redeem-code")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/login")


def test_only_doctors_can_add_patients(client, monkeypatch):
    _login_google(client, monkeypatch, sub="google-pat-d", email="d@example.com", name="D")
    client.post("/auth/role", data={"role": "patient"})
    resp = client.get("/doctor/patients")
    assert resp.status_code == 403
