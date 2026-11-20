"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { getAccessToken } from "@/lib/api";
import { useApp } from "@/lib/context";
import type { TranslationKey } from "@/lib/i18n";

const NAV: { href: string; key: TranslationKey }[] = [
  { href: "/dashboard", key: "navDashboard" },
  { href: "/upload", key: "navUpload" },
  { href: "/documents", key: "navDocuments" },
  { href: "/settings", key: "navSettings" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, company, loading, logout, translate } = useApp();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !getAccessToken()) router.replace("/login");
  }, [loading, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-slate-500">{translate("loading")}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-8">
            <Link href="/dashboard" className="text-lg font-semibold text-slate-900">
              HujjatAI
            </Link>
            <nav className="flex items-center gap-1">
              {NAV.map((item) => {
                const active = pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      active ? "bg-slate-100 text-slate-900" : "text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    {translate(item.key)}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <LocaleSwitcher />
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium text-slate-900">{company?.name}</p>
              <p className="text-xs text-slate-500">{user?.email}</p>
            </div>
            <button type="button" onClick={logout} className="btn-secondary">
              {translate("logout")}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  );
}
