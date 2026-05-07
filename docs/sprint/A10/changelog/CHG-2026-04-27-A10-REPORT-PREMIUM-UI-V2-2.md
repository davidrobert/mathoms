---
id: CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-2
type: changelog-entry
date: "2026-04-27"
sprint: A10
adrs: ["[[ADR-148]]"]
commits: ["384b5bf", "0576b11", "076d8f3"]
summary: |
  Report Premium UI v2.8 — comparisons + changelog ativos no relatório ✅ (2026-04-27). - **Report Premium UI v2.8 — comparisons + changelog ativos no relatório ✅ (2026-04-27):** Conecta o `SnapshotChangelogBuilder` (v2.D.1 · [ADR-148](DECISIONS.md
tags:
  - type/changelog-entry
  - sprint/a10
---


# Report Premium UI v2.8 — comparisons + changelog ativos no relatório ✅ (2026-04-27)

- **Report Premium UI v2.8 — comparisons + changelog ativos no relatório ✅ (2026-04-27):**
  Conecta o `SnapshotChangelogBuilder` (v2.D.1 · [ADR-148](DECISIONS.md#adr-148--snapshotchangelogbuilder-comparações-mês-a-mês-de-relatório))
  ao endpoint + UI. 12 placeholders YAML em S1/S2/S3/T2/T3/T5 flippados de
  `enabled:false → true` (commit `384b5bf`); `GET /reports/{id}/data` injeta
  `comparisons: ComparisonItemRead[] | null` + `changelog: ChangelogEntryRead[] | null`
  top-level via `snapshot_pair_loader` + `build_comparison()` (commit `0576b11`);
  novos componentes React `ComparisonItemsBlock` (tabela antes→depois com sinal
  ▲▼•), `SnapshotChangelogList` (lista com borda colorida por delta_signal) e
  `SectionSnapshotDiff` wrapper que filtra por sectionId (commit `076d8f3`).
  `conclusionUtils.deriveSectionSummary` ganha 3 camadas: LLM v2.9 prioritário >
  template + changelog summary determinístico > template puro. **Caveats:**
  (a) débito alheio em origin/main pós-v2.9 — todos os 19 specs `@critical` de
  `/reports/[id]` quebram com erro genérico "Cannot read properties of undefined"
  (verificado em worktree limpa de origin/main); spec novo `snapshot-changelog.@critical.spec.ts`
  marcado `test.skip` com plano de unfreeze. (b) baselines visuais não regenerados
  nesta lane — próxima rodada de visual gate vai precisar `update_visual_baselines=true`
  para S1/S2/S3/T2/T3/T5 (componentes novos renderizam onde antes era nada).
  Onda D do plano Report Premium fechada (2/2). v2.D.1.1 segue aberta como
  débito de copy review pelo product-designer.
