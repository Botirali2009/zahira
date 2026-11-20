"""Module G — one-time doctor consultation requests."""

import io
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


def _login_completed_doctor(client, monkeypatch, sub, email, name, specialty_id="1"):
    _login_google(client, monkeypatch, sub, email, name)
    client.post("/auth/role", data={"role": "doctor"})
    client.post("/doctor/profile", data={
        "full_name": name, "birth_date": "1980-01-01", "phone": "+998900000000",
        "specialties": [specialty_id], "experience_years": "5",
        "documents": [(io.BytesIO(b"%PDF-1.4 x"), "d.pdf")],
    }, content_type="multipart/form-data")


def _login_selfsignup_patient(client, monkeypatch, sub, email, name):
    _login_google(client, monkeypatch, sub, email, name)
    client.post("/auth/role", data={"role": "patient"}, follow_redirects=True)


def _current_patient_id(client, sub):
    from repos import patient_repo, user_identity_repo
    with client.application.app_context():
        identity = user_identity_repo.find("google", sub)
        return patient_repo.get_by_user(identity["user_id"])["id"]


def _verify_doctor(client, sub):
    """Module B's admin-verification step, applied directly at the repo
    layer — that flow is Module B's own concern to test, not Module G's."""
    from repos import doctor_repo, user_identity_repo
    with client.application.app_context():
        identity = user_identity_repo.find("google", sub)
        doctor = doctor_repo.get_by_user(identity["user_id"])
        doctor_repo.mark_verified(doctor["id"])


def test_doctor_can_toggle_consultation_availability(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch, "google-doc-1", "d1@example.com", "Dr One")
    before = client.get("/doctor/profile").get_data(as_text=True)
    assert "Konsultatsiyaga tayyorman deb belgilash" in before

    client.post("/doctor/profile/consultation-toggle")
    after = client.get("/doctor/profile").get_data(as_text=True)
    assert "Konsultatsiyaga tayyorman ✓" in after


def test_request_notifies_only_matching_available_verified_doctors(client, monkeypatch):
    from notifiers import push_notifier
    sent = []
    monkeypatch.setattr(push_notifier, "send_to_subscriber",
                         lambda *a, **k: sent.append((a, k)))

    # Doctor A: right specialty, verified, available -> should be notified
    _login_completed_doctor(client, monkeypatch, "google-doc-a", "a@example.com", "Dr A",
                             specialty_id="1")
    client.post("/doctor/profile/consultation-toggle")
    client.post("/auth/logout")
    _verify_doctor(client, "google-doc-a")

    # Doctor B: right specialty, verified, but NOT toggled available -> must not be notified
    _login_completed_doctor(client, monkeypatch, "google-doc-b", "b@example.com", "Dr B",
                             specialty_id="1")
    client.post("/auth/logout")
    _verify_doctor(client, "google-doc-b")

    # Doctor C: verified, available, but wrong specialty -> must not be notified
    _login_completed_doctor(client, monkeypatch, "google-doc-c", "c@example.com", "Dr C",
                             specialty_id="2")
    client.post("/doctor/profile/consultation-toggle")
    client.post("/auth/logout")
    _verify_doctor(client, "google-doc-c")

    _login_selfsignup_patient(client, monkeypatch, "google-pat-1", "p1@example.com", "Bemor")
    resp = client.post("/patient/consultations", data={
        "specialty_id": "1", "question": "Qandim ko'tarilib ketyapti, nima qilishim kerak?",
    }, follow_redirects=True)
    assert "yuborildi" in resp.get_data(as_text=True)

    doctor_recipients = [a[1] for a, k in sent if a[0] == "doctor"]
    assert len(doctor_recipients) == 1  # only Dr A


def test_first_doctor_to_accept_wins_the_race(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch, "google-doc-a", "a@example.com", "Dr A")
    client.post("/doctor/profile/consultation-toggle")
    client.post("/auth/logout")
    _verify_doctor(client, "google-doc-a")

    _login_selfsignup_patient(client, monkeypatch, "google-pat-1", "p1@example.com", "Bemor")
    client.post("/patient/consultations", data={"specialty_id": "1", "question": "Savol"})
    patient_id = _current_patient_id(client, "google-pat-1")
    client.post("/auth/logout")

    from repos import consultation_repo
    with client.application.app_context():
        consultation_id = consultation_repo.list_for_patient(patient_id)[0]["id"]

    _login_completed_doctor(client, monkeypatch, "google-doc-b", "b@example.com", "Dr B")
    client.post("/doctor/profile/consultation-toggle")
    _verify_doctor(client, "google-doc-b")

    with client.application.app_context():
        from repos import doctor_repo, user_identity_repo
        from services import consultation_service

        doc_a_id = doctor_repo.get_by_user(
            user_identity_repo.find("google", "google-doc-a")["user_id"])["id"]
        doc_b_id = doctor_repo.get_by_user(
            user_identity_repo.find("google", "google-doc-b")["user_id"])["id"]
        doctor_a = doctor_repo.get(doc_a_id)
        doctor_b = doctor_repo.get(doc_b_id)

        consultation_service.accept(doctor_a, consultation_id)
        with pytest.raises(Exception):
            consultation_service.accept(doctor_b, consultation_id)

        consultation = consultation_repo.get(consultation_id)
        assert consultation["accepted_by_doctor_id"] == doc_a_id


def test_full_flow_accept_and_answer_reaches_patient(client, monkeypatch):
    from notifiers import push_notifier
    sent = []
    monkeypatch.setattr(push_notifier, "send_to_subscriber",
                         lambda *a, **k: sent.append((a, k)))

    _login_completed_doctor(client, monkeypatch, "google-doc-a", "a@example.com", "Dr A")
    client.post("/doctor/profile/consultation-toggle")
    client.post("/auth/logout")
    _verify_doctor(client, "google-doc-a")

    _login_selfsignup_patient(client, monkeypatch, "google-pat-1", "p1@example.com", "Bemor")
    client.post("/care/patients/%d/diagnoses" % _current_patient_id(client, "google-pat-1"),
                data={"text": "2-tur diabet"}, content_type="multipart/form-data")
    client.post("/patient/consultations", data={
        "specialty_id": "1", "question": "Dozani oshirsam bo'ladimi?",
    })
    client.post("/auth/logout")

    _login_google(client, monkeypatch, "google-doc-a", "a@example.com", "Dr A")
    open_page = client.get("/doctor/consultations").get_data(as_text=True)
    assert "2-tur diabet" in open_page
    assert "Dozani oshirsam" in open_page

    from repos import consultation_repo
    with client.application.app_context():
        consultation_id = consultation_repo.list_open_for_specialty(1)[0]["id"]

    client.post("/doctor/consultations/%d/accept" % consultation_id)
    client.post("/doctor/consultations/%d/answer" % consultation_id,
                data={"answer": "Yo'q, avval shifokorga ko'rining."})

    assert any(k.get("title") == "Shifokor javob berdi" for a, k in sent)
    client.post("/auth/logout")

    _login_google(client, monkeypatch, "google-pat-1", "p1@example.com", "Bemor")
    patient_page = client.get("/patient/consultations").get_data(as_text=True)
    assert "Yo&#39;q, avval shifokorga ko&#39;ring" in patient_page or \
        "avval shifokorga" in patient_page


def test_unrelated_doctor_cannot_answer_someone_elses_accepted_consultation(client, monkeypatch):
    _login_completed_doctor(client, monkeypatch, "google-doc-a", "a@example.com", "Dr A")
    client.post("/doctor/profile/consultation-toggle")
    client.post("/auth/logout")
    _verify_doctor(client, "google-doc-a")

    _login_selfsignup_patient(client, monkeypatch, "google-pat-1", "p1@example.com", "Bemor")
    client.post("/patient/consultations", data={"specialty_id": "1", "question": "Savol"})
    client.post("/auth/logout")

    _login_google(client, monkeypatch, "google-doc-a", "a@example.com", "Dr A")
    from repos import consultation_repo
    with client.application.app_context():
        consultation_id = consultation_repo.list_open_for_specialty(1)[0]["id"]
    client.post("/doctor/consultations/%d/accept" % consultation_id)
    client.post("/auth/logout")

    _login_completed_doctor(client, monkeypatch, "google-doc-b", "b@example.com", "Dr B")
    client.post("/doctor/profile/consultation-toggle")
    _verify_doctor(client, "google-doc-b")
    client.post("/doctor/consultations/%d/answer" % consultation_id,
                data={"answer": "Men javob beraman"})

    with client.application.app_context():
        consultation = consultation_repo.get(consultation_id)
        assert consultation["status"] == "accepted"
        assert consultation["answer_text"] is None


def test_request_disabled_by_feature_flag(client, monkeypatch):
    import config
    monkeypatch.setattr(config.features, "_flags",
                         {**config.features._flags, "consultation": False})

    _login_selfsignup_patient(client, monkeypatch, "google-pat-1", "p1@example.com", "Bemor")
    resp = client.post("/patient/consultations", data={"specialty_id": "1", "question": "Savol"},
                        follow_redirects=True)
    assert "o&#39;chirilgan" in resp.get_data(as_text=True) or "chirilgan" in resp.get_data(as_text=True)

    patient_id = _current_patient_id(client, "google-pat-1")
    from repos import consultation_repo
    with client.application.app_context():
        assert consultation_repo.list_for_patient(patient_id) == []


def test_consultation_pages_require_correct_role(client, monkeypatch):
    resp = client.get("/patient/consultations")
    assert resp.status_code == 302

    _login_completed_doctor(client, monkeypatch, "google-doc-a", "a@example.com", "Dr A")
    resp = client.get("/patient/consultations")
    assert resp.status_code == 403
