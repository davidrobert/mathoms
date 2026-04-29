"""Report collaboration — DEPRECATED (Direção E · Onda 1 · M2 sunset).

Histórico (ADR-123 · Fase 6.5): endpoints sob ``/workspaces/{ws_id}/
reports/{report_id}/{notes|kanban[/item_id]}`` para CRUD de Notas (T6) +
Kanban (T3) do Modo Tático.

**Sunset (ADR-154 · Direção E · Onda 1 · M2 — 2026-04-29):** Modo Tático
foi removido em ADR-151 (Onda 3); aggregates `KanbanItem` e
`ReportNotes` foram migrados em ADR-154 M1 para `Task` (com
`board_column`/`board_order`/`origin_report_id`) e `WorkspaceNotes`
respectivamente. Tabelas legadas renomeadas para `_legacy_*` (drop
final em PR M3, sprint+2). Frontend não consome mais estes endpoints
desde a Onda 3 (commit `cf14af6`).

Todas as rotas retornam **HTTP 410 Gone** com payload informativo
apontando para os novos endpoints. Manter o roteador (vs simplesmente
deletar) preserva mensagens claras para clientes externos cegos
durante a janela de sunset.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

router = APIRouter(
    prefix="/workspaces/{workspace_id}/reports/{report_id}",
    tags=["report-collab-legacy"],
)


_GONE_NOTES = {
    "code": "report_notes_gone",
    "message": (
        "Endpoint deprecated (ADR-154 M2 · 2026-04-29). Notas de "
        "relatório foram migradas para WorkspaceNotes — consultar "
        "/workspaces/{ws_id}/notes."
    ),
    "migrated_to": "/workspaces/{workspace_id}/notes",
}

_GONE_KANBAN = {
    "code": "report_kanban_gone",
    "message": (
        "Endpoint deprecated (ADR-154 M2 · 2026-04-29). Kanban de "
        "relatório foi fundido em Task — consultar /workspaces/{ws_id}/"
        "tasks com board_column/board_order."
    ),
    "migrated_to": "/workspaces/{workspace_id}/tasks",
}


def _gone(detail: dict) -> HTTPException:
    return HTTPException(status_code=status.HTTP_410_GONE, detail=detail)


@router.get("/notes")
async def get_notes_gone(
    workspace_id: Annotated[str, Path()],
    report_id: Annotated[str, Path()],
) -> None:
    raise _gone(_GONE_NOTES)


@router.put("/notes")
async def put_notes_gone(
    workspace_id: Annotated[str, Path()],
    report_id: Annotated[str, Path()],
) -> None:
    raise _gone(_GONE_NOTES)


@router.get("/kanban")
async def list_kanban_gone(
    workspace_id: Annotated[str, Path()],
    report_id: Annotated[str, Path()],
) -> None:
    raise _gone(_GONE_KANBAN)


@router.post("/kanban")
async def create_kanban_gone(
    workspace_id: Annotated[str, Path()],
    report_id: Annotated[str, Path()],
) -> None:
    raise _gone(_GONE_KANBAN)


@router.patch("/kanban/{item_id}")
async def update_kanban_gone(
    workspace_id: Annotated[str, Path()],
    report_id: Annotated[str, Path()],
    item_id: Annotated[str, Path()],
) -> None:
    raise _gone(_GONE_KANBAN)


@router.delete("/kanban/{item_id}")
async def delete_kanban_gone(
    workspace_id: Annotated[str, Path()],
    report_id: Annotated[str, Path()],
    item_id: Annotated[str, Path()],
) -> None:
    raise _gone(_GONE_KANBAN)
