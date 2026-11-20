/**
 * Display formatting.
 *
 * Amounts are rendered the way Uzbek accounting software does — space thousands
 * separators, comma decimals — because the number on screen has to be visually
 * comparable to the number on the paper invoice next to the monitor.
 */

import type { Locale } from "./i18n";

export function formatAmount(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const numeric = typeof value === "number" ? value : Number(String(value).replace(/\s/g, ""));
  if (Number.isNaN(numeric)) return String(value);
  const [whole, fraction = "00"] = numeric.toFixed(2).split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${grouped},${fraction}`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${day}.${month}.${date.getFullYear()}`;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const time = date.toTimeString().slice(0, 5);
  return `${formatDate(value)} ${time}`;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDuration(ms: number | null | undefined): string {
  if (!ms) return "—";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

/** Hours and minutes, in the active language. */
export function formatMinutesSaved(minutes: number, locale: Locale): string {
  const labels: Record<Locale, { h: string; m: string }> = {
    uz: { h: "soat", m: "daqiqa" },
    "uz-Cyrl": { h: "соат", m: "дақиқа" },
    ru: { h: "ч", m: "мин" },
  };
  const label = labels[locale];
  if (minutes < 60) return `${minutes} ${label.m}`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} ${label.h} ${rest} ${label.m}` : `${hours} ${label.h}`;
}

export type ConfidenceLevel = "high" | "medium" | "low";

/**
 * 0.85 is the review threshold used by the backend; keeping the same number
 * here means the colour on screen always agrees with the "needs review" queue.
 */
export function confidenceLevel(confidence: number): ConfidenceLevel {
  if (confidence >= 0.85) return "high";
  if (confidence >= 0.6) return "medium";
  return "low";
}

export const CONFIDENCE_STYLES: Record<ConfidenceLevel, { border: string; badge: string; text: string }> = {
  high: {
    border: "border-l-4 border-l-green-600",
    badge: "bg-green-100 text-green-800",
    text: "text-green-700",
  },
  medium: {
    border: "border-l-4 border-l-amber-500",
    badge: "bg-amber-100 text-amber-800",
    text: "text-amber-700",
  },
  low: {
    border: "border-l-4 border-l-red-600",
    badge: "bg-red-100 text-red-800",
    text: "text-red-700",
  },
};

export const STATUS_STYLES: Record<string, string> = {
  pending: "bg-slate-100 text-slate-700",
  processing: "bg-blue-100 text-blue-700",
  ready: "bg-green-100 text-green-800",
  needs_review: "bg-amber-100 text-amber-800",
  confirmed: "bg-emerald-100 text-emerald-800",
  failed: "bg-red-100 text-red-800",
};
