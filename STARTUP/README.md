# HujjatAI

**Uzbek-language document AI for 1C accounting.** Extracts structured data from
`hisob-faktura` / `счёт-фактура` invoices written in any mix of Uzbek Latin,
Uzbek Cyrillic and Russian, and exports it as CommerceML 2.08 for import into
1C:Buxgalteriya 8.3.

This repository contains both the business plan and a working implementation of
the Phase 2 MVP described in it.

```
01-research-findings.md   Uzbekistan market research
02-scored-ideas.md        10 scored startup ideas and the winner
03-deep-dive.md           Customer, architecture, competition, risks, MVP spec
04-execution-plan.md      Phase-by-phase plan with budgets and decision gates
05-financial-model.md     Unit economics and projections
06-executive-summary.md   One-page investor summary

backend/                  FastAPI service: OCR, extraction, validation, 1C export
web/                      Next.js interface in Uzbek (Latin + Cyrillic) and Russian
docs/                     Architecture, data residency, pilot runbook, LOI template
docker-compose.yml        Full stack: api, worker, postgres, redis, web
```

---

## Quick start

```bash
docker compose up --build
# Web  http://localhost:3000
# API  http://localhost:8000/docs
```

Or run the backend alone with no external services at all — SQLite, local file
storage, in-process queue, rule-based extraction:

```bash
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload
```

```bash
cd web
npm install && npm run dev
```

No API keys are required to run or evaluate the system. Born-digital PDFs (which
Uzbekistan's e-invoicing mandate is producing more of every year) are read
through their text layer, and the rule-based extractor is fully offline. Cloud
OCR and the LLM are optional accelerators, configured by environment variable.

---

## What the pipeline does

```
upload ─► preprocess ─► OCR ─► script detection ─► extraction ─► counterparty
                                                                   registry
                                                                      │
   1C CommerceML ◄── human review ◄── needs-review queue ◄── validation
```

1. **Preprocess** — deskew, denoise, contrast-normalise scans (`services/preprocess.py`).
2. **OCR** — a provider chain ordered by cost: the PDF text layer (free), Google
   Cloud Vision (~$1.50/1,000 pages), then local Tesseract. First one to return
   text wins (`services/ocr/`).
3. **Script detection** — every text block is classified as Uzbek Latin, Uzbek
   Cyrillic or Russian. Uzbek Cyrillic is distinguished from Russian by the four
   letters Russian does not have: `ў қ ғ ҳ` (`services/script_detect.py`).
4. **Extraction** — a deterministic label-matching extractor handles the common
   layouts for free; the LLM is an escalation path for documents it cannot
   resolve confidently, not the default (`services/extract/`).
5. **Counterparty registry** — a supplier's confirmed name repairs OCR damage on
   later invoices from the same STIR, including across scripts
   (`services/templates.py`).
6. **Validation** — cross-field arithmetic, STIR format, VAT rate, date
   plausibility and intra-word script corruption. Failing checks push confidence
   below the review threshold (`services/validate.py`).
7. **Review** — the accountant confirms or corrects. Corrections are stored as a
   new extraction version, never overwriting what the machine produced.
8. **Export** — CommerceML 2.08, self-validated before download
   (`services/export_1c.py`).

---

## Measured behaviour

Everything below is reproducible from a clean checkout.

```bash
cd backend
python scripts/eval_extraction.py --count 300                        # parser only
python scripts/eval_extraction.py --count 60 --via-pdf               # through the real OCR chain
python scripts/eval_extraction.py --count 200 --noise 0.02 --registry # simulated OCR damage
```

| Condition | Field accuracy | Silent error rate |
|---|---|---|
| Clean synthetic text, 300 documents | 100% | 0% |
| Rendered to PDF, through the OCR chain, 60 documents | 100% | 0% |
| 2% simulated OCR character error rate | 75.9% | 14.0% |
| … plus validation | 75.9% | 8.6% |
| … plus counterparty registry | 82.1% | **3.7%** |

**Read these numbers carefully.** The corpus is synthetic and was written by the
same authors as the parser, so the clean-text figure is a regression baseline —
it says the parser handles the layouts, scripts and number formats it claims to,
and nothing more. It is not evidence about any real customer's documents. Gate
G3 in the execution plan is measured on real beta documents, and only that
counts.

The number that matters commercially is the **silent error rate**: values that
are wrong *and* confident, because those reach a tax filing without a human
looking. Accuracy under noise degrades steeply — a character OCR never emitted
cannot be recovered — so the engineering goal is not to hide errors but to
*catch* them. Validation and the registry cut silent errors by ~4x, at the cost
of flagging ~13% of correct fields for a second look.

---

## Design decisions worth knowing

**Rules before LLM.** At 50 customers this runs ~50,000 documents a month. Every
field the rules resolve costs nothing and, more importantly, is reproducible: a
chief accountant who gets two different answers for the same invoice stops
trusting the product. `HUJJAT_EXTRACTION_STRATEGY=auto` escalates to the LLM only
below the confidence threshold.

**Confidence means "check this".** The threshold is 0.85 in the backend, the
review queue and the UI colour coding — one number, so the colour on screen never
disagrees with the queue.

**The human is in the loop by design.** Chief accountants are risk-averse with
tax-critical data (deep-dive risk #6). Nothing reaches 1C without confirmation,
every field shows the evidence it came from, and every registry repair is
disclosed rather than applied silently.

**Corrections are the product's data moat.** Each one is stored as a labelled
example against the original machine output — the training set described in
deep-dive §6, accumulating from the first pilot customer.

**Stable 1C identifiers.** Counterparties and goods use UUID5 values derived from
business data, so re-importing a document updates one record in 1C instead of
creating a duplicate supplier. This is the detail that decides whether a 1C
integration is usable in practice.

**Document images stay local.** `storage_backend=local` by default; only OCR
*text* is sent to any cloud API. See [docs/data-residency.md](docs/data-residency.md).

---

## Tests

```bash
cd backend
pytest -q                       # 136 tests
ruff check app tests scripts
cd ../web && npm run typecheck && npm run build
```

The suite covers parsers, script detection, extraction across all
script/layout combinations, validation, the 1C export format, template learning,
the full upload→review→export API flow, and tenant isolation.

CI additionally runs the accuracy harness as a gate, so a regression in
extraction quality fails the build.

---

## Configuration

All settings are environment variables prefixed `HUJJAT_`. The defaults run
locally with no external services.

| Variable | Default | Notes |
|---|---|---|
| `HUJJAT_SECRET_KEY` | random per process | **Required in production** |
| `HUJJAT_DATABASE_URL` | SQLite file | PostgreSQL in production |
| `HUJJAT_STORAGE_BACKEND` | `local` | `s3` for object storage |
| `HUJJAT_OCR_PROVIDERS` | `pdf_text,google_vision,tesseract` | Ordered chain |
| `HUJJAT_GOOGLE_VISION_API_KEY` | — | Optional |
| `HUJJAT_LLM_API_KEY` | — | Optional; enables escalation |
| `HUJJAT_EXTRACTION_STRATEGY` | `auto` | `rules`, `llm`, `auto` |
| `HUJJAT_QUEUE_BACKEND` | `inline` | `celery` for production volume |
| `HUJJAT_VAT_RATE_PERCENT` | `12.0` | Uzbekistan standard rate |

`GET /ready` reports which capabilities are actually wired up, so a deployment
missing an API key is visible immediately rather than as unexplained low accuracy
days later.

---

## What is built and what is not

**Built and verified:** the entire Phase 2 MVP feature list from deep-dive §5 —
batch upload, multi-script OCR, invoice extraction, human review UI, 1C export,
correction feedback loop, authentication with company workspaces, usage
dashboard.

**Not built (deliberately out of MVP scope):** mobile app, contract and waybill
extraction, tax-form filing, multi-company accounting-firm mode, public API,
on-premise packaging. Rationale for each is in deep-dive §5.

**Cannot be done by software** — these need a founder in Tashkent, and no amount
of code substitutes for them:

- The 15 customer discovery interviews and gates G1/G2 (Phase 1.1, 1.5)
- IT Park residency and LLC registration (Phase 1.2, 1.3)
- Signing a 1C:Franchisee partner and testing the export against *their*
  customers' real 1C installations — the export is validated against the
  CommerceML 2.08 specification here, which is not the same as being tested in a
  live 1C:Buxgalteriya
- Collecting real invoices; every document in this repository is synthetic
- Hiring, pricing validation, and everything in Phases 3-5

See [docs/pilot-runbook.md](docs/pilot-runbook.md) for how to take this code into
the first paid pilot.
