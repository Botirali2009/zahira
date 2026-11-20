"use client";

import { useEffect, useState } from "react";

import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { api, type User } from "@/lib/api";
import { useApp } from "@/lib/context";

export default function SettingsPage() {
  const { company, user, translate, refreshCompany } = useApp();
  const [form, setForm] = useState({ name: "", tin: "", address: "" });
  const [onec, setOnec] = useState({ organization_name: "", organization_tin: "", operation: "" });
  const [users, setUsers] = useState<User[]>([]);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!company) return;
    setForm({ name: company.name, tin: company.tin ?? "", address: company.address ?? "" });
    const config = company.onec_config ?? {};
    setOnec({
      organization_name: String(config.organization_name ?? company.name ?? ""),
      organization_tin: String(config.organization_tin ?? company.tin ?? ""),
      operation: String(config.operation ?? "Счет на оплату"),
    });
  }, [company]);

  useEffect(() => { api.users().then(setUsers).catch(() => setUsers([])); }, []);

  async function save() {
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await api.updateCompany({
        name: form.name,
        tin: form.tin || null,
        address: form.address || null,
        // Stored per company: 1C configurations differ between customers and
        // the export mapping has to follow theirs, not ours.
        onec_config: onec,
      });
      await refreshCompany();
      setSaved(true);
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : String(exception));
    } finally {
      setBusy(false);
    }
  }

  const isAdmin = user?.role === "admin";

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-xl font-semibold text-slate-900">{translate("settingsTitle")}</h1>

      <section className="card p-4">
        <h2 className="mb-3 text-sm font-medium text-slate-700">{translate("interfaceLanguage")}</h2>
        <LocaleSwitcher />
      </section>

      <section className="card space-y-4 p-4">
        <h2 className="text-sm font-medium text-slate-700">{translate("companySettings")}</h2>

        <div>
          <label className="label" htmlFor="name">{translate("companyName")}</label>
          <input id="name" className="input" disabled={!isAdmin} value={form.name}
                 onChange={(event) => setForm({ ...form, name: event.target.value })} />
        </div>
        <div>
          <label className="label" htmlFor="tin">{translate("companyTin")}</label>
          <input id="tin" className="input" disabled={!isAdmin} value={form.tin}
                 onChange={(event) => setForm({ ...form, tin: event.target.value })} />
        </div>
        <div>
          <label className="label" htmlFor="address">{translate("address")}</label>
          <input id="address" className="input" disabled={!isAdmin} value={form.address}
                 onChange={(event) => setForm({ ...form, address: event.target.value })} />
        </div>
      </section>

      <section className="card space-y-4 p-4">
        <h2 className="text-sm font-medium text-slate-700">{translate("onecSettings")}</h2>

        <div>
          <label className="label" htmlFor="org">{translate("onecOrganization")}</label>
          <input id="org" className="input" disabled={!isAdmin} value={onec.organization_name}
                 onChange={(event) => setOnec({ ...onec, organization_name: event.target.value })} />
        </div>
        <div>
          <label className="label" htmlFor="orgtin">{translate("companyTin")}</label>
          <input id="orgtin" className="input" disabled={!isAdmin} value={onec.organization_tin}
                 onChange={(event) => setOnec({ ...onec, organization_tin: event.target.value })} />
        </div>
        <div>
          <label className="label" htmlFor="operation">{translate("onecOperation")}</label>
          <select id="operation" className="input" disabled={!isAdmin} value={onec.operation}
                  onChange={(event) => setOnec({ ...onec, operation: event.target.value })}>
            <option value="Счет на оплату">Счет на оплату</option>
            <option value="Поступление товаров и услуг">Поступление товаров и услуг</option>
            <option value="Заказ товара">Заказ товара</option>
          </select>
        </div>

        {isAdmin && (
          <div className="flex items-center gap-3">
            <button type="button" onClick={save} disabled={busy} className="btn-primary">
              {busy ? translate("saving") : translate("save")}
            </button>
            {saved && <span className="text-sm text-emerald-700">{translate("saved")}</span>}
            {error && <span className="text-sm text-red-700">{error}</span>}
          </div>
        )}
      </section>

      <section className="card p-4">
        <h2 className="mb-3 text-sm font-medium text-slate-700">{translate("team")}</h2>
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="py-1">{translate("email")}</th>
              <th className="py-1">{translate("fullName")}</th>
              <th className="py-1">{translate("role")}</th>
            </tr>
          </thead>
          <tbody>
            {users.map((member) => (
              <tr key={member.id} className="border-b border-slate-100 last:border-0">
                <td className="py-1.5 text-slate-800">{member.email}</td>
                <td className="py-1.5 text-slate-600">{member.full_name ?? "—"}</td>
                <td className="py-1.5 text-slate-600">{member.role}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
