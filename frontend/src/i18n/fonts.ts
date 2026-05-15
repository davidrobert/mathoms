// ADR-130 revisado 2026-05-15 — escopo reduzido para 3 locales
// (pt-BR + en + es), todos Latin Extended-A.
//
// Plus Jakarta Sans + Inter + JetBrains Mono (next/font no layout)
// cobrem os 3 locales atuais; nenhum precisa de fonte secundária.
//
// FONT_HREFS permanece tipado mas vazio — quando locales CJK/RTL
// reentrarem (via nova ADR), entradas voltam aqui sem refactor de
// callers (`localeFontHrefs` mantém a mesma assinatura).

import type { Locale } from "./config";

const FONT_HREFS: Partial<Record<Locale, string>> = {};

export function localeFontHrefs(locale: Locale): readonly string[] {
  const href = FONT_HREFS[locale];
  return href ? [href] : [];
}
