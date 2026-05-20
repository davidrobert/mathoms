"""Debt API — CRUD para passivos persistidos (ADR-227 §D1 · Sprint A15 Onda 4)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace
from backend.app.models import Debt
from backend.app.models.workspace import Workspace
from backend.app.repositories.debt_repository import DebtRepository
from backend.app.schemas.dto.debt import DebtCreate, DebtResponse, DebtUpdate

router = APIRouter(tags=["debts"])

_BRL_TO_CENTS = Decimal("100")
_BRL_QUANTUM = Decimal("0.01")


def _get_repo(db: AsyncSession = Depends(get_db)) -> DebtRepository:
    return DebtRepository(db)


def _brl_to_cents(value: Decimal | None) -> int | None:
    if value is None:
        return None
    return int(value * _BRL_TO_CENTS)


def _cents_to_brl(cents: int | None) -> Decimal | None:
    if cents is None:
        return None
    return (Decimal(cents) / _BRL_TO_CENTS).quantize(_BRL_QUANTUM)


def _to_response(debt: Debt) -> DebtResponse:
    return DebtResponse(
        id=debt.id,
        workspace_id=debt.workspace_id,
        family_member_id=debt.family_member_id,
        property_id=debt.property_id,
        tipo=debt.tipo,  # type: ignore[arg-type]
        descricao=debt.descricao,
        saldo_devedor_brl=_cents_to_brl(debt.saldo_devedor_cents),
        parcela_mensal_brl=_cents_to_brl(debt.parcela_mensal_cents),
        taxa_juros_aa=debt.taxa_juros_aa,
        prazo_meses_restantes=debt.prazo_meses_restantes,
        data_contratacao=debt.data_contratacao,
        source=debt.source,  # type: ignore[arg-type]
        migration_source_key=debt.migration_source_key,
        needs_review=debt.needs_review,
        percentual_atribuicao_imovel=debt.percentual_atribuicao_imovel,
        created_at=debt.created_at,
        updated_at=debt.updated_at,
    )


def _build_debt_fields(body: DebtCreate) -> dict:
    return {
        "family_member_id": body.family_member_id,
        "property_id": body.property_id,
        "tipo": body.tipo,
        "descricao": body.descricao,
        "saldo_devedor_cents": _brl_to_cents(body.saldo_devedor_brl),
        "parcela_mensal_cents": _brl_to_cents(body.parcela_mensal_brl),
        "taxa_juros_aa": body.taxa_juros_aa,
        "prazo_meses_restantes": body.prazo_meses_restantes,
        "data_contratacao": body.data_contratacao,
        "source": body.source,
        "migration_source_key": body.migration_source_key,
        "needs_review": body.needs_review,
        "percentual_atribuicao_imovel": body.percentual_atribuicao_imovel,
    }


@router.get("/workspaces/{workspace_id}/debts", response_model=list[DebtResponse])
async def list_debts(
    needs_review: bool | None = None,
    workspace: Workspace = Depends(get_current_workspace),
    repo: DebtRepository = Depends(_get_repo),
) -> list[DebtResponse]:
    """Lista Debts do workspace; filtro opcional ``?needs_review=true``."""
    if needs_review:
        debts = await repo.list_needs_review(workspace.id)
    else:
        debts = await repo.list_for_workspace(workspace.id)
    return [_to_response(d) for d in debts]


@router.post(
    "/workspaces/{workspace_id}/debts",
    response_model=DebtResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_debt(
    body: DebtCreate,
    workspace: Workspace = Depends(get_current_workspace),
    repo: DebtRepository = Depends(_get_repo),
) -> DebtResponse:
    debt = await repo.create(workspace.id, **_build_debt_fields(body))
    return _to_response(debt)


_FIELD_MAP_DIRECT = (
    "family_member_id",
    "property_id",
    "tipo",
    "descricao",
    "taxa_juros_aa",
    "prazo_meses_restantes",
    "data_contratacao",
    "percentual_atribuicao_imovel",
    "needs_review",
)


def _build_update_dict(body: DebtUpdate) -> dict:
    """Constrói dict de updates filtrando None + convertendo BRL para cents."""
    fields: dict = {}
    for name in _FIELD_MAP_DIRECT:
        value = getattr(body, name)
        if value is not None:
            fields[name] = value
    if body.saldo_devedor_brl is not None:
        fields["saldo_devedor_cents"] = int(body.saldo_devedor_brl * _BRL_TO_CENTS)
    if body.parcela_mensal_brl is not None:
        fields["parcela_mensal_cents"] = int(body.parcela_mensal_brl * _BRL_TO_CENTS)
    return fields


@router.patch("/workspaces/{workspace_id}/debts/{debt_id}", response_model=DebtResponse)
async def update_debt(
    debt_id: str,
    body: DebtUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    repo: DebtRepository = Depends(_get_repo),
) -> DebtResponse:
    debt = await repo.get_by_id(workspace.id, debt_id)
    if debt is None:
        raise HTTPException(status_code=404, detail="Debt não encontrada")
    updated = await repo.update(debt, **_build_update_dict(body))
    return _to_response(updated)


@router.delete(
    "/workspaces/{workspace_id}/debts/{debt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_debt(
    debt_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    repo: DebtRepository = Depends(_get_repo),
) -> None:
    debt = await repo.get_by_id(workspace.id, debt_id)
    if debt is None:
        raise HTTPException(status_code=404, detail="Debt não encontrada")
    await repo.delete(debt)
