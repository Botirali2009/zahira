"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, type DashboardStats } from "@/lib/api";
import { useApp } from "@/lib/context";
import { formatDuration, formatMinutesSaved } from "@/lib/format";

export default function DashboardPage() {
  const { translate, locale } = useApp();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboard().then(setStats).catch((exception) => setError(String(exception)));
  }, []);

  if (error) {
    return <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>;
  }
  if (!stats) {
    return <p className="text-sm text-slate-500">{translate("loading")}</p>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900">{translate("navDashboard")}</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={translate("documentsThisMonth")}
          value={String(stats.documents_this_month)}
          hint={`${translate("quotaUsed")}: ${stats.quota_used_percent}%`}
        />
        {/* The number the chief accountant repeats to their director. */}
        <StatCard
          label={translate("timeSaved")}
          value={formatMinutesSaved(stats.minutes_saved_this_month, locale)}
          accent="text-emerald-700"
        />
        <StatCard
          label={translate("needsReview")}
          value={String(stats.needs_review)}
          accent={stats.needs_review > 0 ? "text-amber-700" : undefined}
          href={stats.needs_review > 0 ? "/documents?status=needs_review" : undefined}
        />
        <StatCard
          label={translate("averageAccuracy")}
          value={`${Math.round(stats.average_confidence * 100)}%`}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="card p-4">
          <h2 className="mb-3 text-sm font-medium text-slate-700">{translate("topVendors")}</h2>
          {stats.top_vendors.length === 0 ? (
            <p className="text-sm text-slate-500">{translate("noDataYet")}</p>
          ) : (
            <table className="w-full text-sm">
              <tbody>
                {stats.top_vendors.map((vendor) => (
                  <tr key={vendor.vendor_tin} className="border-b border-slate-100 last:border-0">
                    <td className="py-2 pr-2">
                      <span className="font-medium text-slate-800">{vendor.vendor_name}</span>
                      <span className="ml-2 text-xs text-slate-500">{vendor.vendor_tin}</span>
                    </td>
                    <td className="py-2 text-right text-slate-600">{vendor.documents}</td>
                    <td className="py-2 pl-2 text-right">
                      {/* An active template means this vendor's invoices no
                          longer cost anything to extract. */}
                      {vendor.template_active && (
                        <span className="badge bg-emerald-100 text-emerald-800">auto</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="card space-y-2 p-4 text-sm">
          <h2 className="mb-3 text-sm font-medium text-slate-700">{translate("navDashboard")}</h2>
          <Row label={translate("knownVendors")} value={String(stats.known_vendors)} />
          <Row
            label={translate("correctionRate")}
            value={`${Math.round(stats.correction_rate * 100)}%`}
          />
          <Row
            label={translate("processedIn")}
            value={formatDuration(stats.average_processing_ms)}
          />
          <Row label={translate("statusConfirmed")} value={String(stats.confirmed_this_month)} />
          <Row label={translate("statusFailed")} value={String(stats.failed_this_month)} />
        </section>
      </div>
    </div>
  );
}

function StatCard({
  label, value, hint, accent, href,
}: {
  label: string; value: string; hint?: string; accent?: string; href?: string;
}) {
  const content = (
    <div className="card p-4">
      <p className="text-sm text-slate-600">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${accent ?? "text-slate-900"}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
  return href ? <Link href={href} className="block transition-shadow hover:shadow-md">{content}</Link> : content;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 py-1.5 last:border-0">
      <span className="text-slate-600">{label}</span>
      <span className="font-medium text-slate-900">{value}</span>
    </div>
  );
}
