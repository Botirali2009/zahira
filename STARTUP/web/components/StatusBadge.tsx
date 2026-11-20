"use client";

import { STATUS_STYLES } from "@/lib/format";
import { translateStatus } from "@/lib/i18n";
import { useApp } from "@/lib/context";

export function StatusBadge({ status }: { status: string }) {
  const { locale } = useApp();
  return (
    <span className={`badge ${STATUS_STYLES[status] ?? "bg-slate-100 text-slate-700"}`}>
      {translateStatus(status, locale)}
    </span>
  );
}
