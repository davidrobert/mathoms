// F12.1e · ADR-130 revisado 2026-04-26 — Locales suportados (10), default
// e RTL set. Fonte: docs/I18N_PLAN.md §1.1.

export const LOCALES = [
  "pt-BR",
  "en",
  "pt-PT",
  "zh-CN",
  "es",
  "fr",
  "ru",
  "de",
  "ja",
  "ko",
] as const;

export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "pt-BR";

// Sem locales RTL no escopo F12 (ADR-130 revisado). Mantido tipado para
// reentrada futura — getDir continua simétrico.
export const RTL_LOCALES: ReadonlySet<Locale> = new Set<Locale>();

export const LOCALE_COOKIE = "NEXT_LOCALE";

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

export function getDir(locale: Locale): "ltr" | "rtl" {
  return RTL_LOCALES.has(locale) ? "rtl" : "ltr";
}
