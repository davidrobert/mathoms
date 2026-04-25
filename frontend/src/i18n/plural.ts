// F12.1 · ADR-130 — helper ICU MessageFormat.
// next-intl@4 já delega plurais para ICU MessageFormat via Intl.PluralRules
// nativo do runtime. Este módulo expõe o resolver direto para casos
// onde precisamos calcular a categoria (zero/one/two/few/many/other) fora
// do contexto de tradução — ex.: validações de teste, escolha de ícone.

import type { Locale } from "./config";

export type PluralCategory = Intl.LDMLPluralRule;

const cache = new Map<Locale, Intl.PluralRules>();

function getRules(locale: Locale): Intl.PluralRules {
  let rules = cache.get(locale);
  if (!rules) {
    rules = new Intl.PluralRules(locale);
    cache.set(locale, rules);
  }
  return rules;
}

export function pluralCategory(locale: Locale, n: number): PluralCategory {
  return getRules(locale).select(n);
}
