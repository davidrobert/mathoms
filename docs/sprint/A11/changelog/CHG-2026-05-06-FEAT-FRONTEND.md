---
id: CHG-2026-05-06-FEAT-FRONTEND
type: changelog-entry
date: "2026-05-06"
sprint: A11
summary: |
  feat(frontend): CSS gate + tokens fantasma corrigidos (W1-T01 · 2026-05-06). - **feat(frontend): CSS gate + tokens fantasma corrigidos (W1-T01 · 2026-05-06):** Onda 1 do `archive/PLATFORM_REVIEW_PLAN-2026-07-08.md` — fecha cluster PD-001/002/005/023.
tags:
  - type/changelog-entry
  - sprint/a11
---


# feat(frontend): CSS gate + tokens fantasma corrigidos (W1-T01 · 2026-05-06)

- **feat(frontend): CSS gate + tokens fantasma corrigidos (W1-T01 · 2026-05-06):**
  Onda 1 do `archive/PLATFORM_REVIEW_PLAN-2026-07-08.md` — fecha cluster PD-001/002/005/023.
  Antes: `var(--semantic-danger|success|warning)` e `var(--brand-secondary)`
  consumidos em 7 arquivos do relatório premium / plano / ação resolviam
  para `unset` (cor herdada do parent ou preto), apesar de aparentarem
  cores semânticas. Tailwind classes `brand-500/400` (não existem na
  config v4 inline) também caíam silenciosamente.
  Fix: aliases em `design-tokens/tokens.json` (`--semantic-success` →
  gain, `--semantic-danger` → loss, `--semantic-warning` → alert,
  `--brand-secondary` → neutral) — preserva compat com qualquer
  consumidor externo futuro. `brand-500/400` substituídos por
  `[var(--brand-info)]` / `[var(--brand-accent)]`. Novo gate
  `dev/check_css_var_references.py` parseia `tokens.css` + `globals.css`,
  varre `frontend/src/**/*.{tsx,ts,css}` e falha se algum `var(--xxx)`
  não está declarado (allowlist runtime para `--font-*` de next/font e
  `--radix-*`). Hook pre-commit ativo. Smoke test em
  `frontend/tests/components/report/snapshotChangelog.test.tsx`
  valida `<ComparisonItemsBlock delta_signal="down"/>` aplicando
  `var(--semantic-danger)`. Visual baselines não atualizadas neste PR
  — diferimento para W5-T01 do plano (visual regression baselines).
