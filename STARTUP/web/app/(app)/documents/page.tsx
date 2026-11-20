"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { StatusBadge } from "@/components/StatusBadge";
import { api, type DocumentSummary } from "@/lib/api";
import { useApp } from "@/lib/context";
import { formatDateTime } from "@/lib/format";
import { translateStatus } from "@/lib/i18n";

const STATUSES = ["pending", "processing", "ready", "needs_review", "confirmed", "failed"];

export default function DocumentsPage() {
  const { translate, locale } = useApp();
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.documents({ status: statusFilter || undefined, limit: 100 });
      setDocuments(data.items);
      setTotal(data.total);
      setError(null);
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : String(exception));
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { void load(); }, [load]);

  // Documents still in the queue resolve in seconds; poll while any are active
  // so the accountant does not have to refresh manually.
  useEffect(() => {
    const active = documents.some((d) => d.status === "pending" || d.status === "processing");
    if (!active) return;
    const timer = setInterval(() => { void load(); }, 3000);
    return () => clearInterval(timer);
  }, [documents, load]);

  function toggle(id: number) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function exportSelected() {
    setExporting(true);
    setError(null);
    try {
      await api.downloadExport(Array.from(selected));
      setSelected(new Set());
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : String(exception));
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-slate-900">
          {translate("documentsTitle")} <span className="text-sm font-normal text-slate-500">({total})</span>
        </h1>

        <div className="flex items-center gap-2">
          <select
            className="input w-auto"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="">{translate("allStatuses")}</option>
            {STATUSES.map((status) => (
              <option key={status} value={status}>{translateStatus(status, locale)}</option>
            ))}
          </select>

          <button type="button" onClick={() => void load()} className="btn-secondary">
            {translate("refresh")}
          </button>

          {selected.size > 0 && (
            <button type="button" onClick={exportSelected} disabled={exporting} className="btn-success">
              {exporting ? translate("loading")
                : `${translate("exportSelected")} (${selected.size})`}
            </button>
          )}
        </div>
      </div>

      {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="card overflow-hidden">
        {loading && documents.length === 0 ? (
          <p className="p-6 text-sm text-slate-500">{translate("loading")}</p>
        ) : documents.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-slate-500">{translate("noDocuments")}</p>
            <Link href="/upload" className="btn-primary mt-4 inline-flex">
              {translate("uploadButton")}
            </Link>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="w-10 px-3 py-2" />
                <th className="px-3 py-2">{translate("fileName")}</th>
                <th className="px-3 py-2">{translate("status")}</th>
                <th className="px-3 py-2">{translate("uploadedAt")}</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {documents.map((document) => (
                <tr key={document.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      aria-label={document.original_filename}
                      checked={selected.has(document.id)}
                      // Only reviewed documents can go to 1C.
                      disabled={!["ready", "confirmed", "needs_review"].includes(document.status)}
                      onChange={() => toggle(document.id)}
                    />
                  </td>
                  <td className="max-w-xs truncate px-3 py-2 text-slate-800">
                    {document.original_filename}
                    {document.error_message && (
                      <span className="ml-2 text-xs text-red-600">{document.error_message}</span>
                    )}
                  </td>
                  <td className="px-3 py-2"><StatusBadge status={document.status} /></td>
                  <td className="px-3 py-2 text-slate-600">{formatDateTime(document.created_at)}</td>
                  <td className="px-3 py-2 text-right">
                    <Link href={`/documents/${document.id}`} className="text-slate-900 underline">
                      {translate("reviewTitle")}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
