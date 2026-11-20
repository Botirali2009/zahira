# Architecture

## Request paths

```
Browser (Next.js)
   │  JWT bearer
   ▼
FastAPI ──── upload ────► storage (local disk / S3)
   │                          │
   │                          ▼
   └──── enqueue ────► worker (inline or Celery)
                              │
                              ├─ preprocess (deskew, denoise)
                              ├─ OCR chain (pdf_text → vision → tesseract)
                              ├─ script detection per block
                              ├─ extraction (rules → LLM escalation)
                              ├─ counterparty registry repair
                              └─ validation → confidence adjustment
                                      │
                                      ▼
                              PostgreSQL (versioned extractions)
                                      │
                              human review → CommerceML 2.08 → 1C
```

## Why these components

**FastAPI + Python.** The ML ecosystem is Python, and the OCR/extraction work is
the product. A second language for the API would mean either a service hop on
every document or a rewrite when the models move in-process.

**PostgreSQL with JSONB.** Extraction output is a per-document field bag whose
shape changes as new document types are added. JSONB stores it without a
migration per field, while the columns that need indexing — vendor TIN, total,
status, confidence — stay relational for the dashboard and queue queries.

**Celery + Redis, with an inline fallback.** OCR is slow and bursty: an
accountant scans a day's invoices and drops in 40 files at once. The API must
stay responsive, so processing is asynchronous. Below roughly 10 customers, the
inline queue avoids operating two more services for no benefit —
`HUJJAT_QUEUE_BACKEND` switches between them with no code change.

**Provider chains everywhere.** OCR and extraction are both pluggable behind an
interface with an `is_available()` probe. This is what makes the Month 10-12
transition to self-hosted PaddleOCR and a fine-tuned Qwen model a configuration
change rather than a rewrite, and it is why the system runs with zero API keys
today.

## Data model

| Table | Purpose |
|---|---|
| `companies` | Tenant boundary. Holds the per-customer 1C mapping. |
| `users` | Admin / operator roles inside one company. |
| `documents` | Uploaded file, content hash, status, processing timings. |
| `ocr_results` | Raw text, blocks with bounding boxes, script summary, provider. |
| `extractions` | **Versioned.** v1 is the machine's answer; later versions are what humans accepted. |
| `corrections` | One row per changed field. The labelled training data. |
| `vendor_templates` | Confirmed counterparties, name aliases, learned label hints. |
| `export_logs` | What was handed to 1C, when, by whom, with a checksum. |

Two decisions deserve explanation.

**Extractions are versioned, not mutated.** Overwriting the machine's answer with
the human's would destroy the only signal that says how well extraction is
actually working. Keeping both makes the correction rate on the dashboard a real
production accuracy measurement rather than an estimate.

**Money is `Numeric(18, 2)`.** A two-billion-soʻm invoice is ordinary in this
market. Floats are not an option anywhere near tax data.

## Multi-tenancy

Every query is scoped by `company_id`, taken from the authenticated user rather
than from any request parameter. Documents belonging to another company return
404, not 403 — the existence of a document id is itself information about another
customer. Storage keys are partitioned per company, so two tenants uploading a
byte-identical invoice never share a path. `tests/test_security.py` asserts all
of this.

## Cost control

The chain order is a cost decision, not just a fallback list:

| Stage | Cost per document | When it runs |
|---|---|---|
| PDF text layer | $0 | Born-digital e-invoices — a growing share |
| Google Vision | ~$0.0015 | Scans and photos |
| Tesseract | $0 (CPU) | On-premise deployments, Vision outage |
| Rule extractor | $0 | Always |
| LLM | ~$0.0002 | Only below the confidence threshold |

Two further mechanisms cut the bill: OCR results are cached by content hash, so
the same scan uploaded twice is never paid for twice; and once a vendor's
template is confirmed, their invoices resolve on rules alone.

At the plan's Month 9 volume (50 customers, ~50,000 pages/month) this lands
around $75/month in OCR with LLM costs in the single dollars — consistent with
the financial model's margin assumptions.

## Scaling path

| Customers | Change |
|---|---|
| 1-10 | Single API container, inline queue, SQLite or a small Postgres |
| 10-35 | Celery workers, managed Postgres, Redis |
| 35-100 | Scale workers horizontally; read replica for dashboard queries |
| 100+ | Self-hosted PaddleOCR + fine-tuned extraction model on one GPU |

The scaling limit is OCR CPU, not the database. Workers are stateless and scale
with `docker compose up --scale worker=N`.

## Known gaps

- **Line-item review is read-only in the UI.** Header fields are editable; the
  items table is displayed but not yet inline-editable. The API accepts corrected
  line items, so this is a UI gap, not a backend one.
- **The LLM extractor has never run against a live API** in this repository — no
  key was available. Its request shape, JSON parsing, salvage path and cost
  accounting are unit-tested against a stubbed client, but the first real call
  should be watched closely.
- **PDF preview uses the browser's native viewer.** Adequate for review, but
  field-level bounding-box highlighting (which the OCR layer already records)
  would be a genuine improvement to the review workflow.
- **No rate limiting** on the API. Needed before the product is exposed beyond
  pilot customers.
