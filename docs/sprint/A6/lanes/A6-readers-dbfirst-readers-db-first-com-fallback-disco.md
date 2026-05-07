---
id: A6-readers.dbfirst
type: lane
title: "Readers DB-first com fallback disco"
sprint: A6
status: shipped
priority: P0
ship_date: "2026-04-23"
adrs: ["[[ADR-118]]", "[[ADR-120]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a6
  - status/shipped
  - priority/p0
---


# A6-readers.dbfirst — Readers DB-first com fallback disco


| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| readers.1 | Helper único `backend.app.services.artifact_reader.read_latest_artifact(workspace_id, …)` DB-first, disco fallback | P0 | 2h | ✅ |
| readers.2 | Migração dos 4 readers user-facing impactados (dashboard, transações, extract-JSON IRPF, relatório HTML) | P0 | 3h | ✅ |
| readers.3 | Regressão do incidente 2026-04-23 (workspace caed2272, `940k` vs `4.3M`) coberta por teste | P0 | 1h | ✅ |
| readers.4 | ADR-120 registrada + CHANGELOG `[Unreleased]` | P0 | 30min | ✅ |

**Checkpoint:** ✅ Readers consultam `ArtifactStore` antes de disco; disco preservado p/ CLI dev; rollback ADR-118 continua viável.
