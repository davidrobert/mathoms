"""CategorizationRules API — learning loop CRUD + preview + async apply (ADR-186/188 · A12 P3)."""

from __future__ import annotations

import uuid
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import PreconditionFailedError
from backend.app.application.categorization import (
    rule_management_service,
    rule_preview_service,
)
from backend.app.application.categorization._caps import SYNC_APPLY_THRESHOLD
from backend.app.application.categorization.rule_management_service import (
    ApplyTooLargeError,
    HardCapExceededError,
    RuleAlreadyExistsError,
)
from backend.app.core import database as _db_module
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.repositories.config_blob_repository import ConfigBlobRepository
from backend.app.schemas.dto.categorization_rule import (
    AsyncRuleCreatedResponse,
    CategorizationRuleCreate,
    CategorizationRuleResponse,
    RuleApplyStatusResponse,
    RulePreviewRequest,
    RulePreviewResponse,
    RulesListResponse,
)
from backend.app.services import rule_apply_state
from backend.app.services.config_defaults import ConfigDefaultsLoader
from backend.app.services.feature_flags_service import is_enabled
from backend.app.services.transaction_service import load_transactions
from backend.app.services.transfer_detector_resolver import (
    resolve_internal_transfer_detector,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/categorization/rules",
    tags=["categorization", "learning-loop"],
)


async def _require_learning_loop(
    workspace_id: str,
    db: AsyncSession,
) -> None:
    """Gate via feature flag — raise ``PreconditionFailedError`` (handler 403 global, ADR-188 PR3 R2)."""
    if not await is_enabled(workspace_id, "learning_loop_enabled", db=db):
        raise PreconditionFailedError(
            "Learning loop não habilitado para este workspace. "
            "Solicite ativação ao admin (gate dogfood ADR-186 §D6).",
            code="learning_loop_disabled",
        )


async def _resolve_detector(workspace_id: str, db: AsyncSession):
    """Reutiliza o resolver A11 (DB-first → defaults globais)."""
    repo = ConfigBlobRepository(db)
    defaults = ConfigDefaultsLoader()
    return await resolve_internal_transfer_detector(workspace_id, repo=repo, defaults=defaults)


def _load_transactions_for(workspace_id: str) -> list:
    """Carrega transações E4 fora da sync session do CRUD (evita nested-session rollback)."""
    return load_transactions(workspace_id, str(settings.STORAGE_ROOT / workspace_id))


def _http_422_hard_cap(exc: HardCapExceededError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": "hard_cap_exceeded",
            "message": str(exc),
            "current": exc.current,
            "limit": exc.limit,
        },
    )


def _http_409_already_exists(exc: RuleAlreadyExistsError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "rule_already_exists",
            "message": str(exc),
            "existing_rule_id": exc.existing_rule_id,
        },
    )


def _http_422_apply_too_large(exc: ApplyTooLargeError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": "apply_too_large_for_sync",
            "message": str(exc),
            "expected_overrides": exc.expected_overrides,
        },
    )


def _preview_rule_sync(
    *,
    workspace_id: str,
    body: RulePreviewRequest,
    detector,
    transactions: list,
    sync_db,
) -> RulePreviewResponse:
    soft_cap_reached = rule_management_service.soft_cap_reached(
        workspace_id=workspace_id, db=sync_db
    )
    return rule_preview_service.preview_rule(
        workspace_id=workspace_id,
        keyword=body.keyword,
        target_category=body.target_category,
        period_window=body.period_window,
        transactions=transactions,
        db=sync_db,
        detector=detector,
        soft_cap_reached=soft_cap_reached,
    )


def _list_rules_sync(
    *,
    workspace_id: str,
    enabled: Optional[bool],
    page: int,
    page_size: int,
    sync_db,
) -> RulesListResponse:
    from sqlalchemy import select as sa_select

    ws_row = sync_db.execute(sa_select(Workspace).where(Workspace.id == workspace_id)).scalar_one()
    return rule_management_service.list_rules(
        workspace=ws_row,
        enabled=enabled,
        page=page,
        page_size=page_size,
        db=sync_db,
    )


def _create_rule_sync(
    *,
    workspace_id: str,
    body: CategorizationRuleCreate,
    user_id: str,
    detector,
    transactions: list,
    sync_db,
) -> CategorizationRuleResponse:
    from sqlalchemy import select as sa_select

    ws_row = sync_db.execute(sa_select(Workspace).where(Workspace.id == workspace_id)).scalar_one()
    try:
        return rule_management_service.create_rule(
            workspace=ws_row,
            keyword=body.keyword,
            target_category=body.target_category,
            priority=body.priority,
            user_id=user_id,
            detector=detector,
            transactions=transactions,
            db=sync_db,
        )
    except HardCapExceededError as exc:
        raise _http_422_hard_cap(exc) from exc
    except RuleAlreadyExistsError as exc:
        raise _http_409_already_exists(exc) from exc
    except ApplyTooLargeError as exc:
        raise _http_422_apply_too_large(exc) from exc


def _persist_rule_async(
    *, workspace_id: str, body: CategorizationRuleCreate, user_id: str, sync_db
):
    """Cria regra sem apply — traduz erros tipados em HTTPException."""
    from sqlalchemy import select as sa_select

    ws_row = sync_db.execute(sa_select(Workspace).where(Workspace.id == workspace_id)).scalar_one()
    try:
        return rule_management_service.create_rule_async(
            workspace=ws_row,
            keyword=body.keyword,
            target_category=body.target_category,
            priority=body.priority,
            user_id=user_id,
            db=sync_db,
        )
    except HardCapExceededError as exc:
        raise _http_422_hard_cap(exc) from exc
    except RuleAlreadyExistsError as exc:
        raise _http_409_already_exists(exc) from exc


def _dispatch_apply_celery(workspace_id: str, rule_id: str) -> str:
    """Mark pending + .delay() — retorna job_id."""
    job_id = str(uuid.uuid4())
    rule_apply_state.mark_pending(workspace_id=workspace_id, rule_id=rule_id, job_id=job_id)
    from backend.app.tasks.categorization_apply import apply_rule_retroactive_task

    apply_rule_retroactive_task.delay(workspace_id, rule_id)
    return job_id


def _create_rule_async_dispatch(
    *, workspace_id: str, body: CategorizationRuleCreate, user_id: str, sync_db
) -> AsyncRuleCreatedResponse:
    """Cria regra sem apply + dispara Celery task (ADR-188 PR3 escopo 1)."""
    rule = _persist_rule_async(
        workspace_id=workspace_id, body=body, user_id=user_id, sync_db=sync_db
    )
    job_id = _dispatch_apply_celery(workspace_id, rule.id)
    return AsyncRuleCreatedResponse(
        rule_id=rule.id,
        workspace_id=workspace_id,
        status="pending",
        job_id=job_id,
        message="Aplicação retroativa iniciada em background. Use GET /apply-status para acompanhar.",
    )


@router.post(
    "/preview",
    response_model=RulePreviewResponse,
    status_code=status.HTTP_200_OK,
)
async def preview_rule_endpoint(
    body: RulePreviewRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> RulePreviewResponse:
    """Preview sem persistência — UI decide antes de POST /."""
    await _require_learning_loop(workspace.id, db)
    detector = await _resolve_detector(workspace.id, db)
    transactions = _load_transactions_for(workspace.id)
    with _db_module.SyncSessionLocal() as sync_db:
        return _preview_rule_sync(
            workspace_id=workspace.id,
            body=body,
            detector=detector,
            transactions=transactions,
            sync_db=sync_db,
        )


@router.post(
    "",
    response_model=Union[CategorizationRuleResponse, AsyncRuleCreatedResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        202: {
            "model": AsyncRuleCreatedResponse,
            "description": "Apply retroativo deferido para Celery worker.",
        }
    },
)
async def create_rule_endpoint(
    body: CategorizationRuleCreate,
    response: Response,
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cria regra — ≤500 matches inline (201); >500 dispara Celery (202 + job_id) (ADR-188 PR3)."""
    await _require_learning_loop(workspace.id, db)
    detector = await _resolve_detector(workspace.id, db)
    transactions = _load_transactions_for(workspace.id)
    estimated = rule_management_service.estimate_apply_matches(
        keyword=body.keyword,
        target_category=body.target_category,
        transactions=transactions,
    )
    if estimated > SYNC_APPLY_THRESHOLD:
        response.status_code = status.HTTP_202_ACCEPTED
        with _db_module.SyncSessionLocal() as sync_db:
            return _create_rule_async_dispatch(
                workspace_id=workspace.id, body=body, user_id=current_user.id, sync_db=sync_db
            )
    with _db_module.SyncSessionLocal() as sync_db:
        return _create_rule_sync(
            workspace_id=workspace.id,
            body=body,
            user_id=current_user.id,
            detector=detector,
            transactions=transactions,
            sync_db=sync_db,
        )


def _apply_status_from_raw(rule_id: str, ws_id: str, raw: dict | None) -> RuleApplyStatusResponse:
    if raw is None:
        return RuleApplyStatusResponse(rule_id=rule_id, workspace_id=ws_id, status="unknown")
    return RuleApplyStatusResponse(
        rule_id=rule_id,
        workspace_id=ws_id,
        status=raw.get("status", "unknown"),
        job_id=raw.get("job_id"),
        started_at=raw.get("started_at"),
        completed_at=raw.get("completed_at"),
        applied_count=int(raw.get("applied_count") or 0),
        failed_count=int(raw.get("failed_count") or 0),
        error=raw.get("error"),
    )


@router.get(
    "/{rule_id}/apply-status",
    response_model=RuleApplyStatusResponse,
)
async def get_apply_status_endpoint(
    rule_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> RuleApplyStatusResponse:
    """Status do apply retroativo async — ``unknown`` se job nunca foi disparado (ADR-188 PR3)."""
    await _require_learning_loop(workspace.id, db)
    raw = rule_apply_state.get_status(workspace_id=workspace.id, rule_id=rule_id)
    return _apply_status_from_raw(rule_id, workspace.id, raw)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_rule_endpoint(
    rule_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Response:
    """Soft-delete rule + cascade ``transaction_overrides.source='rule'``."""
    await _require_learning_loop(workspace.id, db)
    with _db_module.SyncSessionLocal() as sync_db:
        rule_management_service.delete_rule(workspace_id=workspace.id, rule_id=rule_id, db=sync_db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "",
    response_model=RulesListResponse,
)
async def list_rules_endpoint(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    enabled: bool | None = None,
    page: int = 1,
    page_size: int = 50,
) -> RulesListResponse:
    """Lista paginada de regras + meta (count, caps, warnings)."""
    await _require_learning_loop(workspace.id, db)
    with _db_module.SyncSessionLocal() as sync_db:
        return _list_rules_sync(
            workspace_id=workspace.id,
            enabled=enabled,
            page=page,
            page_size=page_size,
            sync_db=sync_db,
        )


@router.post(
    "/{rule_id}/disable",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def disable_rule_endpoint(
    rule_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Response:
    """Toggle ``enabled=false`` — não cascadia overrides (idempotente)."""
    await _require_learning_loop(workspace.id, db)
    with _db_module.SyncSessionLocal() as sync_db:
        rule_management_service.disable_rule(workspace_id=workspace.id, rule_id=rule_id, db=sync_db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
