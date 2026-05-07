---
id: CHG-2026-05-05-FEAT-DB
type: changelog-entry
date: "2026-05-05"
sprint: A10
adrs: ["[[ADR-154]]"]
summary: |
  feat(db): B7 M3 — DROP _legacy_kanban_items + _legacy_report_notes + model cleanup (ADR-154) (2026-05-05). - **feat(db): B7 M3 — DROP _legacy_kanban_items + _legacy_report_notes + model cleanup (ADR-154) (2026-05-05):** Migration final após 7 dias de validação pós-M2 (2026-04-29).
tags:
  - type/changelog-entry
  - sprint/a10
---


# feat(db): B7 M3 — DROP _legacy_kanban_items + _legacy_report_notes + model cleanup (ADR-154) (2026-05-05)

- **feat(db): B7 M3 — DROP _legacy_kanban_items + _legacy_report_notes + model cleanup (ADR-154) (2026-05-05):**
  Migration final após 7 dias de validação pós-M2 (2026-04-29). `_legacy_kanban_items` e
  `_legacy_report_notes` DROPadas. Cleanup de todos os artefatos dependentes:
  - `b7c8d9e0f1a2_adr154_m3_drop_legacy_collab_tables.py`: DROP `_legacy_kanban_items` + `_legacy_report_notes`
  - `backend/app/models/report_collab.py`: modelos `KanbanItem`/`ReportNotes` removidos
  - `backend/app/schemas/report_collab.py`: schemas `ReportNotesRead/Write`, `KanbanItem*` removidos
  - `backend/app/services/internal_ops/purge_reports.py`: import + `_delete_report_collab()` removidos
  - `backend/tests/internal_ops/test_purge_reports.py`: helper `_add_report_collab` + asserts collab removidos
  - `backend/tests/test_kanban_to_task_backfill.py`: teste de paridade M1 removido (tabelas não existem mais)
  - `backend/tests/test_alembic_guardrails.py`: `IRREVERSIBLE_MIGRATIONS` + lógica de floor parcial para suportar DROP sem downgrade
  - `frontend/src/lib/api/reports.ts`: 6 funções deprecated (`getReportNotes`, `putReportNotes`, `listKanbanItems`, `createKanbanItem`, `updateKanbanItem`, `deleteKanbanItem`) + tipos (`ReportNotesPayload`, `KanbanItem*`) removidos
  - `docs/reference/DB_SCHEMA_REFERENCE.md` regenerado — tabelas `_legacy_*` ausentes
