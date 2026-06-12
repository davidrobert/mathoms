---
id: CHG-2026-06-12-REMOVE-HISTORICO-CICLOS
type: changelog-entry
date: "2026-06-12"
sprint: A25
lane: null
prs: [617, 618]
breaking: false
summary: "Remove card 'Histórico de Ciclos' do Apêndice E do relatório React — duplicata single-pair do data.changelog (ADR-148) já exibido via SectionSnapshotDiff, com rótulo enganoso em apêndice forward-looking. Backlog W5 (série temporal multi-ciclo de KPIs) registrado no plano SNAPSHOT_CHANGELOG_V3 para a lacuna metodológica real."
tags:
  - type/changelog-entry
  - area/report
  - sprint/a25
---

# Remoção do card "Histórico de Ciclos" (Apêndice E)

Execução de [[TRACK-remove-historico-ciclos-app-e]] (decisão de
2026-06-12, revisão `product-designer` + `financial-planner` +
`product-manager` + `information-architect`).

- **#617 (docs):** track de remoção + seção W5 (backlog bloqueado por
  dado) no plano [[PLAN-snapshot-changelog-v3]].
- **#618 (frontend):** remove o `ReportCard` de `ApendiceESection` +
  `toEntryView` local + imports órfãos; copy fallback APP_E atualizada
  em `conclusionUtils.ts`; teste anti-regressão de duplicação impede o
  card de voltar. `SnapshotChangelogList`/wire permanecem vivos até
  W4-T07 ([[ADR-190]]). Baselines visuais APP-E regeneradas no CI.
