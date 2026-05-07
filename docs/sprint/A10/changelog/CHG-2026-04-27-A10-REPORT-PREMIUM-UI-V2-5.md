---
id: CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-5
type: changelog-entry
date: "2026-04-27"
sprint: A10
adrs: ["[[ADR-090]]"]
commits: ["0805a87", "38aa0ee"]
summary: |
  Report Premium UI v2.4 — T2 Aportes seção real ✅ (2026-04-27). - **Report Premium UI v2.4 — T2 Aportes seção real ✅ (2026-04-27):** Substitui stub "estará disponível…" de `T2AportesSection` por seção real, fechando o débito
tags:
  - type/changelog-entry
  - sprint/a10
---


# Report Premium UI v2.4 — T2 Aportes seção real ✅ (2026-04-27)

- **Report Premium UI v2.4 — T2 Aportes seção real ✅ (2026-04-27):**
  Substitui stub "estará disponível…" de `T2AportesSection` por seção
  real, fechando o débito que a Fase 8 da v1 marcou ✅ embora T2 nunca
  tenha sido implementada. **Decisão D1=(a) MVP determinístico:** dados
  já existem em `dashboard.aportes` (status por destino, meta,
  valor_feito) + `dashboard.investimentos_delta` (variação por bloco)
  do snapshot E5 — paridade com `EXEMPLO_DE_RELATORIO.html:1477-1484`
  (`dash-aportes`); zero mudança de pipeline/backend/endpoint.

  Render: KPI strip (5 slots: destinos, concluídos, total realizado,
  meta, % cobertura), grade de cards (1 por aporte com badge
  OK/Pendente, valor efetivo vs meta) e tabela "Variação Patrimonial
  por Bloco". Conclusion lê `narrativas[t2_aportes].conclusion` (E5.N
  LLM) com fallback determinístico.

  Tipos novos em
  [`frontend/src/types/report-analysis.ts`](../frontend/src/types/report-analysis.ts):
  `AporteItem`, `InvestimentoDeltaItem`, `DashboardData` (subset
  tipado, mantém `[key: string]: unknown` para chaves consumidas por
  T1/T3/T5). Adapter puro em
  [`frontend/src/components/report/utils/aportesAdapter.ts`](../frontend/src/components/report/utils/aportesAdapter.ts):
  `deriveAporteSummary` + `deriveInvestimentosDelta`. YAML
  [`config/report_layout.yaml`](../config/report_layout.yaml) T2
  declara `cards: [aportes_status, investimentos_delta]` (eram `[]`)
  + codegen TS/py atualizado.

  Tests: 5 casos novos em `dataAdapters.test.ts` + 4 em
  `taticoSections.test.tsx`; vitest 655 passed. Money sempre via
  `<MonetaryValue/>` (ADR-090). Funções TS ≤20 linhas (extração de
  helper `summarize()` no adapter para honrar code-style baseline).
  Commits: `0805a87` (feat) + `38aa0ee` (refactor honrando 20 linhas).
