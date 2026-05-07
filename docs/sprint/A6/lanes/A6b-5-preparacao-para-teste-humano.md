---
id: A6b.5
type: lane
title: "Preparação para teste humano (ADR-103)"
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


# A6b.5 — Preparação para teste humano (ADR-103)


| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6b.5.1 | `docker-compose.smoke.yml` (Redis) + `Makefile` (`smoke-up/down/reset/seed/logs` + `test/lint/format`) | P0 | 4h | ✅ |
| A6b.5.2 | `backend/app/scripts/seed_smoke.py` (2 users + 2 workspaces + copia fixtures p/ inbox) | P0 | 3h | ✅ |
| A6b.5.3 | `tests/fixtures/smoke_inbox/` (5 CSVs: 2 extratos C6, 1 dup, 1 Nubank extrato, 1 Nubank fatura + `life_plan_goals.md` + `ambiguous_document-smoke.txt` + README) | P0 | 6h | ✅ |
| A6b.5.4 | `docs/reference/SMOKE_TEST_HUMAN.md` — runbook completo (setup + 46 checks + troubleshooting + template decisão A6c) | P0 | 4h | ✅ |
| A6b.5.5 | `GET /health` inclui `artifact_store_mode: "disk"\|"db"` (A6b indicator) | P0 | 3h | ✅ |
| A6b.5.6 | Free-tier: pipeline já emite `skipped_free_tier` nos stages LLM; banner na UI pendente (F7B) | P0 | 2h | 🚧 |

**Checkpoint A6b.5:** ✅ `make smoke-up && make smoke-seed` → sistema utilizável em <2min.

**Nota A6b.5.6**: Logs de `skipped_free_tier` já existem no pipeline desde F5. Banner visual na UI fica para F7B (security hardening) junto com outros elementos de UX de produção.
