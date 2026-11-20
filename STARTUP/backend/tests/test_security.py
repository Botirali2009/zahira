"""Authentication, authorisation and tenant isolation.

These are the tests that matter most commercially. Customers are handing over
their entire supplier list and invoice values — one cross-tenant read would end
the company, and a chief accountant asks about exactly this in the first demo.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.security import (
    MAX_PASSWORD_BYTES,
    TokenError,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.testing.corpus import random_invoice, render_pdf


def register(client, **overrides) -> dict:
    payload = {
        "email": f"user-{uuid.uuid4().hex[:8]}@example.uz",
        "password": "juda-kuchli-parol-2026",
        "company_name": "Test Company MChJ",
        **overrides,
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return {"tokens": response.json(), "email": payload["email"],
            "password": payload["password"]}


# --- password and token primitives ------------------------------------------

def test_password_hashing_roundtrip() -> None:
    hashed = hash_password("correct horse battery")
    assert hashed != "correct horse battery"
    assert verify_password("correct horse battery", hashed)
    assert not verify_password("wrong password", hashed)


def test_password_over_bcrypt_limit_is_rejected() -> None:
    """bcrypt silently truncates at 72 bytes; two long passwords would collide."""
    with pytest.raises(ValueError):
        hash_password("a" * (MAX_PASSWORD_BYTES + 1))


def test_verify_password_handles_corrupt_hash() -> None:
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_access_token_cannot_be_used_as_refresh() -> None:
    token = create_token(1, "access")
    with pytest.raises(TokenError):
        decode_token(token, expected_type="refresh")


def test_tampered_token_is_rejected() -> None:
    token = create_token(1, "access")
    with pytest.raises(TokenError):
        decode_token(token[:-4] + "AAAA", expected_type="access")


# --- endpoint authentication -------------------------------------------------

@pytest.mark.parametrize(("method", "path"), [
    ("get", "/api/v1/documents"),
    ("get", "/api/v1/dashboard"),
    ("get", "/api/v1/auth/me"),
    ("get", "/api/v1/exports/history"),
    ("post", "/api/v1/documents/upload"),
])
def test_endpoints_require_authentication(client, method: str, path: str) -> None:
    client.headers.pop("Authorization", None)
    response = getattr(client, method)(path)
    assert response.status_code == 401


def test_invalid_bearer_token_is_rejected(client) -> None:
    client.headers.update({"Authorization": "Bearer not.a.real.token"})
    assert client.get("/api/v1/auth/me").status_code == 401
    client.headers.pop("Authorization", None)


def test_login_does_not_reveal_whether_an_email_exists(client) -> None:
    account = register(client)

    unknown = client.post("/api/v1/auth/login", json={
        "email": "nobody@example.uz", "password": "juda-kuchli-parol-2026"})
    wrong_password = client.post("/api/v1/auth/login", json={
        "email": account["email"], "password": "totally-wrong-password"})

    assert unknown.status_code == wrong_password.status_code == 401
    assert unknown.json()["detail"] == wrong_password.json()["detail"]


def test_duplicate_registration_is_rejected(client) -> None:
    account = register(client)
    response = client.post("/api/v1/auth/register", json={
        "email": account["email"], "password": "juda-kuchli-parol-2026",
        "company_name": "Another Company"})
    assert response.status_code == 409


def test_weak_password_is_rejected(client) -> None:
    response = client.post("/api/v1/auth/register", json={
        "email": f"weak-{uuid.uuid4().hex[:6]}@example.uz",
        "password": "short", "company_name": "X Company"})
    assert response.status_code == 422


def test_refresh_issues_a_new_access_token(client) -> None:
    account = register(client)
    response = client.post("/api/v1/auth/refresh",
                           json={"refresh_token": account["tokens"]["refresh_token"]})
    assert response.status_code == 200
    assert response.json()["access_token"]


# --- tenant isolation ---------------------------------------------------------

def test_one_company_cannot_read_another_companys_documents(client) -> None:
    first = register(client)
    client.headers.update({"Authorization": f"Bearer {first['tokens']['access_token']}"})
    pdf = render_pdf(random_invoice(seed=77), seed=77)
    uploaded = client.post("/api/v1/documents/upload",
                           files=[("files", ("a.pdf", pdf, "application/pdf"))]).json()
    document_id = uploaded["accepted"][0]["id"]

    second = register(client)
    client.headers.update({"Authorization": f"Bearer {second['tokens']['access_token']}"})

    # 404, not 403: the existence of another tenant's id is itself information.
    assert client.get(f"/api/v1/documents/{document_id}").status_code == 404
    assert client.get(f"/api/v1/documents/{document_id}/file").status_code == 404
    assert client.get(f"/api/v1/documents/{document_id}/text").status_code == 404
    assert client.post(f"/api/v1/documents/{document_id}/review",
                       json={"fields": {}, "accept": True}).status_code == 404
    assert client.delete(f"/api/v1/documents/{document_id}").status_code == 404
    assert client.post("/api/v1/exports/commerceml",
                       json={"document_ids": [document_id]}).status_code == 404

    listing = client.get("/api/v1/documents").json()
    assert all(item["id"] != document_id for item in listing["items"])


def test_operator_cannot_change_company_settings(client) -> None:
    admin = register(client)
    client.headers.update({"Authorization": f"Bearer {admin['tokens']['access_token']}"})

    operator_email = f"operator-{uuid.uuid4().hex[:6]}@example.uz"
    invited = client.post("/api/v1/auth/users", json={
        "email": operator_email, "password": "juda-kuchli-parol-2026", "role": "operator"})
    assert invited.status_code == 201

    login = client.post("/api/v1/auth/login", json={
        "email": operator_email, "password": "juda-kuchli-parol-2026"}).json()
    client.headers.update({"Authorization": f"Bearer {login['access_token']}"})

    assert client.patch("/api/v1/auth/company", json={"name": "Hijacked"}).status_code == 403
    assert client.post("/api/v1/auth/users", json={
        "email": "x@example.uz", "password": "juda-kuchli-parol-2026"}).status_code == 403
    # An operator can still do their actual job.
    assert client.get("/api/v1/documents").status_code == 200


def test_storage_keys_cannot_escape_the_storage_root(tmp_path) -> None:
    """A crafted storage key must not read /etc/passwd."""
    from app.services.storage import LocalStorage

    storage = LocalStorage(root=tmp_path)
    for key in ("../../etc/passwd", "a/../../../../etc/shadow"):
        with pytest.raises(ValueError):
            storage.load(key)
        with pytest.raises(ValueError):
            storage.save(key, b"data")


def test_storage_keys_are_content_addressed_per_company() -> None:
    """Two tenants uploading the same file must not share a storage path."""
    from app.services.storage import build_storage_key, compute_sha256

    data = b"identical invoice bytes"
    digest = compute_sha256(data)
    first = build_storage_key(1, digest, "faktura.pdf")
    second = build_storage_key(2, digest, "faktura.pdf")

    assert first != second
    assert first.startswith("company-1/")
    assert second.startswith("company-2/")
