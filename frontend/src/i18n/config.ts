// ADR-130 revisado 2026-05-15 — escopo reduzido para 3 locales
// (pt-BR + en + es). ICP confirmado: brasileiros nômades digitais
// morando fora do Brasil. Demais 7 locales (pt-PT/zh-CN/fr/ru/de/ja/ko)
// saem do escopo F12. Fonte: docs/plan/I18N/_README.md §1.1.

export const LOCALES = ["pt-BR", "en", "es"] as const;

export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "pt-BR";

// Sem locales RTL no escopo F12. Mantido tipado para reentrada futura —
// getDir continua simétrico e RTL_LOCALES preserva o shape esperado.
export const RTL_LOCALES: ReadonlySet<Locale> = new Set<Locale>();

export const LOCALE_COOKIE = "NEXT_LOCALE";

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

export function getDir(locale: Locale): "ltr" | "rtl" {
  return RTL_LOCALES.has(locale) ? "rtl" : "ltr";
}
