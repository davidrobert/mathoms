"""CategorizationRules API — learning loop CRUD + preview (ADR-186/188 · A12 P3 PR2)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.categorization import rule_management_service, rule_preview_service
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
    CategorizationRuleCreate,
    CategorizationRuleResponse,
    RulePreviewRequest,
    RulePreviewResponse,
    RulesListResponse,
)
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
    """Gate via ``workspaces.learning_loop_enabled`` feature flag (default off)."""
    if not await is_enabled(workspace_id, "learning_loop_enabled", db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "learning_loop_disabled",
                "message": "Learning loop não habilitado para este workspace. "
                "Solicite ativação ao admin (gate dogfood ADR-186 §D6).",
            },
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
    response_model=CategorizationRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rule_endpoint(
    body: CategorizationRuleCreate,
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CategorizationRuleResponse:
    """Cria regra + apply retroativo síncrono (≤500 overrides)."""
    await _require_learning_loop(workspace.id, db)
    detector = await _resolve_detector(workspace.id, db)
    transactions = _load_transactions_for(workspace.id)
    with _db_module.SyncSessionLocal() as sync_db:
        return _create_rule_sync(
            workspace_id=workspace.id,
            body=body,
            user_id=current_user.id,
            detector=detector,
            transactions=transactions,
            sync_db=sync_db,
        )


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
