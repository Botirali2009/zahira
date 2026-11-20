# Pilot runbook

How to get from this repository to a chief accountant processing real invoices.
Written for the founder, assuming Phase 1 gates G1 and G2 have been passed
(15 interviews done, 3+ LOIs signed).

---

## Before the first customer session

**1. Deploy somewhere in Uzbekistan.** A single VPS is enough for the first ten
customers. Vertical scaling covers you to roughly 35.

```bash
git clone <repo> && cd STARTUP
cp .env.example .env      # set HUJJAT_SECRET_KEY to a real random value
docker compose up -d --build
```

Verify before inviting anyone:

```bash
curl -s localhost:8000/ready | jq
```

`status` must be `ok` and at least one OCR provider `true`. If you are running
the in-country posture, confirm `google_vision: false` is what you intended
rather than an accident.

**2. Decide the OCR posture per customer.** See
[data-residency.md](data-residency.md). Ask directly in the demo: "Do your
documents have to stay on servers in Uzbekistan?" The answer sets
`HUJJAT_OCR_PROVIDERS`, and asking the question earns more trust than any
feature.

**3. Get 20 real invoices from the customer *before* the session.** Run them
through yourself:

```bash
# after creating their account
curl -X POST localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" -F "files=@invoice.pdf"
```

Check the extraction, and if a field is wrong, look at the OCR text
(`GET /documents/{id}/text`) to see whether the problem is recognition or
extraction. If it is extraction, the fix is usually one label added to
`backend/app/services/extract/lexicon.py` — a five-minute change that
permanently improves every customer. **Do this before the demo, not during it.**

---

## The 45-minute onboarding (Phase 3.4)

| Minutes | Step |
|---|---|
| 0-5 | Create their account. Set company name, STIR, and the 1C organisation name in Settings. |
| 5-10 | Upload the 20 invoices you already tested. They watch it work on *their* documents. |
| 10-25 | Walk one document through review together. Show the confidence colours and let them correct a field. |
| 25-35 | Export to 1C. **They** import it on their machine, on their screen. |
| 35-45 | Telegram support group, login handover, schedule the week-1 check-in. |

Two things decide whether this session converts:

- **The 1C import must work on their installation.** Test with your 1C partner
  on that customer's configuration before the visit. A failed import in front of
  the accountant is very hard to recover from.
- **Do not hide the corrections.** "The machine got 9 of 10 fields and flagged
  the one it was unsure about" is a better story than pretending it is perfect.
  It also sets the expectation that they review — which is the compliance model
  the whole product depends on.

---

## Weekly loop

Every Monday, per customer:

```
GET /api/v1/dashboard
```

- `correction_rate` — the honest accuracy number. Rising means a new document
  format has appeared.
- `needs_review` — if it is growing, they are uploading but not reviewing. Call
  them; this is the leading indicator of churn.
- `known_vendors` / `template_active` — templates going active is the product
  getting cheaper and more accurate on its own.

When a correction pattern repeats:

1. Pull the document's OCR text.
2. If a label is missing, add it to `lexicon.py`, add a test case, ship it.
3. `POST /documents/{id}/reprocess` to re-run affected documents.

Run the accuracy harness before every deploy. CI does this too, but a local run
takes seconds:

```bash
cd backend && python scripts/eval_extraction.py --count 200 --fail-under 0.98
```

---

## Failure playbook

| Symptom | First check | Usual cause |
|---|---|---|
| Document status `failed` | `error_message` on the document | Scanned PDF with no text layer and no OCR provider configured |
| All fields empty, status ready | `GET /documents/{id}/text` | OCR returned text but in an unexpected layout — send the file to engineering |
| Totals flagged every time | `validation.errors` | Vendor rounds VAT per line item; usually a real discrepancy worth telling the customer about |
| Vendor name wrong on one supplier | `validation.registry_repairs` | Registry conflict — the supplier renamed, or their STIR was misread |
| 1C import rejects the file | Export preview `problems` | Missing STIR or a document with no line items |
| Everything slow | Worker logs | OCR queue depth; scale workers |

Every log line carries `document_id`, so one document's full lifecycle greps out
of the log stream cleanly.

---

## Gate G3 (end of Week 12)

The plan requires **85%+ accuracy on beta customers' actual invoices** and 3+
active users. Measure it honestly:

- `correction_rate` from the dashboard is your real accuracy — the share of
  confirmed documents a human had to change.
- Do **not** substitute the synthetic harness number. It measures regression,
  not reality.
- If accuracy is below 80% after two weeks of tuning, the plan says extend by
  two weeks. Below 70%, the approach itself needs revisiting.

The number to watch even more closely is how often a *wrong* value came through
with high confidence. One silent error that reaches a tax filing costs more
trust than ten flagged ones cost time.
