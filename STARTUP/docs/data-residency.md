# Data residency and personal data

> This is an engineering description of how the system handles data, written to
> support a conversation with a lawyer. It is not legal advice, and the legal
> opinion called for in deep-dive risk #4 still has to be obtained from an
> Uzbek IT law firm before the first paying customer.

## The obligation

The Law on Personal Data (2019, amended 2021) requires a legal basis for
processing personal data and regulates cross-border transfer. Uzbekistan has no
blanket localisation mandate comparable to Russia's Federal Law 242-FZ, but the
State Inspectorate for Personal Data Protection can restrict transfers abroad.

Business invoices are not obviously "personal data" — but they carry individual
names (director, chief accountant), signatures, sometimes a PINFL, and always
counterparty STIRs. A chief accountant will ask where the images go in the first
demo, and "a server in Frankfurt" is a bad answer to give in a sales meeting even
where it is defensible legally.

## What this implementation does

The system separates **images** from **text**, because they carry different risk:

| Data | Where it goes | Why |
|---|---|---|
| Original scan (image/PDF) | Local disk or a local object store, `storage_backend=local` by default | Contains signatures, stamps, names, sometimes passport data |
| OCR text | May be sent to a cloud LLM when escalation is enabled | Much narrower content, and only for documents the rules could not resolve |
| Extracted fields | The application database | The customer's own accounting data |

Concretely:

- `HUJJAT_STORAGE_BACKEND=local` (the default) writes document images to a
  volume the operator controls. Nothing uploads them anywhere.
- The **LLM extractor sends OCR text only** — never the page image. This is
  enforced by construction: `services/extract/llm.py` receives a string.
- `HUJJAT_EXTRACTION_STRATEGY=rules` disables all outbound model calls, and the
  system remains fully functional on born-digital PDFs and Tesseract OCR.
- Google Cloud Vision, when configured, **does** receive the page image. An
  installation that must keep images in-country should not enable it; set
  `HUJJAT_OCR_PROVIDERS=pdf_text,tesseract` instead. The backend Docker image
  ships the Uzbek Latin, Uzbek Cyrillic and Russian Tesseract packs precisely so
  that this configuration is a real option and not a theoretical one.

## Deployment postures

**Posture A — local images, cloud assist (default).** Images on an Uzbek server;
Vision and the LLM optional. Highest accuracy, some text crosses the border.

**Posture B — fully in-country.** `pdf_text,tesseract` + `rules`. No outbound
calls at all. Lower accuracy on poor scans; the correct choice for a customer
who cannot accept any transfer, and the basis of an on-premise offering.

**Posture C — cloud everything.** Only appropriate for customers who have
explicitly agreed to it.

The posture is a per-deployment configuration change, not a code fork.

## Retention

- Documents and extractions: for the life of the agreement plus five years,
  matching Uzbek tax record retention.
- `export_logs` keeps a checksum of every file handed to 1C, so a disputed
  filing can be traced back to the exact export.
- Deleting a document removes the stored image and its extractions. The export
  audit trail survives deliberately — it is the record of what was filed.

## Before the first paying customer

1. Obtain a written legal opinion on whether these invoices constitute personal
   data under the 2019 law, and on cross-border OCR text transfer.
2. Register as a data processor with the State Inspectorate (filing, no fee).
3. Have the DPA and service agreement drafted by the IT lawyer (Phase 3.6,
   budgeted at $300).
4. Decide the default posture per customer and record it in `onec_config`
   alongside the 1C mapping.
5. Add a data-deletion endpoint for contract termination. Not implemented yet.
