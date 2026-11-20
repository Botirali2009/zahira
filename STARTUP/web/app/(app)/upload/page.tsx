"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { api, type UploadResult } from "@/lib/api";
import { useApp } from "@/lib/context";
import { formatFileSize } from "@/lib/format";

const MAX_FILES = 20;

export default function UploadPage() {
  const { translate } = useApp();
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  function addFiles(incoming: FileList | null) {
    if (!incoming) return;
    setFiles((current) => [...current, ...Array.from(incoming)].slice(0, MAX_FILES));
    setResult(null);
  }

  async function submit() {
    if (files.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.upload(files));
      setFiles([]);
      if (inputRef.current) inputRef.current.value = "";
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : String(exception));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900">{translate("uploadTitle")}</h1>

      <div
        onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          addFiles(event.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => { if (event.key === "Enter") inputRef.current?.click(); }}
        className={`card flex cursor-pointer flex-col items-center justify-center gap-2 border-2 border-dashed
                    px-6 py-12 text-center transition-colors ${
          dragging ? "border-slate-900 bg-slate-100" : "border-slate-300 hover:bg-slate-50"
        }`}
      >
        <svg className="h-10 w-10 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"
             strokeWidth={1.5} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round"
                d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-.41-8.98 4.5 4.5 0 0 1 8.4-2.61 3 3 0 0 1 3.75 3.75 4.5 4.5 0 0 1 .41 8.98H6.75Z" />
        </svg>
        <p className="text-sm font-medium text-slate-700">{translate("dropFiles")}</p>
        <p className="text-xs text-slate-500">{translate("uploadHint")}</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="application/pdf,image/jpeg,image/png,image/tiff"
          className="hidden"
          onChange={(event) => addFiles(event.target.files)}
        />
      </div>

      {files.length > 0 && (
        <section className="card p-4">
          <h2 className="mb-3 text-sm font-medium text-slate-700">
            {translate("selectedFiles")} ({files.length})
          </h2>
          <ul className="mb-4 divide-y divide-slate-100">
            {files.map((file, index) => (
              <li key={`${file.name}-${index}`} className="flex items-center justify-between py-2 text-sm">
                <span className="truncate text-slate-800">{file.name}</span>
                <span className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">{formatFileSize(file.size)}</span>
                  <button
                    type="button"
                    className="text-xs text-red-600 hover:underline"
                    onClick={() => setFiles((current) => current.filter((_, i) => i !== index))}
                  >
                    ✕
                  </button>
                </span>
              </li>
            ))}
          </ul>
          <button type="button" onClick={submit} disabled={busy} className="btn-primary">
            {busy ? translate("uploading") : translate("uploadButton")}
          </button>
        </section>
      )}

      {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {result && (
        <section className="space-y-4">
          {result.accepted.length > 0 && (
            <div className="card p-4">
              <h2 className="mb-2 text-sm font-medium text-emerald-800">
                {translate("uploadAccepted")} ({result.accepted.length})
              </h2>
              <ul className="divide-y divide-slate-100">
                {result.accepted.map((document) => (
                  <li key={document.id} className="flex items-center justify-between py-2 text-sm">
                    <span className="truncate text-slate-800">{document.original_filename}</span>
                    <Link href={`/documents/${document.id}`} className="text-slate-900 underline">
                      {translate("reviewTitle")}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Partial success is normal: one bad file in a scanner batch must not
              hide the nineteen that worked. */}
          {result.rejected.length > 0 && (
            <div className="card border-red-200 p-4">
              <h2 className="mb-2 text-sm font-medium text-red-800">
                {translate("uploadRejected")} ({result.rejected.length})
              </h2>
              <ul className="divide-y divide-slate-100">
                {result.rejected.map((item, index) => (
                  <li key={`${item.filename}-${index}`} className="py-2 text-sm">
                    <span className="font-medium text-slate-800">{item.filename}</span>
                    <span className="ml-2 text-red-700">{item.reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
