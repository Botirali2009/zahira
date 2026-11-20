"""End-to-end API tests.

The first test walks the exact path a chief accountant takes: register, upload a
scan, review what came back, correct a field, confirm, export to 1C. If that
passes, the product works.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import Decimal

from app.testing.corpus import random_invoice, render_pdf


def upload_invoice(client, seed: int = 42, style: str = "uz_latin") -> dict:
    spec = random_invoice(seed=seed, style=style, layout="classic")
    pdf = render_pdf(spec, seed=seed)
    response = client.post(
        "/api/v1/documents/upload",
        files=[("files", (f"faktura-{seed}.pdf", pdf, "application/pdf"))],
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["rejected"] == []
    return {"document": body["accepted"][0], "spec": spec}


def test_full_upload_review_export_flow(registered_client) -> None:
    client = registered_client
    uploaded = upload_invoice(client)
    document_id = uploaded["document"]["id"]
    spec = uploaded["spec"]

    # --- processing completed synchronously via the inline queue -------------
    detail = client.get(f"/api/v1/documents/{document_id}").json()
    assert detail["status"] in ("ready", "needs_review"), detail
    extraction = detail["extraction"]
    assert extraction is not None

    fields = extraction["fields"]
    assert fields["invoice_number"]["value"] == spec.invoice_number
    assert fields["vendor_tin"]["value"] == spec.vendor_tin
    assert Decimal(str(fields["total_amount"]["value"])) == spec.total_amount

    # Every field carries the evidence it came from.
    assert fields["vendor_tin"]["source"].startswith("label:")
    assert 0.0 <= extraction["overall_confidence"] <= 1.0

    # --- the accountant corrects one field and confirms ----------------------
    review = client.post(
        f"/api/v1/documents/{document_id}/review",
        json={"fields": {"vendor_name": "Corrected Supplier LLC"}, "accept": True},
    )
    assert review.status_code == 200, review.text
    reviewed = review.json()
    assert reviewed["version"] == extraction["version"] + 1
    assert reviewed["fields"]["vendor_name"]["value"] == "Corrected Supplier LLC"
    # A human-entered value is ground truth.
    assert reviewed["fields"]["vendor_name"]["confidence"] == 1.0
    assert reviewed["fields"]["vendor_name"]["source"] == "human"

    # The machine's original version is preserved, not overwritten.
    versions = client.get(f"/api/v1/documents/{document_id}/extractions").json()
    assert len(versions) >= 2
    assert versions[0]["fields"]["vendor_name"]["value"] == spec.vendor_name

    assert client.get(f"/api/v1/documents/{document_id}").json()["status"] == "confirmed"

    # --- export to 1C --------------------------------------------------------
    preview = client.post("/api/v1/exports/preview", json={"document_ids": [document_id]})
    assert preview.status_code == 200, preview.text
    assert preview.json()["problems"] == []

    export = client.post("/api/v1/exports/commerceml", json={"document_ids": [document_id]})
    assert export.status_code == 200, export.text
    assert "attachment" in export.headers["content-disposition"]

    root = ET.fromstring(export.content)
    assert root.tag == "КоммерческаяИнформация"
    assert root.findtext("Документ/Номер") == spec.invoice_number
    assert "Corrected Supplier LLC" in export.text

    history = client.get("/api/v1/exports/history").json()
    assert history[0]["document_count"] == 1
    assert history[0]["checksum"]


def test_batch_upload_accepts_valid_and_rejects_invalid(registered_client) -> None:
    """One bad file must not reject the whole scanner batch."""
    good = render_pdf(random_invoice(seed=7), seed=7)
    response = registered_client.post("/api/v1/documents/upload", files=[
        ("files", ("good.pdf", good, "application/pdf")),
        ("files", ("virus.exe", b"MZ\x00binary", "application/x-msdownload")),
        ("files", ("empty.pdf", b"", "application/pdf")),
    ])

    assert response.status_code == 202
    body = response.json()
    assert len(body["accepted"]) == 1
    assert len(body["rejected"]) == 2
    reasons = " ".join(item["reason"] for item in body["rejected"])
    assert "Unsupported file type" in reasons
    assert "empty" in reasons.lower()


def test_oversized_upload_is_rejected(registered_client) -> None:
    from app.core.config import settings

    oversized = b"%PDF-1.4\n" + b"0" * (settings.max_upload_bytes + 1)
    response = registered_client.post(
        "/api/v1/documents/upload",
        files=[("files", ("huge.pdf", oversized, "application/pdf"))],
    )

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] == []
    assert "larger than" in body["rejected"][0]["reason"]


def test_duplicate_upload_reuses_cached_ocr(registered_client) -> None:
    """The same scan uploaded twice must not be paid for twice."""
    pdf = render_pdf(random_invoice(seed=9), seed=9)
    files = [("files", ("dup.pdf", pdf, "application/pdf"))]

    first = registered_client.post("/api/v1/documents/upload", files=files).json()
    second = registered_client.post("/api/v1/documents/upload", files=files).json()

    first_text = registered_client.get(
        f"/api/v1/documents/{first['accepted'][0]['id']}/text"
    ).json()
    second_text = registered_client.get(
        f"/api/v1/documents/{second['accepted'][0]['id']}/text"
    ).json()

    assert first_text["from_cache"] is False
    assert second_text["from_cache"] is True
    assert first_text["text"] == second_text["text"]


def test_document_listing_filters_and_paginates(registered_client) -> None:
    for seed in (21, 22, 23):
        upload_invoice(registered_client, seed=seed)

    listing = registered_client.get("/api/v1/documents", params={"limit": 2}).json()
    assert len(listing["items"]) == 2
    assert listing["total"] >= 3

    filtered = registered_client.get("/api/v1/documents", params={"status": "confirmed"}).json()
    assert all(item["status"] == "confirmed" for item in filtered["items"])

    bad = registered_client.get("/api/v1/documents", params={"status": "nonsense"})
    assert bad.status_code == 422


def test_ocr_text_endpoint_reports_script_mix(registered_client) -> None:
    """Support needs the raw OCR output to explain a bad extraction."""
    uploaded = upload_invoice(registered_client, seed=31, style="mixed")
    payload = registered_client.get(
        f"/api/v1/documents/{uploaded['document']['id']}/text"
    ).json()

    assert payload["provider"] == "pdf_text"
    assert payload["text"]
    assert payload["blocks"]
    assert "dominant" in payload["script_summary"]


def test_original_file_is_served_for_side_by_side_review(registered_client) -> None:
    uploaded = upload_invoice(registered_client, seed=33)
    response = registered_client.get(f"/api/v1/documents/{uploaded['document']['id']}/file")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")


def test_export_refuses_unprocessed_document(registered_client, db_session) -> None:
    from app.db.models import Document

    document = Document(
        company_id=1, original_filename="pending.pdf", mime_type="application/pdf",
        size_bytes=10, sha256="f" * 64, storage_key="pending",
    )
    db_session.add(document)
    db_session.commit()

    response = registered_client.post(
        "/api/v1/exports/commerceml", json={"document_ids": [document.id]}
    )
    assert response.status_code in (404, 409)


def test_dashboard_reports_real_activity(registered_client) -> None:
    upload_invoice(registered_client, seed=41)
    stats = registered_client.get("/api/v1/dashboard").json()

    assert stats["documents_this_month"] >= 1
    assert stats["minutes_saved_this_month"] >= 15
    assert 0.0 <= stats["average_confidence"] <= 1.0
    assert stats["quota"] > 0


def test_reprocess_creates_a_new_extraction_version(registered_client) -> None:
    uploaded = upload_invoice(registered_client, seed=51)
    document_id = uploaded["document"]["id"]

    before = len(registered_client.get(f"/api/v1/documents/{document_id}/extractions").json())
    assert registered_client.post(
        f"/api/v1/documents/{document_id}/reprocess"
    ).status_code == 202
    after = len(registered_client.get(f"/api/v1/documents/{document_id}/extractions").json())

    assert after == before + 1


def test_health_and_readiness(client) -> None:
    assert client.get("/health").json()["status"] == "ok"

    ready = client.get("/ready").json()
    assert ready["checks"]["database"] is True
    assert "pdf_text" in ready["checks"]["ocr_providers"]
