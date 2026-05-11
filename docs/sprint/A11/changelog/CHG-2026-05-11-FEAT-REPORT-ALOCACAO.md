---
id: CHG-2026-05-11-FEAT-REPORT-ALOCACAO
type: changelog-entry
date: "2026-05-11"
sprint: A11
lane: "[[A12.alocacao-v2]]"
adrs:
  - "[[ADR-141]]"
  - "[[ADR-193]]"
summary: |
  feat(report): card AlocacaoAtualVsAlvoCard substitui 3 cards S3 (Fase A
  · v1). Bullet chart com tick de alvo + tabela ordenada por |desvio| +
  footer imperativo. Caixa exibida como "Reserva" fora do denominador;
  Cripto/Outros como "Fora do alvo". Cálculo client-side sobre schema v1;
  ADR-141 promovida Roadmap→Proposto com plano de migração v2 (A12).
tags:
  - type/changelog-entry
  - sprint/a11
  - area/report
  - area/frontend
  - area/methodology
  - methodology/auvp
---

# feat(report): redesenho S3 — card Alocação · Atual vs Alvo (Fase A v1)

Substitui em S3 três cards legados — `NarrativeChartCard(alocacao_atual)`,
`NarrativeChartCard(alocacao_alvo)` e `InvestimentosClasseCard` — por um
único card full-width `AlocacaoAtualVsAlvoCard` que responde à pergunta
chave da seção: "estou desviando da meta? onde e quanto?".

Co-design com `product-designer`, `financial-planner` e `data-engineer`
em paralelo antes do código (2026-05-11).

**Entregue:**

- `frontend/src/components/report/utils/alocacaoBucketMapper.ts`: util
  agrega `tabela_classes` (10 buckets canônicos [ADR-193]) em 4 buckets
  do alvo v1 com decisões validadas pelo financial-planner:
  - **Caixa** fora do denominador (reserva ≠ investimento); exibida como
    linha "Reserva" separada com `alvo: null`.
  - **Cripto + Outros** vão para linha "Fora do alvo" (alvo=0, desvio=+pp).
  - **Previdência → Renda Fixa**, **Fundos → Ações**, **Internacional →
    Liquidez USD** são aproximações documentadas no card.
- `frontend/src/components/report/cards/AlocacaoAtualVsAlvoCard.tsx`: card
  com header (total + split investível/reserva), badge de severidade
  (`alinhado` ≤2pp / `atenção` 2-5pp / `rebalancear` >5pp), bullet chart
  com tick vertical 2px no alvo (sobre trilho cinza-claro), tabela
  desktop ordenada por |desvio| desc e cards stacked em mobile <768px,
  footer imperativo. Aria-labels completas (WCAG 1.4.1).
- `frontend/src/components/report/utils/conclusionUtils.ts`: builder
  dinâmico para `alocacao_atual` (próximo aporte → classe sub-alocada)
  e `alocacao_alvo` (maior desvio em pp); fallback CTA para
  `/plano/alocacao` quando sem alvo.
- `config/prompts/chart_conclusions.yaml`: templates imperativos cap 200
  chars com lista de termos banidos ("recomenda-se", "gradualmente",
  "sugere-se", "considerar", "talvez", "idealmente").
- `config/report_layout.yaml` (+ codegen `frontend/src/generated/
  report-layout.ts` + `backend/app/generated/report_layout.py`):
  tombstones via `enabled: false` para 3 entries; nova entry
  `alocacao_atual_vs_alvo` em `cards:`. Chart IDs `alocacao_atual` e
  `alocacao_alvo` mantidos em `ALL_CHART_IDS` e narrativas E5N para
  não quebrar 4 enforcers no pipeline.
- 15 testes Vitest novos (9 unit `alocacaoBucketMapper`, 6 DOM
  `AlocacaoAtualVsAlvoCard`) cobrindo: vazio retorna null, sem alvo →
  CTA, alinhado, rebalancear, llmFooter override, "Fora do alvo" +
  nota de rodapé.

**Decisões pragmáticas (Fase A):**

1. **Cálculo client-side.** v1 não tem `derived.desvio_por_classe`;
   v2 ([ADR-141]) tem. Duplicar no backend agora vira dead-code em
   1-2 sprints — débito explícito da ADR-141.
2. **Tombstones em vez de `git rm`.** Padrão estabelecido no repo
   (`milhas`, `viagens`); preserva IDs no `ALL_CARD_IDS`/`ALL_CHART_IDS`
   e evita quebra dos 4 enforcers do pipeline (`e7_review._REQUIRED_CHARTS`,
   `format_helpers.required_charts`, `charts_narrator`,
   `test_e5n_builder_decomposition`).
3. **NarrativeChartCard não renomeado.** 6 consumers ativos (S4, S7, S8,
   S9, S10) — refactor mecânico fica para PR separado.

**ADR-141 promovida Roadmap → Proposto.** Seção "Débito de Fase A"
lista os 6 itens a remover/migrar quando v2 entrar; lane
[[A12.alocacao-v2]] aberta como `ready` (5d eng).

**Aprendizados não-óbvios:**

- O seeder (`backend/app/scripts/seed_goals_workspace.py`) grava
  `rf_pct/rv_pct/alternativos_pct` enquanto o serializer lê
  `renda_fixa_pct/acoes_pct/imoveis_reits_pct/liquidez_usd_pct` —
  inconsistência herdada; corrigida na lane v2.
- `chart_canvas_map` em `report_layout.yaml` é dead-code latente
  desde [ADR-129] (renderer único React, PDF via Playwright sobre rota
  `/reports/[id]`). Limpeza vai junto com a lane v2.
