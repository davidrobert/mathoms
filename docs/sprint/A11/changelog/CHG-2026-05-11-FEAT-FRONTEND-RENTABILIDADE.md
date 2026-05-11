---
id: CHG-2026-05-11-FEAT-FRONTEND-RENTABILIDADE
type: changelog-entry
date: "2026-05-11"
sprint: A11
lane: "[[A11.w5]]"
adrs:
  - "[[ADR-191]]"
summary: |
  feat(frontend): card Rentabilidade rebrandeado — TRS efetiva full-width + KPI hero
  + cobertura essencial + empty states (PR-B do track T06 · ADR-191).
tags:
  - type/changelog-entry
  - sprint/a11
  - area/frontend
  - area/report
---

# feat(frontend): card Rentabilidade rebrandeado (ADR-191 §D1)

PR-B do track [TRACK-a11-w5-t06-rentabilidade-card](../tracks/a11-w5-t06-rentabilidade-card.md)
consome o shape aninhado entregue em PR-A e re-renderiza o card "Rentabilidade"
da seção S3 ([S3InvestimentosSection.tsx](../../../../frontend/src/components/report/sections/S3InvestimentosSection.tsx)).

**Antes:** card meio-largo mostrando só um número solto (ex.: `3,25%`) sem
ano-base, sem comparativo, sem indicação do que é medido. Usuário não conseguia
interpretar.

**Agora:** card **full-width** (`md:col-span-4`) com:

- KPI hero "TRS efetiva (% a.a.)" com variant semântica por status vs meta.
- Comparativo com meta 5% (referência consagrada, sem nomear metodologia —
  §13 COPY_GUIDELINES).
- Métrica derivada "cobre N% das despesas essenciais via renda passiva"
  (tradução operacional de "renda passiva sustenta seu padrão de vida básico").
- Rodapé com ano-base IRPF + defasagem em meses.
- Empty state honesto por `status`:
  - `sem_irpf` → CTA "Documentos → Adicionar".
  - `gerador_zero` → explica ausência de carteira de renda.
  - `sem_dados_essencial` → mostra TRS, omite cobertura, nota "categorização
    incompleta".
- Badge "Dado defasado" quando `defasagem_meses > 18`.
- Microcopy explicando TRS efetiva ≠ retorno total da carteira.

**Entregue:**

- `frontend/src/components/report/cards/RentabilidadeCard.tsx` (novo).
- `frontend/src/types/report-analysis.ts` extende `RatiosData` com
  `rentabilidade?: RentabilidadeRatio | null` + enum `RentabilidadeStatus`.
  Campo flat `rentabilidade_pct` preservado por back-compat.
- `S3InvestimentosSection.tsx` substitui card legado pelo novo
  `<RentabilidadeCard />` full-width.
- `frontend/tests/components/RentabilidadeCard.test.tsx` (novo) — 12 unit
  cobrindo 4 status + branch defasagem >18m + fallback back-compat (workspace
  sem campo aninhado).
- Tokens: usa `var(--brand-warning)` + `color-mix` (sem hex; ADR-076).

**Decisões fechadas (ADR-191 §D5 — não rediscutir):**

- Sem CDI no card, sem retorno total, sem Trinity 4%, sem rename interno.

**Visual snapshots:** baselines S3 light/dark podem precisar de refresh
em CI — fixture `medium` continua sem campo `rentabilidade` aninhado
(fallback path renderiza, visual estável). Quando fixture for atualizada
para exercitar o novo design, baseline refresh é manual via
`--update-snapshots` no CI.

**Tests:** 12 unit (`RentabilidadeCard`) + 868 demais (sem regressão);
880 passed pós-mudança.
