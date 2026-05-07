---
id: A6-ux.livestep
type: lane
title: "Contrato `LiveStep`"
sprint: A6
status: shipped
priority: P0
ship_date: "2026-04-23"
adrs: ["[[ADR-119]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a6
  - status/shipped
  - priority/p0
---


# A6-ux.livestep — Contrato `LiveStep`


| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| livestep.1 | `LiveStep` payload formalizado (`items_done`, `items_total`, `current_item`, `phase`) + helper `pipeline.live_progress.emit_item_progress` com throttle | P0 | 2h | ✅ |
| livestep.2 | Primitivo frontend `<LiveStepProgress/>` render uniforme | P0 | 1h | ✅ |
| livestep.3 | Primeira adoção: E2-extratos + E2-faturas (sub-progresso "Arquivo N/M · nome.pdf") | P0 | 1h | ✅ |
| livestep.4 | ADR-119 registrada + CHANGELOG `[Unreleased]` | P0 | 30min | ✅ |
| livestep.5 | Migração das stages iterativas restantes (E1, E1.5, E1.5c, E2-llm, E3, E0, E4, E5) | P1 | 3h | ✅ 2026-04-25 |

**Checkpoint:** ✅ Saga concluída 2026-04-25 — **todas as 9 stages instrumentáveis** emitem `emit_item_progress` (ADR-119): E1.5 (`3bc9d25`), E2 (`09858df`), E1 + E1.5c (`3d819db`), E4 + E5 (`2a6d5e5`), E2-llm (`56d8c42`), E3 (`e6e9ebd`), E0 (`26225b1`). Zero callers de `emit_stage_activity` antigo em `pipeline/`/`scripts/`. Stages rápidas (`unlock_documents`, `audit_documents`, `validate_cross`, `apply_review`) ficam sem emit intencionalmente — throttle de 250ms engoliria preparing+finalizing.
