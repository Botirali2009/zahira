"""Test fixtures.

Every test runs against a throwaway SQLite file and a throwaway storage
directory, so the suite never touches a developer's local data and tests can run
in any order.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session", autouse=True)
def _configure_environment(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    root = tmp_path_factory.mktemp("hujjatai")
    os.environ.update({
        "HUJJAT_ENVIRONMENT": "test",
        "HUJJAT_DATABASE_URL": f"sqlite:///{root / 'test.db'}",
        "HUJJAT_STORAGE_LOCAL_ROOT": str(root / "documents"),
        "HUJJAT_SECRET_KEY": "test-secret-key-not-used-anywhere-else",
        "HUJJAT_QUEUE_BACKEND": "inline",
        # Rules only: the suite must not depend on network access or API keys.
        "HUJJAT_EXTRACTION_STRATEGY": "rules",
        "HUJJAT_OCR_PROVIDERS": "pdf_text",
        "HUJJAT_LOG_LEVEL": "WARNING",
    })
    yield


@pytest.fixture()
def db_session(_configure_environment):
    from app.db.base import init_db
    from app.db.session import SessionLocal

    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(_configure_environment):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def registered_client(client):
    """A client authenticated as the admin of a fresh company."""
    import uuid

    email = f"hisobchi-{uuid.uuid4().hex[:8]}@example.uz"
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "juda-kuchli-parol-2026",
        "full_name": "Bosh hisobchi",
        "company_name": '"AGROMASH SERVIS" MChJ',
        "company_tin": "205000137",
    })
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.email = email  # type: ignore[attr-defined]
    return client


@pytest.fixture()
def sample_invoice_pdf() -> bytes:
    from app.testing.corpus import random_invoice, render_pdf

    return render_pdf(random_invoice(seed=42, style="uz_latin", layout="classic"), seed=42)


@pytest.fixture()
def sample_invoice_spec():
    from app.testing.corpus import random_invoice

    return random_invoice(seed=42, style="uz_latin", layout="classic")
