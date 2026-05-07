---
id: CHG-2026-05-05-FEAT-PIPELINE
type: changelog-entry
date: "2026-05-05"
sprint: A10
adrs: ["[[ADR-165]]"]
prs: [52, 55]
summary: |
  feat(pipeline): N3 — IFProjector v2 Monte Carlo + IFConeChart (2026-05-05). - **feat(pipeline): N3 — IFProjector v2 Monte Carlo + IFConeChart (2026-05-05):** Simulação estocástica de Independência Financeira com 3 percentis.
tags:
  - type/changelog-entry
  - sprint/a10
---


# feat(pipeline): N3 — IFProjector v2 Monte Carlo + IFConeChart (2026-05-05)

- **feat(pipeline): N3 — IFProjector v2 Monte Carlo + IFConeChart (2026-05-05):**
  Simulação estocástica de Independência Financeira com 3 percentis.
  Entregue em 2 PRs:
  - **PR-A (#52):** `IFProjector` v2 com `run_monte_carlo_if()`: 1 000
    trajetórias, distribuição normal em retorno (`mean±std`), `IFMonteCarloConfig`
    (tipado, valor object), `MonteCarloIFResult` com `p10`/`p50`/`p90` cone
    paths + `years_to_if` por percentil.
  - **PR-B+C (#55):** Chart.js `IFConeChart` em S7 com 3 bandas coloridas
    P10/P50/P90 + linha "Meta IF"; E5 exporta `monte_carlo_if` key no
    output JSON para consumo frontend. CI re-running, auto-merge habilitado.
  Nota: ADR formal para Monte Carlo (candidato ADR-165) pendente de sign-off
  G0 (financial-planner) — regras de domínio precisam de revisão antes de
  formalizar hipóteses de retorno.
