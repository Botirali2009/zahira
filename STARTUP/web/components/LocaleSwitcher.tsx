"use client";

import { LOCALES, type Locale } from "@/lib/i18n";
import { useApp } from "@/lib/context";

/**
 * Three-way script switcher. Uzbek Latin and Uzbek Cyrillic are separate
 * options, not a single "Uzbek" — that distinction is the market this product
 * is built for.
 */
export function LocaleSwitcher() {
  const { locale, setLocale } = useApp();

  return (
    <div className="flex items-center rounded-md border border-slate-300 bg-white p-0.5">
      {LOCALES.map((option) => (
        <button
          key={option.code}
          type="button"
          onClick={() => setLocale(option.code as Locale)}
          aria-pressed={locale === option.code}
          className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
            locale === option.code
              ? "bg-slate-900 text-white"
              : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
