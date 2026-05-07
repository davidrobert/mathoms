---
id: A6b
type: lane
title: "Ativar `USE_DB_ARTIFACTS=true` + validar end-to-end"
sprint: A6
status: shipped
priority: P0
ship_date: "2026-04-19"
adrs: ["[[ADR-106]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a6
  - status/shipped
  - priority/p0
---


# A6b — Ativar `USE_DB_ARTIFACTS=true` + validar end-to-end


| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6b.1 | Coluna `workspaces.use_db_artifacts_override: bool \| None` (opt-in por workspace) | P0 | 1h | ✅ |
| A6b.2 | `pipeline_task.py` instancia `DBArtifactStore` quando flag ativa; sessão longa com commit após cada stage | P0 | 2h | ✅ |
| A6b.3 | Pipeline completo em workspace piloto com DB ativado; comparar outputs vs disk baseline | P0 | 1-2 dias | ☐ |
| A6b.4 | Script `dev/compare_disk_vs_db.py` — gate ≥99% paridade (disk vs DB, ignora timestamps/order) | P0 | 1 dia | ✅ |
| A6b.5 | Discrepâncias esperadas documentadas em ADR-106: `_meta`, `created_at`, ordem de listas | P0 | 2h | ✅ |

**Checkpoint A6b.1+2+4+5:** ✅ Infraestrutura de ativação pronta. A6b.3 (validação em workspace real) fica para teste humano A6-human.

**Estimativa remanescente:** A6b.3 (1-2 dias de debugging em workspace real).
