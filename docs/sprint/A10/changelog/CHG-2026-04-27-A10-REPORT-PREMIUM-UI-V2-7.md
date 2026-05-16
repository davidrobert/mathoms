---
id: CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-7
type: changelog-entry
date: "2026-04-27"
sprint: A10
summary: |
  Report Premium UI v2 — v2.6 `cards/` cleanup ✅ (2026-04-27). - **Report Premium UI v2 — v2.6 `cards/` cleanup ✅ (2026-04-27):** Auditoria pós-v1 (2026-04-25) classificou `frontend/src/components/report/cards/` como "pré-F
tags:
  - type/changelog-entry
  - sprint/a10
---


# Report Premium UI v2 — v2.6 `cards/` cleanup ✅ (2026-04-27)

- **Report Premium UI v2 — v2.6 `cards/` cleanup ✅ (2026-04-27):**
  Auditoria pós-v1 (2026-04-25) classificou
  `frontend/src/components/report/cards/` como "pré-Fase 3" e propôs
  três caminhos: (a) migrar para `ui/`; (b) deprecar como wrappers;
  (c) aceitar legacy. A lane reabriu com evidência empírica e a
  decisão final é **(c) refinada** — `cards/` é a **camada
  section-composer** legítima entre primitivos `ui/`
  (`Alert`/`Badge`/`Kpi`/`ScoreCard`/`Timeline`/…) e `sections/`
  (`S1`–`S10`). Todos os 14 cards já consomem o primitivo canônico
  `ReportCard`; carregam lógica de domínio atrelada a shapes
  específicos do DTO (`PatrimonioData`,
  `OrcamentoProspectivoData`, `EquilibrioCerbasiData`…) e
  pertencem a esta camada por design.

  **Cleanup entregue:**
  - `cards/_registry.ts` (com `MIGRATED_CARD_IDS` morto + nomenclatura
    F2.A obsoleta da migração v1) → `cards/index.ts` (barrel padrão
    com docstring de fronteira de camada + instrução explícita "não
    migrar para `ui/`");
  - 6 consumidores (`S1PatrimonioSection`, `S2FluxoCaixaSection`,
    `S3InvestimentosSection`, `S7IndependenciaSection`,
    `S10SinteseSection`, `ReportShell`) passam a importar pelo barrel
    (`from "../cards"`) em vez de cada arquivo individual;
  - `cards/PontosFortesList` → `cards/PontosFortesCard` (rename)
    resolve colisão de nome com `ui/PontoForteItem::PontosFortesList`
    (este último é primitivo `<ul>` com children; o card recebe
    `pontos: PontoForte[]` do DTO e wrappa em `ReportCard`);
  - `cards/PontosUrgentesList` → `cards/PontosUrgentesCard` por
    simetria;
  - decisão arquitetural registrada em
    [plan/REPORT_PREMIUM/_README.md §17.9](../../../plan/REPORT_PREMIUM/_README.md) com
    diagrama das camadas (`sections/` → `cards/` → `ui/` →
    `ReportCard`).

  **Zero mudança visual.** Apenas reorganização de imports + 2
  renames + docs. Vitest + pre-commit verdes; tsc clean em `src/`
  (erros pré-existentes em `tests/` são unrelated).

  **Não escopo (deferido):** dedup de
  `report/PeriodToggle.tsx` (legado, encaixa em `headerRight` de
  `ReportCard`) vs `ui/PeriodToggle.tsx` (v2.E.1, segmented control
  acima de chart) — APIs distintas com propósitos legítimos
  diferentes; eventual dedup vai para v2.6b/v3. `lib/periodUtils.ts`
  e `hooks/usePeriodTransactions` ficam intocados (servem caso de
  lista bruta de `TransactionItem[]`, não competem com
  `report/hooks/usePeriodWindow` da v2.E.1).
