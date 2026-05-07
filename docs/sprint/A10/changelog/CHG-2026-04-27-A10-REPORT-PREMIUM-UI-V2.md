---
id: CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2
type: changelog-entry
date: "2026-04-27"
sprint: A10
commits: ["adc3a15"]
summary: |
  Report Premium UI v2.2b completa — modo USA re-habilitado + 8 baselines U1-U4 ✅ (2026-04-27). - **Report Premium UI v2.2b completa — modo USA re-habilitado + 8 baselines U1-U4 ✅ (2026-04-27):** Decisão de produto autorizou retomar o modo USA.
tags:
  - type/changelog-entry
  - sprint/a10
---


# Report Premium UI v2.2b completa — modo USA re-habilitado + 8 baselines U1-U4 ✅ (2026-04-27)

- **Report Premium UI v2.2b completa — modo USA re-habilitado + 8 baselines U1-U4 ✅ (2026-04-27):**
  Decisão de produto autorizou retomar o modo USA. Reverte parcialmente
  `adc3a15` ("ocultar USA temporariamente"): U1-U4 `enabled: true` no
  `config/report_layout.yaml`, bloco `navigation.usa` descomentado, codegen
  TS+Pydantic regerados; `ReportActions.VISIBLE_MODES` e `ModeToggle` voltam
  a expor a aba "EUA" no tablist do header; `ReportShell.test` re-afirma
  `getByRole("tab", { name: "EUA" })`. Spec visual `sections.snapshots.visual.spec.ts`
  troca `test.describe.skip("Snapshots — modo USA")` por `test.describe(...)`;
  helper `setupReport(..., "usa")` (já entregue em v2.2b parcial via deep-link
  `?mode=usa`) cobre os 4 sections × {light,dark}. Run CI dispara
  `update_visual_baselines=true` para popular as 8 baselines pendentes
  (U1-U4 × {light,dark}) em `sections.snapshots.visual.spec.ts-snapshots/`.
  Vitest 668/668 verde; baseline drift `code-style-baseline` + `ruff-format`
  pendentes em outras lanes (Lane 5) — não tocados.
