"""Module F — trend visibility for patients + motivation messages.

Reuses the existing seeded demo patient (id 1, persona "bobur") to drive
real risk transitions through the actual analyzer pipeline via
test_smoke's advance()/send() helpers — motivation messages ride on the
same `assessment.created` event the risk-alert pipeline already emits.
"""

from datetime import datetime, timedelta

import pytest

from config import Config
from repos import assessment_repo, medication_repo
from services.motivation_service import evaluate_and_notify
from tests.test_smoke import app, client  # noqa: F401  (fixture reuse)
from tests.test_smoke import advance, data, send


@pytest.fixture(autouse=True)
def _isolate_uploads(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "UPLOAD_DIR", str(tmp_path))


def test_no_motivation_with_fewer_than_two_assessments(client):
    with client.application.app_context():
        assessment_repo.create(1, "green", risk_score=10)
        assert evaluate_and_notify(1) is False


def test_motivation_fires_on_genuine_improvement(client, monkeypatch):
    from notifiers import push_notifier
    sent = []
    monkeypatch.setattr(push_notifier, "send_to_subscriber",
                         lambda *a, **k: sent.append((a, k)))

    with client.application.app_context():
        assessment_repo.create(1, "red", risk_score=90)
        assessment_repo.create(1, "green", risk_score=15)
        assert evaluate_and_notify(1) is True
        assert len(sent) == 1
        assert sent[0][0][0] == "patient"
        assert sent[0][0][1] == 1


def test_motivation_does_not_fire_on_worsening_or_flat_trend(client, monkeypatch):
    from notifiers import push_notifier
    sent = []
    monkeypatch.setattr(push_notifier, "send_to_subscriber",
                         lambda *a, **k: sent.append((a, k)))

    with client.application.app_context():
        assessment_repo.create(1, "green", risk_score=15)
        assessment_repo.create(1, "red", risk_score=90)
        assert evaluate_and_notify(1) is False  # worsening

        assessment_repo.create(1, "red", risk_score=85)  # same level, tiny delta
        assert evaluate_and_notify(1) is False
    assert sent == []


def test_motivation_is_capped_at_once_per_day(client, monkeypatch):
    from notifiers import push_notifier
    sent = []
    monkeypatch.setattr(push_notifier, "send_to_subscriber",
                         lambda *a, **k: sent.append((a, k)))

    with client.application.app_context():
        assessment_repo.create(1, "red", risk_score=90)
        assessment_repo.create(1, "green", risk_score=10)
        assert evaluate_and_notify(1, now=datetime(2026, 6, 1, 9, 0)) is True

        # another improvement later the same day -> deduped, no second push
        assessment_repo.create(1, "red", risk_score=95)
        assessment_repo.create(1, "green", risk_score=5)
        assert evaluate_and_notify(1, now=datetime(2026, 6, 1, 18, 0)) is False
    assert len(sent) == 1

    # next day -> allowed again
    with client.application.app_context():
        assert evaluate_and_notify(1, now=datetime(2026, 6, 2, 9, 0)) is True
    assert len(sent) == 2


def test_motivation_attributes_improvement_to_a_recent_care_plan_change(client, monkeypatch):
    from notifiers import push_notifier
    sent = []
    monkeypatch.setattr(push_notifier, "send_to_subscriber",
                         lambda *a, **k: sent.append((a, k)))

    with client.application.app_context():
        medication_repo.create(
            1, "Metformin", "500 mg", "[]", "2026-01-01", None, "doctor", None)
        assessment_repo.create(1, "red", risk_score=90)
        assessment_repo.create(1, "green", risk_score=10)
        evaluate_and_notify(1, now=datetime.now())

    assert "yangilagandan" in sent[0][1]["body"]


def test_motivation_fires_through_the_real_pipeline_on_a_red_to_green_transition(client, monkeypatch):
    from notifiers import push_notifier
    sent = []
    monkeypatch.setattr(push_notifier, "send_to_subscriber",
                         lambda *a, **k: sent.append((a, k)))

    advance(client, 1)
    send(client, 1, "Nafasimdan aseton hidi kelyapti, qustim")  # day1: red (keyword)
    advance(client, 1)
    send(client, 1, "120/80")  # day2 (blood_pressure): green, within target

    assert any(k.get("title") == "Yaxshi xabar!" for a, k in sent)


def test_trend_api_requires_login_and_patient_access(client, monkeypatch):
    resp = client.get("/api/v1/care/patients/1/trend")
    assert resp.status_code == 401

    import io
    import urllib.parse
    from identity_providers import google

    monkeypatch.setattr(Config, "GOOGLE_CLIENT_ID", "test-id")
    monkeypatch.setattr(Config, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(Config, "GOOGLE_REDIRECT_URI", "http://localhost/auth/google/callback")

    class FakeTokenResponse:
        def json(self):
            return {"access_token": "tok"}

    class FakeProfileResponse:
        def json(self):
            return {"sub": "google-doc-unrelated", "name": "Dr Unrelated", "email": "u@example.com"}

    monkeypatch.setattr(google.requests, "post", lambda *a, **k: FakeTokenResponse())
    monkeypatch.setattr(google.requests, "get", lambda *a, **k: FakeProfileResponse())

    start = client.get("/auth/google/start")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(start.headers["Location"]).query)["state"][0]
    client.get("/auth/google/callback?state=%s&code=whatever" % state)
    client.post("/auth/role", data={"role": "doctor"})
    client.post("/doctor/profile", data={
        "full_name": "Dr Unrelated", "birth_date": "1980-01-01", "phone": "+998900000000",
        "specialties": ["1"], "experience_years": "5",
        "documents": [(io.BytesIO(b"%PDF-1.4 x"), "d.pdf")],
    }, content_type="multipart/form-data")

    # patient 1 is seeded under a different (demo) doctor — this doctor is unrelated
    resp = client.get("/api/v1/care/patients/1/trend")
    assert resp.status_code == 403
