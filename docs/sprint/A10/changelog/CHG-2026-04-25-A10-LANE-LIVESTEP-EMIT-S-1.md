---
id: CHG-2026-04-25-A10-LANE-LIVESTEP-EMIT-S-1
type: changelog-entry
date: "2026-04-25"
sprint: A10
adrs: ["[[ADR-119]]"]
commits: ["56d8c42"]
summary: |
  Lane `livestep-emit-stages` E2-llm — concorrente (2026-04-25). - **Lane `livestep-emit-stages` E2-llm — concorrente (2026-04-25):** sétimo emissor migrado para o contrato [ADR-119](DECISIONS.md#adr-119--contrato-livestep-pa
tags:
  - type/changelog-entry
  - sprint/a10
---


# Lane `livestep-emit-stages` E2-llm — concorrente (2026-04-25)

- **Lane `livestep-emit-stages` E2-llm — concorrente (2026-04-25):**
  sétimo emissor migrado para o contrato
  [ADR-119](../../../DECISIONS.md#adr-119--contrato-livestep-para-progresso-de-etapas)
  (após E1.5/E2/E1/E1.5c/E4/E5). Primeira lane com **concorrência
  real**: `pipeline/stages/extract_with_llm.py` usa
  `ThreadPoolExecutor(max_workers=workers)` (1–8 conforme
  `pipeline.json`). Quatro fases por documento dentro do worker
  (`preparing → awaiting_llm → validating → persisting`); thread
  principal emite `finalizing` único após `as_completed`, bypassando
  o throttle. `items_done` é snapshot atômico via
  `_E2LLMProgress` (helper local `threading.Lock` + counter
  compartilhado, increment no main após `fut.result()`, fora do
  crítico). Remove o `emit_stage_activity` inicial "Iniciando
  leitura com IA" — substituído pelo primeiro `preparing` do worker.
  Commit `56d8c42`. Suíte verde: 1464 pipeline + 22 events + 6
  live_progress + 7 e2_llm. Restam **2 lanes** ADR-119 abertas: E0
  (route loop), E3 (reconcile loop, exige instrumentar adapter).
