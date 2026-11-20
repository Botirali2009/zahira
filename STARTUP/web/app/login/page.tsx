"use client";

import Link from "next/link";
import { useState } from "react";

import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { useApp } from "@/lib/context";

export default function LoginPage() {
  const { login, translate } = useApp();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : String(exception));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">HujjatAI</h1>
            <p className="text-sm text-slate-600">{translate("tagline")}</p>
          </div>
          <LocaleSwitcher />
        </div>

        <form onSubmit={onSubmit} className="card space-y-4 p-6">
          <h2 className="text-lg font-medium">{translate("login")}</h2>

          <div>
            <label className="label" htmlFor="email">{translate("email")}</label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              className="input"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div>
            <label className="label" htmlFor="password">{translate("password")}</label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              className="input"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          {error && (
            <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <button type="submit" disabled={busy} className="btn-primary w-full">
            {busy ? translate("loading") : translate("login")}
          </button>

          <p className="text-center text-sm text-slate-600">
            {translate("noAccount")}{" "}
            <Link href="/register" className="font-medium text-slate-900 underline">
              {translate("register")}
            </Link>
          </p>
        </form>
      </div>
    </main>
  );
}
