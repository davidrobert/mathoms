"""Suggestions API — router fino (ADR-101 R15/R16 · ADR-153).

Endpoints sob ``/workspaces/{workspace_id}/...`` cobrem dois recursos:

- ``/suggestions/...`` — CRUD-like sobre Suggestion: list/get/count +
  transições accept/modify/dismiss.
- ``/reports/{report_id}/regenerate-suggestions`` — re-roda generator
  E5 sobre o snapshot do relatório, persiste novas drafts respeitando
  dedup. Idempotente.

Erros de domínio (NotFound, Conflict, Validation) traduzidos para HTTP
por handlers globais em ``main.py``.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.suggestions import (
    accept_suggestion as _uc_accept_suggestion,
)
from backend.app.application.suggestions import (
    count_suggestions as _uc_count_suggestions,
)
from backend.app.application.suggestions import (
    dismiss_suggestion as _uc_dismiss_suggestion,
)
from backend.app.application.suggestions import (
    get_suggestion as _uc_get_suggestion,
)
from backend.app.application.suggestions import (
    list_suggestions as _uc_list_suggestions,
)
from backend.app.application.suggestions import (
    modify_suggestion as _uc_modify_suggestion,
)
from backend.app.application.suggestions import (
    regenerate_for_report as _uc_regenerate_for_report,
)
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.repositories.decision_repository import DecisionRepository
from backend.app.repositories.suggestion_repository import SuggestionRepository
from backend.app.schemas.dto.suggestion import (
    AcceptSuggestionCommand,
    DismissSuggestionCommand,
    ModifySuggestionCommand,
    RegenerateSuggestionsCommand,
    SuggestionCountResponse,
    SuggestionListResponse,
    SuggestionRegenerateResponse,
    SuggestionResponse,
)

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["suggestions"])


def _suggestion_repo(db: AsyncSession = Depends(get_db)) -> SuggestionRepository:
    return SuggestionRepository(db)


def _decision_repo(db: AsyncSession = Depends(get_db)) -> DecisionRepository:
    return DecisionRepository(db)


def _actor_id(user: User) -> str:
    return f"user:{user.id}"


@router.get("/suggestions", response_model=SuggestionListResponse)
async def list_suggestions(
    status_filter: Optional[str] = Query(None, alias="status"),
    workspace: Workspace = Depends(get_current_workspace),
    repo: SuggestionRepository = Depends(_suggestion_repo),
) -> SuggestionListResponse:
    return await _uc_list_suggestions(workspace.id, status=status_filter, repo=repo)


@router.get("/suggestions/count", response_model=SuggestionCountResponse)
async def count_suggestions(
    status_filter: Optional[str] = Query("Pendente", alias="status"),
    workspace: Workspace = Depends(get_current_workspace),
    repo: SuggestionRepository = Depends(_suggestion_repo),
) -> SuggestionCountResponse:
    return await _uc_count_suggestions(workspace.id, status=status_filter, repo=repo)


@router.get("/suggestions/{suggestion_id}", response_model=SuggestionResponse)
async def get_suggestion(
    suggestion_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    repo: SuggestionRepository = Depends(_suggestion_repo),
) -> SuggestionResponse:
    return await _uc_get_suggestion(workspace.id, suggestion_id, repo=repo)


@router.post(
    "/suggestions/{suggestion_id}/accept",
    response_model=SuggestionResponse,
    dependencies=[Depends(require_write_role)],
)
async def accept_suggestion(
    suggestion_id: str,
    payload: AcceptSuggestionCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    suggestion_repo_dep: SuggestionRepository = Depends(_suggestion_repo),
    decision_repo_dep: DecisionRepository = Depends(_decision_repo),
) -> SuggestionResponse:
    response = await _uc_accept_suggestion(
        payload,
        workspace_id=workspace.id,
        suggestion_id=suggestion_id,
        suggestion_repo=suggestion_repo_dep,
        decision_repo=decision_repo_dep,
        actor=_actor_id(user),
        db=db,  # ADR-163 — context_snapshot do relatório-fonte
    )
    await db.commit()
    return response


@router.post(
    "/suggestions/{suggestion_id}/modify",
    response_model=SuggestionResponse,
    dependencies=[Depends(require_write_role)],
)
async def modify_suggestion(
    suggestion_id: str,
    payload: ModifySuggestionCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    suggestion_repo_dep: SuggestionRepository = Depends(_suggestion_repo),
    decision_repo_dep: DecisionRepository = Depends(_decision_repo),
) -> SuggestionResponse:
    response = await _uc_modify_suggestion(
        payload,
        workspace_id=workspace.id,
        suggestion_id=suggestion_id,
        suggestion_repo=suggestion_repo_dep,
        decision_repo=decision_repo_dep,
        actor=_actor_id(user),
        db=db,  # ADR-163 — context_snapshot do relatório-fonte
    )
    await db.commit()
    return response


@router.post(
    "/suggestions/{suggestion_id}/dismiss",
    response_model=SuggestionResponse,
    dependencies=[Depends(require_write_role)],
)
async def dismiss_suggestion(
    suggestion_id: str,
    payload: DismissSuggestionCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: SuggestionRepository = Depends(_suggestion_repo),
) -> SuggestionResponse:
    response = await _uc_dismiss_suggestion(
        payload,
        workspace_id=workspace.id,
        suggestion_id=suggestion_id,
        repo=repo,
    )
    await db.commit()
    return response


@router.post(
    "/reports/{report_id}/regenerate-suggestions",
    response_model=SuggestionRegenerateResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_write_role)],
)
async def regenerate_suggestions_for_report(
    report_id: str,
    payload: RegenerateSuggestionsCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: SuggestionRepository = Depends(_suggestion_repo),
) -> SuggestionRegenerateResponse:
    del payload  # placeholder para evolução futura (filtros, force, etc.)
    response = await _uc_regenerate_for_report(
        workspace_id=workspace.id,
        report_id=report_id,
        db=db,
        repo=repo,
    )
    await db.commit()
    return response
