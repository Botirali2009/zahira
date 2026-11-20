"use client";

import Link from "next/link";
import { useState } from "react";

import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { useApp } from "@/lib/context";

export default function RegisterPage() {
  const { register, translate } = useApp();
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    company_name: "",
    company_tin: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function update(field: keyof typeof form) {
    return (event: React.ChangeEvent<HTMLInputElement>) =>
      setForm((current) => ({ ...current, [field]: event.target.value }));
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await register({
        email: form.email,
        password: form.password,
        full_name: form.full_name || undefined,
        company_name: form.company_name,
        company_tin: form.company_tin || undefined,
      });
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : String(exception));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-8">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">HujjatAI</h1>
            <p className="text-sm text-slate-600">{translate("tagline")}</p>
          </div>
          <LocaleSwitcher />
        </div>

        <form onSubmit={onSubmit} className="card space-y-4 p-6">
          <h2 className="text-lg font-medium">{translate("register")}</h2>

          <div>
            <label className="label" htmlFor="company_name">{translate("companyName")}</label>
            <input
              id="company_name"
              required
              minLength={2}
              className="input"
              placeholder='"AGROMASH SERVIS" MChJ'
              value={form.company_name}
              onChange={update("company_name")}
            />
          </div>

          <div>
            <label className="label" htmlFor="company_tin">{translate("companyTin")}</label>
            <input
              id="company_tin"
              className="input"
              inputMode="numeric"
              pattern="\d{9}"
              placeholder="205673412"
              value={form.company_tin}
              onChange={update("company_tin")}
            />
          </div>

          <div>
            <label className="label" htmlFor="full_name">{translate("fullName")}</label>
            <input id="full_name" className="input" value={form.full_name} onChange={update("full_name")} />
          </div>

          <div>
            <label className="label" htmlFor="email">{translate("email")}</label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              className="input"
              value={form.email}
              onChange={update("email")}
            />
          </div>

          <div>
            <label className="label" htmlFor="password">{translate("password")}</label>
            <input
              id="password"
              type="password"
              required
              minLength={10}
              autoComplete="new-password"
              className="input"
              value={form.password}
              onChange={update("password")}
            />
          </div>

          {error && (
            <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <button type="submit" disabled={busy} className="btn-primary w-full">
            {busy ? translate("loading") : translate("register")}
          </button>

          <p className="text-center text-sm text-slate-600">
            {translate("haveAccount")}{" "}
            <Link href="/login" className="font-medium text-slate-900 underline">
              {translate("login")}
            </Link>
          </p>
        </form>
      </div>
    </main>
  );
}
