// F12.1e · ADR-130 revisado 2026-04-26 — Carregamento condicional de fontes
// secundárias.
//
// As fontes default (Plus Jakarta Sans, Inter, JetBrains Mono via next/font)
// cobrem Latin Extended-A; bastam para 7 dos 10 locales (Latin LTR + ru
// Cyrillic, ambos cobertos por Inter).
//
// Para os 3 locales CJK (zh-CN, ja, ko) precisamos de Noto Sans secundárias.
// Carregadas via `<link rel="stylesheet">` apenas quando o locale ativo as
// requer — evita ~430KB de wire em sessões pt-BR/en/etc. Trade-off
// documentado em docs/I18N_PLAN.md §7.

import type { Locale } from "./config";

// Família Noto Sans (Google Fonts CDN) — variável CSS já é "Noto Sans <X>",
// fallback feito via `font-family` em globals.css quando lang=<locale>.
const FONT_HREFS: Partial<Record<Locale, string>> = {
  "zh-CN":
    "https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap",
  ja: "https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap",
  ko: "https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap",
};

export function localeFontHrefs(locale: Locale): readonly string[] {
  const href = FONT_HREFS[locale];
  return href ? [href] : [];
}
