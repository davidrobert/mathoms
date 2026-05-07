---
id: A6c
type: lane
title: "Deletar bridge + legados"
sprint: A6
status: shipped
priority: P0
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a6
  - status/shipped
  - priority/p0
---


# A6c — Deletar bridge + legados


| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6c.1 | Deletar `pipeline/stage_runner_compat.py` | P0 | 30min | ✅ |
| A6c.2 | Deletar `pipeline/materialization_bridge.py` | P0 | 30min | ✅ |
| A6c.3 | Deletar `main(root_dir)` legado dos 6 scripts determinísticos (E1.5c, E3, E4, E5, E5.N, E7) — helpers reutilizados preservados | P0 | 2h | ✅ |
| A6c.4 | Atualizar docs (`ARCHITECTURE.md`, `CHANGELOG.md`, `CLAUDE.md`) | P0 | 1h | ✅ |

**Estimativa:** 1 sessão pequena (~20 testes ajustados).
