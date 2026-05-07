---
id: CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-4
type: changelog-entry
date: "2026-04-27"
sprint: A10
commits: ["adc3a15", "d4e0dfe", "029c3d9", "0558ea3", "db6cf6f", "35eee5f", "a534e9d"]
summary: |
  Report Premium UI v2.2b — fix `clickMode()` + 12 baselines Tático ✅ parcial (2026-04-27). - **Report Premium UI v2.2b — fix `clickMode()` + 12 baselines Tático ✅ parcial (2026-04-27):** Resíduo da v2.2 fechado parcialmente — Tático populado, USA bloqueado por decisão de produto.
tags:
  - type/changelog-entry
  - sprint/a10
---


# Report Premium UI v2.2b — fix `clickMode()` + 12 baselines Tático ✅ parcial (2026-04-27)

- **Report Premium UI v2.2b — fix `clickMode()` + 12 baselines Tático ✅ parcial (2026-04-27):**
  Resíduo da v2.2 fechado parcialmente — Tático populado, USA bloqueado
  por decisão de produto.

  **Diagnose:** `clickMode()` em `sections.snapshots.visual.spec.ts:77-83`
  retornava `false` silenciosamente para `/Tático/i` e `/USA|EUA/i` por
  dois motivos sobrepostos: (1) o toggle real é `ReportActions` (não o
  `ModeToggle` legado), com `<button role="tab">` envolto em
  `<TooltipTrigger>` — o label "Tático"/"EUA" fica fora do `<button>`,
  então `getByRole("button", { name: ... })` não casa; (2) modo `usa`
  foi removido de `VALID_MODES` em `adc3a15` (decisão de produto:
  ocultar USA temporariamente), então `?mode=usa` caía no default e a
  aba "EUA" também sumiu da UI.

  **Fix:** `setupReport(page, theme, mode)` aceita `mode` opcional e
  navega via deep-link `?mode=tatico|usa` em vez de click —
  `ReportModeProvider` já lê `searchParams.get("mode")` na montagem.
  `usa` re-incluído em `VALID_MODES` (apenas no `Set`; toggle UI
  permanece hidden — link compartilhável era a intenção do TEMP). Commit
  `d4e0dfe`.

  **Baselines Tático:** run [25002843680](https://github.com/davidrobert/mathoms/actions/runs/25002843680)
  com `gh workflow run CI -f run_visual=true -f update_visual_baselines=true`
  gerou 12 PNGs (T1-T6 × {light,dark}); copiadas do artefato
  `report-visual-baselines-generated` para
  `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts-snapshots/`.
  Commit `029c3d9`.

  **USA pendente (8 baselines):** U1-U4 têm `enabled: false` em
  `config/report_layout.yaml` (commit `adc3a15`). `ReportShell` filtra
  por `enabledSections` antes de montar `<section>`, então as seções
  não existem no DOM nem em prod nem com mock. Re-habilitar no YAML
  mudaria runtime de produção (USA voltaria a aparecer); fora de
  escopo. Marcado `test.describe.skip()` com motivação inline; quando
  produto retomar, basta flip dos 4 `enabled: false` + remover TEMP em
  `ReportActions.VISIBLE_MODES` + trocar `skip` por `describe` + nova
  run `update_visual_baselines`. Helper já está pronto.

  **Regressão pre-existente fora de escopo:** 28 baselines estratégicas
  + APP + cover (commit `0558ea3` em 2026-04-26) "passavam" no run
  #24952539088 mas "skipam" em [25002843680](https://github.com/davidrobert/mathoms/actions/runs/25002843680)
  com `count() === 0` para `section#S1[data-report-section]`. Mesmo
  `setupReport()`, mesma URL — não causada por v2.2b. Commits
  candidatos: `db6cf6f` (cover identity v2.F.3b), `35eee5f` (Hero out
  of S1 v2.F.2), `a534e9d` (header refactor). Investigar em lane
  separada antes de re-rodar gate empírico.
