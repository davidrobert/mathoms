---
id: CHG-2026-04-29-A10-DIRE-O-E-ONDA-1-M2-S
type: changelog-entry
date: "2026-04-29"
sprint: A10
adrs: ["[[ADR-154]]"]
summary: |
  Direção E — Onda 1 M2 (sunset legacy `report_collab`, 2026-04-29). - **Direção E — Onda 1 M2 (sunset legacy `report_collab`, 2026-04-29):** M2 da Onda 1 entregue como **estratégia conservadora** — RENAME + endpoints 410 Gone em
tags:
  - type/changelog-entry
  - sprint/a10
---


# Direção E — Onda 1 M2 (sunset legacy `report_collab`, 2026-04-29)

- **Direção E — Onda 1 M2 (sunset legacy `report_collab`, 2026-04-29):**

  M2 da Onda 1 entregue como **estratégia conservadora** — RENAME +
  endpoints 410 Gone em vez do DROP direto previsto no
  [ADR-154](DECISIONS.md#adr-154--fusão-kanbanitem-em-task--migração-reportnotes-para-workspacenotes-direção-e--onda-1).
  Razão: M1 e M2 no mesmo dia (2026-04-29); janela de 7 dias de
  validação não cumprida; rename é reversível em segundos via
  downgrade, drop é irreversível sem backup. Drop final fica para PR
  M3 (sprint+2, ~2026-05-13).

  **Backend:**
  - Migration `a0b1c2d3e4f5_adr154_m2_sunset_legacy.py`:
    `op.rename_table("kanban_items", "_legacy_kanban_items")` +
    `op.rename_table("report_notes", "_legacy_report_notes")`.
    Downgrade reverte.
  - `backend/app/api/reports_collab.py` reescrito: 6 rotas (notes
    GET/PUT + kanban GET/POST/PATCH/DELETE) retornam **HTTP 410 Gone**
    com payload `{code, message, migrated_to}` apontando para
    `/workspaces/{ws}/notes` e `/workspaces/{ws}/tasks`.
  - `backend/app/models/report_collab.py`: `__tablename__` atualizado
    para `_legacy_*`; docstring marca como deprecated. Models
    permanecem porque `purge_reports.py` ainda usa em DELETE.
  - `backend/tests/test_reports_collab_api.py` reescrito: 6 testes
    novos validam 410 Gone + payload com código + ADR-154 reference.

  **Frontend:**
  - `frontend/src/lib/api/reports.ts`: 6 funções legadas
    (`getReportNotes`, `putReportNotes`, `listKanbanItems`,
    `createKanbanItem`, `updateKanbanItem`, `deleteKanbanItem`)
    marcadas com `@deprecated` JSDoc apontando para os hooks novos.
    Tipos preservados.

  **Documentação:**
  - [ADR-154](DECISIONS.md#adr-154--fusão-kanbanitem-em-task--migração-reportnotes-para-workspacenotes-direção-e--onda-1)
    ganha banner "M2 sunset entregue" + reescreve seção "Migration
    M1 → M2 → M3" (3 fases agora).
  - `docs/reference/RUNBOOK.md` atualizado: localStorage `notas:*` e `kanban:*`
    chaves agora marcadas como "endpoints retornam 410 Gone desde
    ADR-154 M2".
