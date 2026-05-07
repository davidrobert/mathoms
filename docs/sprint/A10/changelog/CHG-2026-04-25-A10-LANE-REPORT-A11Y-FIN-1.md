---
id: CHG-2026-04-25-A10-LANE-REPORT-A11Y-FIN-1
type: changelog-entry
date: "2026-04-25"
sprint: A10
summary: "Lane `report-a11y-finalize` item 6 (2026-04-25). - **Lane `report-a11y-finalize` item 6 (2026-04-25):** gate empírico validado."
tags:
  - type/changelog-entry
  - sprint/a10
---


# Lane `report-a11y-finalize` item 6 (2026-04-25)

- **Lane `report-a11y-finalize` item 6 (2026-04-25):** gate empírico
  validado. Em vez de PR descartável remoto, regressão exercitada
  localmente — `<button>` com `<svg>` filho, sem `aria-label`/texto,
  inserido em `S10SinteseSection.tsx`. Resultado:
  - axe-core: 2 testes `@critical` falharam com `button-name` critical
    (`Element does not have inner text that is visible to screen readers`).
  - tab-order: 1 teste `@critical` falhou em "nenhum focável dentro de
    `[data-report-scope]` sem accessible name".
  - Após `git checkout` da regressão: 28/28 verde de novo.
  - Evidência arquivada em
    [`docs/REPORT_A11Y_GATE_PROOF.md`](REPORT_A11Y_GATE_PROOF.md) (não
    em commit msg, que rota com o tempo).
  - Resíduos da lane: items 3 (snapshots por seção × tema) e 5
    (checklist WCAG operacional).
