// F12.1 · ADR-130 — Carregamento condicional de fontes secundárias.
//
// As fontes default (Plus Jakarta Sans, Inter, JetBrains Mono via next/font)
// cobrem Latin Extended-A; bastam para 6 dos 11 locales (Latin LTR + ru
// Cyrillic, ambos cobertos por Inter).
//
// Para zh-CN, hi, bn, ar precisamos de Noto Sans secundárias. Carregadas
// via `<link rel="stylesheet">` apenas quando o locale ativo as requer —
// evita ~430KB de wire em sessões pt-BR/en/etc. Trade-off documentado em
// docs/I18N_PLAN.md §7.

import type { Locale } from "./config";

// Família Noto Sans (Google Fonts CDN) — variável CSS já é "Noto Sans <X>",
// fallback feito via `font-family` em globals.css quando lang=<locale>.
const FONT_HREFS: Partial<Record<Locale, string>> = {
  "zh-CN":
    "https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap",
  hi: "https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap",
  bn: "https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;500;600;700&display=swap",
  ar: "https://fonts.googleapis.com/css2?family=Noto+Sans+Arabic:wght@400;500;600;700&display=swap",
};

export function localeFontHrefs(locale: Locale): readonly string[] {
  const href = FONT_HREFS[locale];
  return href ? [href] : [];
}
