---
id: A5f
type: lane
title: "E1.5c Caminho B"
sprint: A6
status: shipped
priority: P0
ship_date: "2026-04-19"
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a6
  - status/shipped
  - priority/p0
---


# A5f — E1.5c Caminho B


| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A5f.1 | `scripts/e15_consolidate.main_with_store(ctx)` lê baseline via store, invoca `consolidate()` legado, grava E1.5c via store | P0 | ~30min | ✅ |
| A5f.2 | `pipeline/stages/e15c.py` chama `main_with_store` direto, sem `stage_runner_compat`; preserva skip gracioso free tier | P0 | 15min | ✅ |
| A5f.3 | Golden de paridade `main(root_dir)` vs `main_with_store(ctx)` em workspace sintético | P0 | 20min | ✅ |
| A5f.4 | Critério estrutural: `grep stage_runner_compat pipeline/stages/` = zero | P0 | 5min | ✅ |

**Checkpoint A5f:** ✅ todos os 7 stages determinísticos no Caminho B; bridge com zero clientes vivos no wrapper.
