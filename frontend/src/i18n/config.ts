// F12.1 · ADR-130 — Locales suportados (11), default e RTL set.
// Fonte: docs/I18N_PLAN.md §1.1.

export const LOCALES = [
  "pt-BR",
  "en",
  "pt-PT",
  "zh-CN",
  "hi",
  "es",
  "ar",
  "fr",
  "bn",
  "ru",
  "id",
] as const;

export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "pt-BR";

export const RTL_LOCALES: ReadonlySet<Locale> = new Set(["ar"]);

export const LOCALE_COOKIE = "NEXT_LOCALE";

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

export function getDir(locale: Locale): "ltr" | "rtl" {
  return RTL_LOCALES.has(locale) ? "rtl" : "ltr";
}
