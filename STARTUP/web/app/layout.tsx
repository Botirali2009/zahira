import type { Metadata } from "next";

import { AppProvider } from "@/lib/context";

import "./globals.css";

export const metadata: Metadata = {
  title: "HujjatAI — Hisob-fakturalarni avtomatik o'qish",
  description:
    "O'zbek tilidagi hisob-fakturalarni avtomatik o'qib, 1C ga tayyor fayl yaratadi.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // lang="uz" by default; the in-app switcher changes only the strings, not the
  // document language, because the workspace can contain readers of both scripts.
  return (
    <html lang="uz">
      <body>
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
