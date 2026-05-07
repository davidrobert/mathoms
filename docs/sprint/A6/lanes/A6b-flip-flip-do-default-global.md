---
id: A6b.flip
type: lane
title: "Flip do default global"
sprint: A6
status: shipped
priority: P0
ship_date: "2026-04-23"
adrs: ["[[ADR-118]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a6
  - status/shipped
  - priority/p0
---


# A6b.flip — Flip do default global


| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6b.flip.1 | `USE_DB_ARTIFACTS: bool = True` em `backend/app/core/config.py` | P0 | 5min | ✅ |
| A6b.flip.2 | CI consolidado: remove job `backend-tests-db-artifacts` (continue-on-error) e seta `MATHOMS_USE_DB_ARTIFACTS=true` no único `backend-tests` → bloqueia `all-green` | P0 | 15min | ✅ |
| A6b.flip.3 | Docs atualizadas (`CLAUDE.md`, `SETUP.md`, `ARCHITECTURE.md` §17.3/§ArtifactStore, `STATELESS_AUDIT.md`, `runbooks/cutover.md` header) | P0 | 30min | ✅ |
| A6b.flip.4 | ADR-118 registrada + `CHANGELOG.md [Unreleased]` | P0 | 20min | ✅ |

**Checkpoint A6b.flip:** ✅ Default `True` em `main`; rollback via `MATHOMS_USE_DB_ARTIFACTS=false` + redeploy (runbook `docs/runbooks/cutover.md §Rollback`).
