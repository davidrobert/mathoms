"""LGPD Art.37 ([[ADR-275]]) — auditoria de acesso a leitura de dado sensível: dependency FastAPI por rota grava 1 linha em ``audit_logs`` (reuso, não tabela nova) e commita ANTES do handler (sobrevive a falha posterior do handler); ``details`` é allowlist tipada (``AccessAuditDetails`` ``extra="forbid"``) com guarda de escrita anti-PII (nunca CPF/valor)."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

from fastapi import Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services.audit import AuditAction, audit_log

# CPF (com/sem máscara) + valor monetário BRL — guarda anti-PII no ``details``.
_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_MONEY_RE = re.compile(r"R\$\s?\d|\b\d{1,3}(?:\.\d{3})*,\d{2}\b")


class AccessAuditPIIError(ValueError):
    """``details`` de acesso contém padrão PII (CPF/valor) — escrita rejeitada."""


class AccessAuditDetails(BaseModel):
    """Metadados de acesso (Art.37) — shape fechado, nunca payload sensível."""

    model_config = ConfigDict(extra="forbid")

    method: str
    route: str
    query_keys: tuple[str, ...] = ()


def assert_pii_free(details: dict) -> dict:
    """Guarda de escrita — rejeita CPF/valor monetário em qualquer valor do ``details``."""
    for key, value in details.items():
        text = " ".join(map(str, value)) if isinstance(value, (list, tuple)) else str(value)
        if _CPF_RE.search(text) or _MONEY_RE.search(text):
            raise AccessAuditPIIError(f"padrão PII no campo de acesso '{key}'")
    return details


def _build_access_details(request: Request) -> dict:
    """Monta o ``details`` allowlistado (template de rota + chaves de query), já guardado anti-PII."""
    route_obj = request.scope.get("route")
    return assert_pii_free(
        AccessAuditDetails(
            method=request.method,
            route=getattr(route_obj, "path", request.url.path),
            query_keys=tuple(sorted(request.query_params.keys())),
        ).model_dump()
    )


def record_access_audit(
    action: AuditAction | str,
    resource_type: str,
    *,
    resource_id_param: str | None = None,
) -> Callable[..., Awaitable[None]]:
    """Fábrica de dependency FastAPI — anexe via ``dependencies=[Depends(...)]`` numa rota GET sensível; grava o acesso em sessão isolada (commit imediato)."""

    async def _record_access(
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
        workspace: Workspace = Depends(get_current_workspace),
    ) -> None:
        resource_id = request.path_params.get(resource_id_param) if resource_id_param else None
        await audit_log(
            db,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            workspace_id=workspace.id,
            actor_user_id=current_user.id,
            request=request,
            details=_build_access_details(request),
        )
        await db.commit()

    _record_access._is_access_audit = True  # marcador p/ test-guard de cobertura
    _record_access._audit_action = action.value if isinstance(action, AuditAction) else action
    return _record_access
