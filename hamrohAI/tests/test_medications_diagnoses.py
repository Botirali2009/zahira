"""Module E — shared medication + diagnosis management.

Module C/D (the real invite-code / self-signup linking flows) don't exist
yet, so these tests link a doctor to a patient directly via the repo layer
— the same end state those modules will produce, just skipping their UI.
"""

import io
from datetime import datetime

import pytest

from config import Config
from repos import patient_repo
from services.medication_reminder_scheduler import check_due_reminders
from tests.test_smoke import app, client  # noqa: F401  (fixture reuse)


@pytest.fixture(autouse=True)
def _isolate_uploads(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "UPLOAD_DIR", str(tmp_path))


def _login_doctor(client, monkeypatch, sub, email, name="Dr. Test"):
    from identity_providers import google
    import urllib.parse

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
    client.post("/auth/role", data={"role": "doctor"})
    client.post("/doctor/profile", data={
        "full_name": name, "birth_date": "1980-01-01", "phone": "+998900000000",
        "specialties": ["1"], "experience_years": "5",
        "documents": [(io.BytesIO(b"%PDF-1.4 x"), "diplom.pdf")],
    }, content_type="multipart/form-data")


def _login_patient(client, monkeypatch, sub, email=None, name="Test Patient"):
    from identity_providers import google
    import urllib.parse

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
    client.post("/auth/role", data={"role": "patient"})


def _setup_doctor_and_patient(client, app, monkeypatch):
    _login_doctor(client, monkeypatch, sub="google-doc-1", email="doc@example.com")
    with app.app_context():
        from repos import doctor_repo as _doctor_repo
        doctor = _doctor_repo.list_all()[-1]
        patient_id = patient_repo.create("Test Patient", "test_persona", doctor["id"])
    return patient_id, doctor["id"]


def test_unauthenticated_cannot_read_medications(client):
    resp = client.get("/api/v1/care/patients/1/medications")
    assert resp.status_code == 401


def test_linked_doctor_can_add_list_update_stop_medication(client, monkeypatch):
    patient_id, _doctor_id = _setup_doctor_and_patient(client, client.application, monkeypatch)

    add = client.post("/api/v1/care/patients/%d/medications" % patient_id, json={
        "drug_name": "Metformin", "dose": "500 mg", "times": ["08:00", "20:00"],
        "start_date": "2026-01-01",
    })
    assert add.status_code == 200
    med = add.get_json()["data"]["medication"]
    assert med["drug_name"] == "Metformin"

    listing = client.get("/api/v1/care/patients/%d/medications" % patient_id)
    meds = listing.get_json()["data"]["medications"]
    assert len(meds) == 1
    assert meds[0]["times"] == ["08:00", "20:00"]

    updated = client.post(
        "/api/v1/care/patients/%d/medications/%d" % (patient_id, med["id"]),
        json={"drug_name": "Metformin", "dose": "850 mg", "times": ["09:00"],
              "start_date": "2026-01-01"},
    )
    assert updated.get_json()["data"]["medication"]["dose"] == "850 mg"

    stopped = client.post(
        "/api/v1/care/patients/%d/medications/%d/stop" % (patient_id, med["id"]))
    assert stopped.get_json()["data"]["medication"]["active"] == 0

    active_only = client.get(
        "/api/v1/care/patients/%d/medications?active_only=1" % patient_id)
    assert active_only.get_json()["data"]["medications"] == []


def test_medication_rejects_bad_time_format(client, monkeypatch):
    patient_id, _ = _setup_doctor_and_patient(client, client.application, monkeypatch)
    resp = client.post("/api/v1/care/patients/%d/medications" % patient_id, json={
        "drug_name": "Aspirin", "times": ["8am"], "start_date": "2026-01-01",
    })
    assert resp.status_code == 422


def test_unrelated_doctor_cannot_touch_another_doctors_patient(client, monkeypatch):
    patient_id, _ = _setup_doctor_and_patient(client, client.application, monkeypatch)
    client.post("/auth/logout")
    _login_doctor(client, monkeypatch, sub="google-doc-2", email="other@example.com",
                  name="Dr. Other")

    resp = client.get("/api/v1/care/patients/%d/medications" % patient_id)
    assert resp.status_code == 403


def test_linked_patient_can_manage_own_diagnosis_and_files(client, monkeypatch):
    patient_id, _doctor_id = _setup_doctor_and_patient(client, client.application, monkeypatch)
    client.post("/auth/logout")

    _login_patient(client, monkeypatch, sub="google-pat-1", email="pat@example.com")
    with client.application.app_context():
        from repos import user_identity_repo
        identity = user_identity_repo.find("google", "google-pat-1")
        patient_repo.set_user_id(patient_id, identity["user_id"])

    add = client.post("/api/v1/care/patients/%d/diagnoses" % patient_id, data={
        "text": "2-tur qandli diabet",
    }, content_type="multipart/form-data")
    assert add.status_code == 200
    diagnosis = add.get_json()["data"]["diagnosis"]["diagnosis"]
    assert diagnosis["created_by"] == "patient"

    closed = client.post(
        "/api/v1/care/patients/%d/diagnoses/%d/status" % (patient_id, diagnosis["id"]),
        json={"status": "closed"},
    )
    assert closed.get_json()["data"]["diagnosis"]["diagnosis"]["status"] == "closed"


def test_other_patient_cannot_see_someone_elses_diagnoses(client, monkeypatch):
    patient_id, _doctor_id = _setup_doctor_and_patient(client, client.application, monkeypatch)
    client.post("/auth/logout")

    _login_patient(client, monkeypatch, sub="google-pat-x", email="x@example.com")
    resp = client.get("/api/v1/care/patients/%d/diagnoses" % patient_id)
    assert resp.status_code == 403


def test_diagnosis_file_access_is_permission_checked(client, monkeypatch):
    patient_id, _doctor_id = _setup_doctor_and_patient(client, client.application, monkeypatch)

    add = client.post("/api/v1/care/patients/%d/diagnoses" % patient_id, data={
        "text": "Tashxis",
        "files": [(io.BytesIO(b"%PDF-1.4 x"), "natija.pdf")],
    }, content_type="multipart/form-data")
    file_id = add.get_json()["data"]["diagnosis"]["files"][0]["id"]

    ok_resp = client.get("/files/diagnosis-files/%d" % file_id)
    assert ok_resp.status_code == 200

    client.post("/auth/logout")
    _login_doctor(client, monkeypatch, sub="google-doc-2", email="other@example.com",
                  name="Dr. Other")
    forbidden = client.get("/files/diagnosis-files/%d" % file_id)
    assert forbidden.status_code == 403


# --- reminder scheduler -------------------------------------------------

def test_reminder_scheduler_fires_once_and_dedupes(client, monkeypatch):
    patient_id, _doctor_id = _setup_doctor_and_patient(client, client.application, monkeypatch)
    client.post("/api/v1/care/patients/%d/medications" % patient_id, json={
        "drug_name": "Insulin", "times": ["08:00"], "start_date": "2020-01-01",
    })

    from notifiers import push_notifier
    sent = []
    monkeypatch.setattr(push_notifier, "send_to_subscriber",
                         lambda *a, **k: sent.append((a, k)))

    with client.application.app_context():
        now = datetime(2026, 6, 1, 8, 0)
        fired = check_due_reminders(now=now)
        assert fired == 1
        assert len(sent) == 1
        assert sent[0][0][0] == "patient"

        # same minute again -> deduped, no second push
        fired_again = check_due_reminders(now=now)
        assert fired_again == 0
        assert len(sent) == 1

        # different time slot -> nothing due
        not_due = check_due_reminders(now=datetime(2026, 6, 1, 9, 0))
        assert not_due == 0


def test_reminder_scheduler_respects_date_range(client, monkeypatch):
    patient_id, _doctor_id = _setup_doctor_and_patient(client, client.application, monkeypatch)
    client.post("/api/v1/care/patients/%d/medications" % patient_id, json={
        "drug_name": "Antibiotik", "times": ["08:00"],
        "start_date": "2026-01-01", "end_date": "2026-01-10",
    })

    from notifiers import push_notifier
    sent = []
    monkeypatch.setattr(push_notifier, "send_to_subscriber",
                         lambda *a, **k: sent.append((a, k)))

    with client.application.app_context():
        after_range = check_due_reminders(now=datetime(2026, 2, 1, 8, 0))
        assert after_range == 0
        assert sent == []
