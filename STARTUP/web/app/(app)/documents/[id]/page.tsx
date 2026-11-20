"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { StatusBadge } from "@/components/StatusBadge";
import { api, type DocumentDetail, type ExtractedField } from "@/lib/api";
import { useApp } from "@/lib/context";
import { CONFIDENCE_STYLES, confidenceLevel, formatDuration } from "@/lib/format";
import type { TranslationKey } from "@/lib/i18n";

/** Field order follows the reading order of a printed hisob-faktura. */
const FIELD_ORDER: TranslationKey[] = [
  "invoice_number",
  "invoice_date",
  "vendor_name",
  "vendor_tin",
  "buyer_name",
  "buyer_tin",
  "contract_number",
  "subtotal",
  "vat_amount",
  "total_amount",
  "currency",
];

export default function ReviewPage() {
  const params = useParams<{ id: string }>();
  const documentId = Number(params.id);
  const { translate } = useApp();

  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [ocrText, setOcrText] = useState<string | null>(null);
  const [showOcr, setShowOcr] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setDetail(await api.document(documentId));
      setError(null);
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : String(exception));
    }
  }, [documentId]);

  useEffect(() => { void load(); }, [load]);

  // Keep polling until the pipeline finishes; processing is seconds, not minutes.
  useEffect(() => {
    if (!detail || !["pending", "processing"].includes(detail.status)) return;
    const timer = setInterval(() => { void load(); }, 2000);
    return () => clearInterval(timer);
  }, [detail, load]);

  useEffect(() => {
    let revoked: string | null = null;
    api.documentFileUrl(documentId)
      .then((url) => { revoked = url; setFileUrl(url); })
      .catch(() => setFileUrl(null));
    return () => { if (revoked) URL.revokeObjectURL(revoked); };
  }, [documentId]);

  const extraction = detail?.extraction ?? null;

  const valueOf = useCallback((name: string): string => {
    if (name in edits) return edits[name];
    const field = extraction?.fields?.[name];
    return field?.value === null || field?.value === undefined ? "" : String(field.value);
  }, [edits, extraction]);

  const fieldsWithProblems = useMemo(() => {
    const flagged = new Set<string>();
    for (const issue of extraction?.validation?.errors ?? []) issue.fields.forEach((f) => flagged.add(f));
    for (const issue of extraction?.validation?.warnings ?? []) issue.fields.forEach((f) => flagged.add(f));
    return flagged;
  }, [extraction]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await api.reviewDocument(documentId, { fields: edits, accept: true });
      setEdits({});
      // Refresh before confirming on screen, so the status badge and the
      // "saved" message never disagree with each other.
      await load();
      setMessage(translate("saved"));
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : String(exception));
    } finally {
      setSaving(false);
    }
  }

  async function exportOne() {
    setExporting(true);
    setError(null);
    try {
      await api.downloadExport([documentId]);
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : String(exception));
    } finally {
      setExporting(false);
    }
  }

  async function toggleOcr() {
    if (!showOcr && ocrText === null) {
      try {
        setOcrText((await api.documentText(documentId)).text);
      } catch {
        setOcrText("");
      }
    }
    setShowOcr((current) => !current);
  }

  if (error && !detail) {
    return <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>;
  }
  if (!detail) return <p className="text-sm text-slate-500">{translate("loading")}</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link href="/documents" className="text-sm text-slate-600 hover:underline">
            ← {translate("back")}
          </Link>
          <h1 className="text-lg font-semibold text-slate-900">{detail.original_filename}</h1>
          <StatusBadge status={detail.status} />
        </div>

        <div className="flex items-center gap-2">
          <button type="button" onClick={toggleOcr} className="btn-secondary">
            {showOcr ? translate("hideOcrText") : translate("showOcrText")}
          </button>
          <button
            type="button"
            onClick={async () => { await api.reprocessDocument(documentId); await load(); }}
            className="btn-secondary"
          >
            {translate("reprocess")}
          </button>
          <button type="button" onClick={exportOne} disabled={exporting || !extraction}
                  className="btn-secondary">
            {exporting ? translate("loading") : translate("exportTo1C")}
          </button>
          <button type="button" onClick={save} disabled={saving || !extraction} className="btn-success">
            {saving ? translate("saving") : translate("saveAndConfirm")}
          </button>
        </div>
      </div>

      {message && (
        <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{message}</p>
      )}
      {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {["pending", "processing"].includes(detail.status) && (
        <p className="rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-800">
          {translate("statusProcessing")}…
        </p>
      )}
      {detail.status === "failed" && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {detail.error_message}
        </p>
      )}

      {/* Problems found by validation, stated in plain language. */}
      {extraction && (extraction.validation.errors?.length || extraction.validation.warnings?.length) ? (
        <section className="card border-amber-200 bg-amber-50 p-4">
          <h2 className="mb-2 text-sm font-medium text-amber-900">{translate("problemsFound")}</h2>
          <ul className="space-y-1 text-sm">
            {extraction.validation.errors?.map((issue, index) => (
              <li key={`e-${index}`} className="text-red-800">• {issue.message}</li>
            ))}
            {extraction.validation.warnings?.map((issue, index) => (
              <li key={`w-${index}`} className="text-amber-800">• {issue.message}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {/* Anything the counterparty registry rewrote is disclosed, never silent. */}
      {extraction?.validation?.registry_repairs?.length ? (
        <section className="card border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
          <p className="font-medium">{translate("weCorrected")}</p>
          <ul className="mt-1 space-y-0.5">
            {extraction.validation.registry_repairs.map((repair, index) => (
              <li key={index}>
                {repair.from ? `${repair.from} → ` : ""}{repair.to ?? "?"}{" "}
                <span className="text-xs text-blue-700">({repair.reason})</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Original scan — the accountant compares against this, not against
            their memory of the paper. */}
        <section className="card overflow-hidden">
          <header className="flex items-center justify-between border-b border-slate-200 px-4 py-2">
            <h2 className="text-sm font-medium text-slate-700">{translate("originalDocument")}</h2>
            <span className="text-xs text-slate-500">
              {detail.ocr_provider} · {formatDuration(detail.processing_ms)}
            </span>
          </header>
          {fileUrl ? (
            detail.mime_type === "application/pdf" ? (
              // PDF open parameters: fit the page width and hide the thumbnail
              // sidebar, so the invoice fills the pane instead of opening with
              // navigation panes over the values being checked. Rendering is
              // the browser's native viewer; the link below is the fallback for
              // browsers without one.
              <object
                data={`${fileUrl}#view=FitH&navpanes=0`}
                type="application/pdf"
                className="h-[640px] w-full"
              >
                <p className="p-4 text-sm text-slate-600">
                  <a href={fileUrl} className="underline" download>{detail.original_filename}</a>
                </p>
              </object>
            ) : (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={fileUrl} alt={detail.original_filename} className="max-h-[640px] w-full object-contain" />
            )
          ) : (
            <p className="p-4 text-sm text-slate-500">{translate("loading")}</p>
          )}
        </section>

        <section className="space-y-4">
          <div className="card p-4">
            <header className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-medium text-slate-700">{translate("extractedData")}</h2>
              {extraction && (
                <span className="text-xs text-slate-500">
                  {Math.round(extraction.overall_confidence * 100)}% · v{extraction.version} · {extraction.strategy}
                </span>
              )}
            </header>

            {!extraction ? (
              <p className="text-sm text-slate-500">{translate("loading")}</p>
            ) : (
              <div className="space-y-3">
                {FIELD_ORDER.map((name) => (
                  <FieldRow
                    key={name}
                    name={name}
                    label={translate(name)}
                    field={extraction.fields[name]}
                    value={valueOf(name)}
                    flagged={fieldsWithProblems.has(name)}
                    checkLabel={translate("checkThis")}
                    onChange={(next) => setEdits((current) => ({ ...current, [name]: next }))}
                  />
                ))}
              </div>
            )}
          </div>

          {extraction && extraction.line_items.length > 0 && (
            <div className="card overflow-x-auto p-4">
              <h2 className="mb-3 text-sm font-medium text-slate-700">{translate("lineItems")}</h2>
              <table className="w-full text-sm">
                <thead className="border-b border-slate-200 text-left text-xs uppercase text-slate-500">
                  <tr>
                    <th className="py-1 pr-2">{translate("colIndex")}</th>
                    <th className="py-1 pr-2">{translate("colDescription")}</th>
                    <th className="py-1 pr-2">{translate("colUnit")}</th>
                    <th className="py-1 pr-2 text-right">{translate("colQuantity")}</th>
                    <th className="py-1 pr-2 text-right">{translate("colUnitPrice")}</th>
                    <th className="py-1 text-right">{translate("colAmount")}</th>
                  </tr>
                </thead>
                <tbody>
                  {extraction.line_items.map((item) => (
                    <tr key={item.index} className="border-b border-slate-100 last:border-0">
                      <td className="py-1.5 pr-2 text-slate-500">{item.index}</td>
                      <td className="py-1.5 pr-2 text-slate-800">{item.description}</td>
                      <td className="py-1.5 pr-2 text-slate-600">{item.unit ?? "—"}</td>
                      <td className="py-1.5 pr-2 text-right text-slate-800">{item.quantity ?? "—"}</td>
                      <td className="py-1.5 pr-2 text-right text-slate-800">{item.unit_price ?? "—"}</td>
                      <td className="py-1.5 text-right font-medium text-slate-900">{item.amount ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {showOcr && (
            <div className="card p-4">
              <h2 className="mb-2 text-sm font-medium text-slate-700">OCR</h2>
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs text-slate-700">
                {ocrText || translate("noDataYet")}
              </pre>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function FieldRow({
  name, label, field, value, flagged, checkLabel, onChange,
}: {
  name: string;
  label: string;
  field: ExtractedField | undefined;
  value: string;
  flagged: boolean;
  checkLabel: string;
  onChange: (value: string) => void;
}) {
  const confidence = field?.confidence ?? 0;
  const level = confidenceLevel(confidence);
  const styles = CONFIDENCE_STYLES[level];

  return (
    <div className={`rounded-md bg-white pl-3 ${styles.border}`}>
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-slate-600" htmlFor={`field-${name}`}>
          {label}
        </label>
        <span className="flex items-center gap-2">
          {flagged && <span className={`badge ${styles.badge}`}>{checkLabel}</span>}
          <span
            className={`text-xs ${styles.text}`}
            // The evidence trail: which label on the page produced this value.
            title={field?.source ?? ""}
          >
            {Math.round(confidence * 100)}%
          </span>
        </span>
      </div>
      <input
        id={`field-${name}`}
        className="input mt-1"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}
