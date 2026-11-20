"""Module A — auth: Google/Telegram login, role selection, session guards.

Google's token/userinfo endpoints and Telegram's HMAC signature are the only
"network" involved, and both are handled without ever making a real request:
Google's `requests.post`/`requests.get` are monkeypatched, and the Telegram
payload is signed locally with the same algorithm `identity_providers/
telegram.py` verifies against. No real OAuth round-trip, no real bot.
"""

import hashlib
import hmac
import time
import urllib.parse

from config import Config
from tests.test_smoke import app, client  # noqa: F401  (fixture reuse)


def _state_from_redirect(resp):
    location = urllib.parse.urlparse(resp.headers["Location"])
    return urllib.parse.parse_qs(location.query)["state"][0]


def _sign_telegram_payload(bot_token, fields):
    check_string = "\n".join(
        "%s=%s" % (k, v) for k, v in sorted(fields.items())
    )
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    digest = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return {**fields, "hash": digest}


# --- login page -------------------------------------------------------

def test_login_page_shows_providers_as_disabled_when_unconfigured(client):
    body = client.get("/auth/login").get_data(as_text=True)
    assert "sozlanmagan" in body
    assert "hozircha mavjud emas" in body  # dmed


def test_app_home_requires_login(client):
    resp = client.get("/auth/app")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/login")


# --- Google flow --------------------------------------------------------

def test_google_login_creates_user_and_prompts_role(client, monkeypatch):
    from identity_providers import google

    monkeypatch.setattr(Config, "GOOGLE_CLIENT_ID", "test-id")
    monkeypatch.setattr(Config, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(Config, "GOOGLE_REDIRECT_URI", "http://localhost/auth/google/callback")

    class FakeTokenResponse:
        def json(self):
            return {"access_token": "fake-access-token"}

    class FakeProfileResponse:
        def json(self):
            return {"sub": "google-42", "name": "Ali Valiyev", "email": "ali@example.com"}

    monkeypatch.setattr(google.requests, "post", lambda *a, **k: FakeTokenResponse())
    monkeypatch.setattr(google.requests, "get", lambda *a, **k: FakeProfileResponse())

    start = client.get("/auth/google/start")
    assert start.status_code == 302
    state = _state_from_redirect(start)

    callback = client.get("/auth/google/callback?state=%s&code=whatever" % state)
    assert callback.status_code == 302
    assert callback.headers["Location"].endswith("/auth/role")

    home_before_role = client.get("/auth/app")
    assert home_before_role.status_code == 302
    assert home_before_role.headers["Location"].endswith("/auth/role")

    # "patient" here, not "doctor" — Module B gates doctors behind profile
    # completion before /auth/app renders; that path is covered in
    # test_doctor_profile.py::test_new_doctor_is_redirected_to_profile_form.
    # Module D then sends a fresh patient to /patient/profile first (there's
    # somewhere to fill in name/phone/diagnosis) rather than straight to
    # /auth/app, which stays reachable and ungated regardless.
    role_pick = client.post("/auth/role", data={"role": "patient"})
    assert role_pick.status_code == 302
    assert role_pick.headers["Location"].endswith("/patient/profile")

    home = client.get("/auth/app")
    assert home.status_code == 200
    assert "Ali Valiyev" in home.get_data(as_text=True)
    assert "Bemor" in home.get_data(as_text=True)


def test_google_login_is_idempotent_per_identity(client, monkeypatch):
    """Logging in twice with the same Google sub must not create a second user."""
    from identity_providers import google
    from repos import user_repo

    monkeypatch.setattr(Config, "GOOGLE_CLIENT_ID", "test-id")
    monkeypatch.setattr(Config, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(Config, "GOOGLE_REDIRECT_URI", "http://localhost/auth/google/callback")

    class FakeTokenResponse:
        def json(self):
            return {"access_token": "fake-access-token"}

    class FakeProfileResponse:
        def json(self):
            return {"sub": "google-99", "name": "Bekzod", "email": "bekzod@example.com"}

    monkeypatch.setattr(google.requests, "post", lambda *a, **k: FakeTokenResponse())
    monkeypatch.setattr(google.requests, "get", lambda *a, **k: FakeProfileResponse())

    for _ in range(2):
        start = client.get("/auth/google/start")
        state = _state_from_redirect(start)
        client.get("/auth/google/callback?state=%s&code=whatever" % state)

    with client.application.app_context():
        assert user_repo.get(1) is not None
        assert user_repo.get(2) is None  # second login reused the same user


def test_google_callback_rejects_mismatched_state(client, monkeypatch):
    from identity_providers import google

    monkeypatch.setattr(Config, "GOOGLE_CLIENT_ID", "test-id")
    monkeypatch.setattr(Config, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(Config, "GOOGLE_REDIRECT_URI", "http://localhost/auth/google/callback")

    called = {"n": 0}

    def fail_if_called(*a, **k):
        called["n"] += 1
        raise AssertionError("token exchange must not happen on bad state")

    monkeypatch.setattr(google.requests, "post", fail_if_called)

    client.get("/auth/google/start")
    resp = client.get("/auth/google/callback?state=wrong&code=whatever")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/login")
    assert called["n"] == 0


# --- Telegram flow --------------------------------------------------------

def test_telegram_login_verifies_signature_and_creates_user(client, monkeypatch):
    monkeypatch.setattr(Config, "TELEGRAM_BOT_TOKEN", "test-bot-token")
    monkeypatch.setattr(Config, "TELEGRAM_BOT_USERNAME", "hamroh_bot")

    fields = _sign_telegram_payload("test-bot-token", {
        "id": "555",
        "first_name": "Nodira",
        "auth_date": str(int(time.time())),
    })
    resp = client.get("/auth/telegram/callback?" + urllib.parse.urlencode(fields))
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/role")


def test_telegram_login_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setattr(Config, "TELEGRAM_BOT_TOKEN", "test-bot-token")
    monkeypatch.setattr(Config, "TELEGRAM_BOT_USERNAME", "hamroh_bot")

    fields = {
        "id": "556",
        "first_name": "Nodira",
        "auth_date": str(int(time.time())),
        "hash": "not-a-real-signature",
    }
    resp = client.get("/auth/telegram/callback?" + urllib.parse.urlencode(fields))
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/login")


# --- dmed stub --------------------------------------------------------

def test_dmed_start_is_unavailable_by_default(client):
    resp = client.get("/auth/dmed/start")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/login")
    body = client.get("/auth/login").get_data(as_text=True)
    assert "hozircha mavjud emas" in body


# --- logout --------------------------------------------------------

def test_logout_clears_session(client, monkeypatch):
    from identity_providers import google

    monkeypatch.setattr(Config, "GOOGLE_CLIENT_ID", "test-id")
    monkeypatch.setattr(Config, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(Config, "GOOGLE_REDIRECT_URI", "http://localhost/auth/google/callback")

    class FakeTokenResponse:
        def json(self):
            return {"access_token": "fake-access-token"}

    class FakeProfileResponse:
        def json(self):
            return {"sub": "google-7", "name": "Test User", "email": "t@example.com"}

    monkeypatch.setattr(google.requests, "post", lambda *a, **k: FakeTokenResponse())
    monkeypatch.setattr(google.requests, "get", lambda *a, **k: FakeProfileResponse())

    start = client.get("/auth/google/start")
    state = _state_from_redirect(start)
    client.get("/auth/google/callback?state=%s&code=whatever" % state)
    client.post("/auth/role", data={"role": "patient"})
    assert client.get("/auth/app").status_code == 200

    client.post("/auth/logout")
    resp = client.get("/auth/app")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/auth/login")


# --- old demo routes stay untouched ----------------------------------

def test_legacy_demo_routes_still_work_without_login(client):
    assert client.get("/").status_code == 200
    assert client.get("/patient/1/chat").status_code == 200
    assert client.get("/doctor/1/dashboard").status_code == 200
