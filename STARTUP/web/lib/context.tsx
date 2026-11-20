"use client";

/**
 * Session and language context.
 *
 * The locale lives in localStorage rather than the URL: an accountant sets it
 * once and never thinks about it again, and there is no SEO reason for
 * per-language routes behind a login.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { api, clearTokens, getAccessToken, setTokens, type Company, type User } from "./api";
import { DEFAULT_LOCALE, type Locale, t, type TranslationKey } from "./i18n";

const LOCALE_KEY = "hujjatai.locale";

interface AppContextValue {
  user: User | null;
  company: Company | null;
  locale: Locale;
  loading: boolean;
  setLocale: (locale: Locale) => void;
  translate: (key: TranslationKey) => string;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string; password: string; full_name?: string;
    company_name: string; company_tin?: string;
  }) => Promise<void>;
  logout: () => void;
  refreshCompany: () => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = window.localStorage.getItem(LOCALE_KEY) as Locale | null;
    if (stored) setLocaleState(stored);

    if (!getAccessToken()) {
      setLoading(false);
      return;
    }
    Promise.all([api.me(), api.company()])
      .then(([me, workspace]) => {
        setUser(me);
        setCompany(workspace);
        // A workspace language set by the admin wins on first load, so a new
        // colleague sees the interface their team already chose.
        if (!stored && workspace.locale) setLocaleState(workspace.locale as Locale);
      })
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    window.localStorage.setItem(LOCALE_KEY, next);
  }, []);

  const translate = useCallback((key: TranslationKey) => t(key, locale), [locale]);

  const afterAuth = useCallback(async () => {
    const [me, workspace] = await Promise.all([api.me(), api.company()]);
    setUser(me);
    setCompany(workspace);
    router.push("/dashboard");
  }, [router]);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await api.login({ email, password });
    setTokens(tokens.access_token, tokens.refresh_token);
    await afterAuth();
  }, [afterAuth]);

  const register = useCallback(async (payload: {
    email: string; password: string; full_name?: string;
    company_name: string; company_tin?: string;
  }) => {
    const tokens = await api.register(payload);
    setTokens(tokens.access_token, tokens.refresh_token);
    await afterAuth();
  }, [afterAuth]);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    setCompany(null);
    router.push("/login");
  }, [router]);

  const refreshCompany = useCallback(async () => {
    setCompany(await api.company());
  }, []);

  const value = useMemo(
    () => ({ user, company, locale, loading, setLocale, translate, login, register, logout, refreshCompany }),
    [user, company, locale, loading, setLocale, translate, login, register, logout, refreshCompany],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used inside AppProvider");
  return context;
}
