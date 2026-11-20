"""Module B — doctor profile completion + admin verification.

Builds on the Google-login mocking pattern from test_auth.py to get a
logged-in doctor session, then exercises the profile form (validation,
file upload, access control) and the admin verification flow.
"""

import io

import pytest

from config import Config
from tests.test_smoke import app, client  # noqa: F401  (fixture reuse)


@pytest.fixture(autouse=True)
def _isolate_uploads(monkeypatch, tmp_path):
    """Never let a test write into the real project uploads/ directory."""
    monkeypatch.setattr(Config, "UPLOAD_DIR", str(tmp_path))


def _login_as_new_doctor(client, monkeypatch, sub="google-doc-1", email="doc@example.com",
                          name="Dr. Aziza"):
    from identity_providers import google

    monkeypatch.setattr(Config, "GOOGLE_CLIENT_ID", "test-id")
    monkeypatch.setattr(Config, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(Config, "GOOGLE_REDIRECT_URI", "http://localhost/auth/google/callback")

    class FakeTokenResponse:
        def json(self):
            return {"access_token": "fake-access-token"}

    class FakeProfileResponse:
        def json(self):
            return {"sub": sub, "name": name, "email": email}

    monkeypatch.setattr(google.requests, "post", lambda *a, **k: FakeTokenResponse())
    monkeypatch.setattr(google.requests, "get", lambda *a, **k: FakeProfileResponse())

    import urllib.parse
    start = client.get("/auth/google/start")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(start.headers["Location"]).query)["state"][0]
    client.get("/auth/google/callback?state=%s&code=whatever" % state)
    client.post("/auth/role", data={"role": "doctor"})


def _pdf_file(name="diplom.pdf"):
    return (io.BytesIO(b"%PDF-1.4 fake pdf content"), name)


def test_new_doctor_is_redirected_to_profile_form(client, monkeypatch):
    _login_as_new_doctor(client, monkeypatch)
    resp = client.get("/auth/app")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/doctor/profile")


def test_profile_form_rejects_missing_document(client, monkeypatch):
    _login_as_new_doctor(client, monkeypatch)
    resp = client.post("/doctor/profile", data={
        "full_name": "Dr. Aziza Rustamova",
        "birth_date": "1985-04-12",
        "phone": "+998901112233",
        "specialties": ["1"],
        "experience_years": "10",
    }, content_type="multipart/form-data", follow_redirects=True)
    assert "Kamida bitta hujjat" in resp.get_data(as_text=True)


def test_profile_form_completes_with_document_and_specialties(client, monkeypatch):
    _login_as_new_doctor(client, monkeypatch)
    resp = client.post("/doctor/profile", data={
        "full_name": "Dr. Aziza Rustamova",
        "birth_date": "1985-04-12",
        "phone": "+998901112233",
        "specialties": ["1", "2"],
        "experience_years": "10",
        "workplace": "Qarshi shahar OSHP",
        "documents": [_pdf_file()],
    }, content_type="multipart/form-data")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/app")

    home = client.get("/auth/app")
    assert home.status_code == 200  # profile complete now, no more bounce

    profile = client.get("/doctor/profile").get_data(as_text=True)
    assert "Tasdiqlanmagan" in profile  # not verified yet
    assert "diplom.pdf" in profile


def test_documents_are_not_accessible_to_other_doctors(client, monkeypatch):
    _login_as_new_doctor(client, monkeypatch, sub="google-doc-A", email="a@example.com")
    client.post("/doctor/profile", data={
        "full_name": "Doctor A", "birth_date": "1980-01-01", "phone": "+998900000001",
        "specialties": ["1"], "experience_years": "5", "documents": [_pdf_file("a-diplom.pdf")],
    }, content_type="multipart/form-data")

    import re
    profile_html = client.get("/doctor/profile").get_data(as_text=True)
    doc_id = re.search(r"/files/doctor-documents/(\d+)", profile_html).group(1)

    client.post("/auth/logout")
    _login_as_new_doctor(client, monkeypatch, sub="google-doc-B", email="b@example.com")

    resp = client.get("/files/doctor-documents/%s" % doc_id)
    assert resp.status_code == 403


def test_admin_can_verify_a_pending_doctor(client, monkeypatch):
    monkeypatch.setattr(Config, "ADMIN_EMAILS", "admin@example.com")

    _login_as_new_doctor(client, monkeypatch, sub="google-doc-C", email="c@example.com",
                          name="Doctor C")
    client.post("/doctor/profile", data={
        "full_name": "Doctor C", "birth_date": "1980-01-01", "phone": "+998900000003",
        "specialties": ["1"], "experience_years": "5", "documents": [_pdf_file()],
    }, content_type="multipart/form-data")
    doctor_profile = client.get("/doctor/profile").get_data(as_text=True)
    assert "Tasdiqlanmagan" in doctor_profile
    client.post("/auth/logout")

    _login_as_new_doctor(client, monkeypatch, sub="google-admin-1", email="admin@example.com",
                          name="Admin")
    client.post("/auth/role", data={"role": "patient"})  # role irrelevant, is_admin gates it

    pending_page = client.get("/admin/doctors")
    assert pending_page.status_code == 200
    assert "Doctor C" in pending_page.get_data(as_text=True)

    import re
    match = re.search(r"/admin/doctors/(\d+)/verify", pending_page.get_data(as_text=True))
    doctor_id = match.group(1)
    verify_resp = client.post("/admin/doctors/%s/verify" % doctor_id)
    assert verify_resp.status_code == 302

    still_pending = client.get("/admin/doctors").get_data(as_text=True)
    assert "Doctor C" not in still_pending


def test_non_admin_cannot_reach_admin_panel(client, monkeypatch):
    _login_as_new_doctor(client, monkeypatch)
    resp = client.get("/admin/doctors")
    assert resp.status_code == 403
