---
id: CHG-2026-04-25-A10-LANE-LIVESTEP-EMIT-S-3
type: changelog-entry
date: "2026-04-25"
sprint: A10
adrs: ["[[ADR-119]]"]
commits: ["3bc9d25", "09858df", "3d819db"]
summary: |
  Lane `livestep-emit-stages` E1 + E1.5c — mecânicas (2026-04-25). - **Lane `livestep-emit-stages` E1 + E1.5c — mecânicas (2026-04-25):** terceiro e quarto emissores migrados para o contrato [ADR-119](DECISIONS.md#adr-119--cont
tags:
  - type/changelog-entry
  - sprint/a10
---


# Lane `livestep-emit-stages` E1 + E1.5c — mecânicas (2026-04-25)

- **Lane `livestep-emit-stages` E1 + E1.5c — mecânicas (2026-04-25):**
  terceiro e quarto emissores migrados para o contrato
  [ADR-119](../../../DECISIONS.md#adr-119--contrato-livestep-para-progresso-de-etapas)
  (após E1.5 em `3bc9d25` e E2 em `09858df`). Stages **single-batch**
  (não-loop):
  - **E1 — `pipeline/stages/extract_members.py`:** chamada LLM única
    em batch (todos docs pessoais combinados num prompt). 5 fases
    sequenciais (`preparing → awaiting_llm → validating → persisting →
    finalizing`), `items_total=1`, `current_item="N documento(s) pessoais"`.
  - **E1.5c — `pipeline/stages/consolidate_baseline.py`:** stage
    determinística rápida (sem LLM, sem loop, <1s). Apenas
    `preparing` + `finalizing` — granularidade maior é desnecessária
    (throttle 250ms engoliria emits intermediários).
  Commit `3d819db`. Suíte verde: 1464 pipeline + 22 events.
