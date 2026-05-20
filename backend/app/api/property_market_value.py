"""PropertyMarketValue API — declarações versionadas append-only (ADR-227 §D2 · Sprint A15 Onda 4)."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace
from backend.app.models import PropertyMarketValue
from backend.app.models.workspace import Workspace
from backend.app.repositories.property_market_value_repository import (
    PropertyMarketValueRepository,
)
from backend.app.schemas.dto.property_market_value import (
    PropertyMarketValueCreate,
    PropertyMarketValueResponse,
)

router = APIRouter(tags=["property-market-values"])

_BRL_TO_CENTS = Decimal("100")
_BRL_QUANTUM = Decimal("0.01")


def _get_repo(db: AsyncSession = Depends(get_db)) -> PropertyMarketValueRepository:
    return PropertyMarketValueRepository(db)


def _to_response(pmv: PropertyMarketValue) -> PropertyMarketValueResponse:
    return PropertyMarketValueResponse(
        id=pmv.id,
        property_id=pmv.property_id,
        workspace_id=pmv.workspace_id,
        valor_brl=(Decimal(pmv.valor_brl_cents) / _BRL_TO_CENTS).quantize(_BRL_QUANTUM),
        valuation_date=pmv.valuation_date,
        source=pmv.source,  # type: ignore[arg-type]
        confidence=pmv.confidence,
        notes=pmv.notes,
        superseded_by_id=pmv.superseded_by_id,
        created_at=pmv.created_at,
        created_by_user_id=pmv.created_by_user_id,
    )


class SupersedeRequest(BaseModel):
    """Marca declaração como superseded por outra do MESMO property_id."""

    superseded_by_id: str = Field(..., max_length=36)


@router.get(
    "/workspaces/{workspace_id}/property-market-values",
    response_model=list[PropertyMarketValueResponse],
)
async def list_property_market_values(
    property_id: str | None = None,
    workspace: Workspace = Depends(get_current_workspace),
    repo: PropertyMarketValueRepository = Depends(_get_repo),
) -> list[PropertyMarketValueResponse]:
    """Lista declarações do workspace; filtro opcional por ``?property_id=...``."""
    if property_id:
        rows = await repo.list_for_property(workspace.id, property_id)
    else:
        rows = await repo.list_for_workspace(workspace.id)
    return [_to_response(p) for p in rows]


def _pmv_create_kwargs(body: PropertyMarketValueCreate) -> dict:
    return {
        "property_id": body.property_id,
        "valor_brl_cents": int(body.valor_brl * _BRL_TO_CENTS),
        "valuation_date": body.valuation_date,
        "source": body.source,
        "confidence": body.confidence,
        "notes": body.notes,
    }


@router.post(
    "/workspaces/{workspace_id}/property-market-values",
    response_model=PropertyMarketValueResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_property_market_value(
    body: PropertyMarketValueCreate,
    workspace: Workspace = Depends(get_current_workspace),
    repo: PropertyMarketValueRepository = Depends(_get_repo),
) -> PropertyMarketValueResponse:
    """Cria declaração; UNIQUE (property_id, valuation_date) → 409 via IntegrityError."""
    try:
        pmv = await repo.create(workspace.id, **_pmv_create_kwargs(body))
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Declaração para esta data já existe; use PATCH /supersede para corrigir.",
        ) from exc
    return _to_response(pmv)


@router.patch(
    "/workspaces/{workspace_id}/property-market-values/{value_id}/supersede",
    response_model=PropertyMarketValueResponse,
)
async def supersede_property_market_value(
    value_id: str,
    body: SupersedeRequest,
    workspace: Workspace = Depends(get_current_workspace),
    repo: PropertyMarketValueRepository = Depends(_get_repo),
) -> PropertyMarketValueResponse:
    """Marca declaração antiga como superseded; ``superseded_by_id`` deve ser do mesmo ``property_id``."""
    old_pmv = await repo.get_by_id(workspace.id, value_id)
    if old_pmv is None:
        raise HTTPException(status_code=404, detail="PropertyMarketValue não encontrado")
    new_pmv = await repo.get_by_id(workspace.id, body.superseded_by_id)
    if new_pmv is None:
        raise HTTPException(status_code=404, detail="Superseded_by_id não encontrado")
    if new_pmv.property_id != old_pmv.property_id:
        raise HTTPException(
            status_code=422,
            detail="superseded_by_id deve apontar para declaração do mesmo property_id",
        )
    updated = await repo.supersede(old_pmv, by_id=body.superseded_by_id)
    return _to_response(updated)
