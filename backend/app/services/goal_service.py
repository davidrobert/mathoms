"""Goal service — ADR-073.

Contém:

- **Compute services puros** (``compute_if_derived``,
  ``compute_aporte_derived``, ``compute_dolar_derived``,
  ``compute_alocacao_derived``): função única que deriva valores
  server-side. Chamados pelos endpoints ``/compute`` (preview live)
  e pelos adapters do pipeline. Domain logic — **zero dependência
  de DB**.
- **Orquestração de alto-nível** (CRUD versionado): delega persistência
  ao ``GoalRepository`` e conversão entity→response ao mapper DTO
  (``schemas/dto/goal/mapper.py``).

**Regra invariante**: para cada ``(workspace_id, type)`` existe no
máximo um registro com ``effective_to IS NULL``. Garantido pelo
unique index parcial ``ux_goals_current_ws_type`` (ver migration
``b1c2d3e4f5a6_f8_goals.py``) + fluxo ``close active + flush + insert``
dentro de ``GoalRepository.create_new_version``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.goal import Goal
from backend.app.models.report import Report
from backend.app.models.user import User
from backend.app.repositories.goal_repository import GoalRepository
from backend.app.schemas.dto.goal import (
    AlocacaoGoalDerived,
    AlocacaoGoalInputs,
    AporteGoalDerived,
    AporteGoalInputs,
    DolarGoalDerived,
    DolarGoalInputs,
    GoalResponseBase,
    IFGoalDerived,
    IFGoalInputs,
    IFGoalResponse,
    goal_to_if_response,
    goal_to_typed_response,
)

# ─── Compute services (puros) ─────────────────────────────────────────


_CENT = Decimal("0.01")
_ZERO = Decimal("0")
_ONE = Decimal("1")
_EPSILON = Decimal("1e-12")


def _retorno_mensal_decimal(retorno_real_anual_pct: float) -> Decimal:
    """Converte taxa real anual (%) em taxa mensal equivalente, em Decimal.

    ``(1+r_anual)^(1/12) - 1`` via ``ln`` + ``exp`` (Decimal não suporta
    expoente fracionário direto). Precisão herda do contexto (default 28).
    """
    r_annual = Decimal(str(retorno_real_anual_pct)) / Decimal("100")
    if r_annual <= _ZERO:
        return _ZERO
    return ((_ONE + r_annual).ln() / Decimal("12")).exp() - _ONE


def _pmt_constante_ate_fv(
    fv_alvo: Decimal,
    n_meses: int,
    retorno_mensal: Decimal,
) -> Decimal:
    """Parcela mensal (início do período) para atingir FV_alvo em n meses,
    com taxa retorno_mensal, **sem** valor inicial (anuidade pura).
    """
    if fv_alvo <= _ZERO:
        return _ZERO
    if retorno_mensal < _EPSILON:
        return fv_alvo / Decimal(n_meses)
    fator = (_ONE + retorno_mensal) ** n_meses - _ONE
    return fv_alvo * retorno_mensal / fator


def _if_meta_targets(inputs: IFGoalInputs) -> tuple[Decimal, Decimal]:
    """Calcula `if_meta_brl` operacional (TRS) e conservadora (4% Trinity)."""
    renda_mensal = inputs.renda_passiva_mensal_brl
    trs = Decimal(str(inputs.trs_pct)) / Decimal("100")
    cons = Decimal(str(inputs.taxa_retirada_conservadora_pct)) / Decimal("100")
    if_meta = renda_mensal * Decimal("12") / trs
    if_meta_conservadora = renda_mensal * Decimal("12") / cons
    return if_meta, if_meta_conservadora


def _aporte_cobrindo_gap_com_patrimonio(
    if_meta: Decimal,
    n_meses: int,
    retorno_mensal: Decimal,
    patrimonio_atual_brl: Decimal,
) -> tuple[Decimal, Decimal]:
    """FV do patrimônio atual leva parte da meta; calcula PMT do gap restante.

    Retorna (aporte_com_pat_arredondado, patrimonio_utilizado_arredondado).
    """
    pat_util = max(_ZERO, patrimonio_atual_brl)
    fv_patrimonio_hoje = pat_util * ((_ONE + retorno_mensal) ** n_meses)
    gap = max(_ZERO, if_meta - fv_patrimonio_hoje)
    aporte = _pmt_constante_ate_fv(gap, n_meses, retorno_mensal).quantize(_CENT)
    return aporte, pat_util.quantize(_CENT)


def compute_if_derived(
    inputs: IFGoalInputs,
    patrimonio_atual_brl: Optional[Decimal] = None,
) -> IFGoalDerived:
    """Deriva os valores da meta IF a partir dos inputs do usuário.

    Fórmulas:
        if_meta_brl = renda_passiva_mensal × 12 / (trs_pct / 100)
        if_meta_conservadora_brl = renda_passiva_mensal × 12 / (taxa_conservadora_pct / 100)
        aporte_necessario_mensal_brl = PMT para atingir if_meta **partindo de zero**
            (mesma fórmula de anuidade que antes — preserva persistência e testes).
        Se `patrimonio_atual_brl` é informado (ex.: patrimônio líquido do último
        relatório), também calcula `aporte_mensal_com_patrimonio_atual_brl` via
        `_aporte_cobrindo_gap_com_patrimonio`.

    Casos especiais: retorno_real_anual_pct == 0 → aporte = meta / n_meses.

    É **função pura**: mesmos inputs → mesmos outputs. Sem side-effects.
    Testada exaustivamente em `test_goal_service.py`.
    """
    if_meta, if_meta_conservadora = _if_meta_targets(inputs)
    n_meses = inputs.horizonte_anos * 12
    retorno_mensal = _retorno_mensal_decimal(inputs.retorno_real_anual_pct)

    aporte_partindo_zero = _pmt_constante_ate_fv(if_meta, n_meses, retorno_mensal)

    aporte_com_pat: Optional[Decimal] = None
    pat_util: Optional[Decimal] = None
    if patrimonio_atual_brl is not None:
        pat_dec = (
            patrimonio_atual_brl
            if isinstance(patrimonio_atual_brl, Decimal)
            else Decimal(str(patrimonio_atual_brl))
        )
        aporte_com_pat, pat_util = _aporte_cobrindo_gap_com_patrimonio(
            if_meta, n_meses, retorno_mensal, pat_dec
        )

    return IFGoalDerived(
        if_meta_brl=if_meta.quantize(_CENT),
        aporte_necessario_mensal_brl=aporte_partindo_zero.quantize(_CENT),
        if_meta_conservadora_brl=if_meta_conservadora.quantize(_CENT),
        aporte_mensal_com_patrimonio_atual_brl=aporte_com_pat,
        patrimonio_atual_utilizado_brl=pat_util,
    )


DEFAULT_CAMBIO_BRL_USD = 5.70  # MVP — override via compute request


def compute_aporte_derived(inputs: AporteGoalInputs) -> AporteGoalDerived:
    """Deriva aporte anual e % de distribuição."""
    anual = inputs.meta_aporte_mensal_brl * Decimal("12")
    pct: dict[str, float] = {}
    if inputs.distribuicao:
        pct = {
            k: float(
                (Decimal("100") * v / inputs.meta_aporte_mensal_brl).quantize(_CENT)
            )
            for k, v in inputs.distribuicao.items()
        }
    return AporteGoalDerived(
        aporte_anual_brl=anual.quantize(_CENT),
        distribuicao_pct=pct,
    )


def compute_dolar_derived(
    inputs: DolarGoalInputs,
    cambio_brl_usd: Optional[float] = None,
) -> DolarGoalDerived:
    """Estima meses para atingir meta USD dado aporte mensal em BRL."""
    cambio = Decimal(str(cambio_brl_usd or DEFAULT_CAMBIO_BRL_USD))
    aporte_usd = inputs.aporte_mensal_brl / cambio
    if aporte_usd <= _ZERO:
        meses = 0.0
    else:
        meses = float(inputs.meta_usd / aporte_usd)
    return DolarGoalDerived(
        horizonte_estimado_meses=round(max(0.0, meses), 1),
    )


def compute_alocacao_derived(inputs: AlocacaoGoalInputs) -> AlocacaoGoalDerived:
    """Calcula soma dos percentuais (deve ser 100)."""
    soma = (
        inputs.renda_fixa_pct
        + inputs.acoes_pct
        + inputs.imoveis_reits_pct
        + inputs.liquidez_usd_pct
    )
    return AlocacaoGoalDerived(soma_percentuais=round(soma, 2))


# ─── Enriquecimento de respostas (autor, patrimônio) ─────────────────


async def _resolve_author_names(user_ids: set[str], *, db: AsyncSession) -> dict[str, str]:
    """Batch lookup ``user_id → full_name``. Usado para authorship nos goals.

    Tenancy: ``User`` é auth-level (não tenant-scoped), então a query
    não inclui ``workspace_id``. Retorna dict vazio se ``user_ids``
    vazio.
    """
    if not user_ids:
        return {}
    rows = await db.execute(select(User).where(User.id.in_(list(user_ids))))
    return {u.id: u.full_name for u in rows.scalars().all()}


async def get_latest_report_patrimonio_liquido(
    workspace_id: str,
    *,
    db: AsyncSession,
) -> Optional[Decimal]:
    """Último ``patrimonio_liquido`` não nulo do workspace (por ``created_at``).

    Usado pelo endpoint IF para enriquecer a resposta com o valor real
    do patrimônio, permitindo UI de progresso (percentual conquistado,
    aporte ajustado). ``Report`` é outro agregado — query fica no
    service porque é composição cross-agregado.
    """
    stmt = (
        select(Report.patrimonio_liquido)
        .where(
            Report.workspace_id == workspace_id,
            Report.patrimonio_liquido.isnot(None),
        )
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    return Decimal(str(row))


# ─── Orquestração (leitura + criação versionada) ─────────────────────


async def get_current_goal_with_author(
    workspace_id: str,
    goal_type: str,
    *,
    db: AsyncSession,
) -> Optional[IFGoalResponse]:
    """Versão IF que já popula ``created_by_name`` — use em endpoints
    de leitura para expor autoria na UI (F9)."""
    repo = GoalRepository(db)
    goal = await repo.get_active_by_type(workspace_id, goal_type)
    if goal is None:
        return None
    names = await _resolve_author_names({goal.created_by} if goal.created_by else set(), db=db)
    return goal_to_if_response(goal, created_by_name=names.get(goal.created_by or ""))


async def get_goal_history_with_authors(
    workspace_id: str,
    goal_type: str,
    *,
    db: AsyncSession,
) -> list[IFGoalResponse]:
    repo = GoalRepository(db)
    goals = await repo.list_by_workspace_and_type(workspace_id, goal_type)
    ids = {g.created_by for g in goals if g.created_by}
    names = await _resolve_author_names(ids, db=db)
    return [goal_to_if_response(g, created_by_name=names.get(g.created_by or "")) for g in goals]


async def get_current_goal_typed(
    workspace_id: str,
    goal_type: str,
    *,
    db: AsyncSession,
) -> Optional[GoalResponseBase]:
    """Retorna o Goal vigente como response tipada (qualquer goal type)."""
    repo = GoalRepository(db)
    goal = await repo.get_active_by_type(workspace_id, goal_type)
    if goal is None:
        return None
    names = await _resolve_author_names({goal.created_by} if goal.created_by else set(), db=db)
    return goal_to_typed_response(goal, created_by_name=names.get(goal.created_by or ""))


async def get_goal_history_typed(
    workspace_id: str,
    goal_type: str,
    *,
    db: AsyncSession,
) -> list[GoalResponseBase]:
    """Histórico tipado de qualquer goal type."""
    repo = GoalRepository(db)
    goals = await repo.list_by_workspace_and_type(workspace_id, goal_type)
    ids = {g.created_by for g in goals if g.created_by}
    names = await _resolve_author_names(ids, db=db)
    return [goal_to_typed_response(g, created_by_name=names.get(g.created_by or "")) for g in goals]


async def create_if_goal_version(
    workspace_id: str,
    inputs: IFGoalInputs,
    *,
    db: AsyncSession,
    created_by: Optional[str] = None,
    notes: Optional[str] = None,
    is_template: bool = False,
    effective_from: Optional[date] = None,
) -> Goal:
    """Cria nova versão da meta IF.

    Deriva os valores via ``compute_if_derived`` e delega persistência
    ao ``GoalRepository.create_new_version`` (fecha vigente + insert
    dentro da mesma transação). Caller faz ``db.commit()``.
    """
    derived = compute_if_derived(inputs)
    repo = GoalRepository(db)
    return await repo.create_new_version(
        workspace_id,
        "INDEPENDENCIA_FINANCEIRA",
        params_json={
            "inputs": inputs.model_dump(mode="json"),
            "meta_version": 1,
        },
        derived_json=derived.model_dump(mode="json", exclude_none=True),
        created_by=created_by,
        notes=notes,
        is_template=is_template,
        effective_from=effective_from,
    )


async def create_goal_version(
    workspace_id: str,
    goal_type: str,
    inputs: BaseModel,
    derived: BaseModel,
    *,
    db: AsyncSession,
    created_by: Optional[str] = None,
    notes: Optional[str] = None,
    is_template: bool = False,
    effective_from: Optional[date] = None,
) -> Goal:
    """Cria nova versão de qualquer goal type (genérico).

    O caller já computou ``derived`` via ``compute_*_derived`` — evita
    acoplamento do service com a tabela de compute functions por tipo.
    """
    repo = GoalRepository(db)
    return await repo.create_new_version(
        workspace_id,
        goal_type,
        params_json={
            "inputs": inputs.model_dump(mode="json"),
            "meta_version": 1,
        },
        derived_json=derived.model_dump(mode="json", exclude_none=True),
        created_by=created_by,
        notes=notes,
        is_template=is_template,
        effective_from=effective_from,
    )


# ─── Compat com chamadores legados (migrarão gradualmente) ───────────


async def get_current_goal(
    workspace_id: str,
    goal_type: str,
    *,
    db: AsyncSession,
) -> Optional[Goal]:
    """Retorna o Goal vigente (entity ORM) ou None.

    Preservado por compat — prefira ``get_current_goal_typed`` /
    ``get_current_goal_with_author`` que devolvem DTOs prontos.
    """
    repo = GoalRepository(db)
    return await repo.get_active_by_type(workspace_id, goal_type)


async def get_goal_history(
    workspace_id: str,
    goal_type: str,
    *,
    db: AsyncSession,
) -> list[Goal]:
    """Histórico (entities ORM) mais recente primeiro.

    Preservado por compat — prefira ``get_goal_history_typed`` que
    devolve DTOs prontos.
    """
    repo = GoalRepository(db)
    return await repo.list_by_workspace_and_type(workspace_id, goal_type)


# Mapper legado — ``_goal_to_response`` / ``_goal_to_typed_response`` —
# migraram para ``schemas/dto/goal/mapper.py``. Re-exports abaixo por
# compat binária (callers legados, ex.: router em migração gradual).
_goal_to_response = goal_to_if_response
_goal_to_typed_response = goal_to_typed_response


__all__ = [
    "DEFAULT_CAMBIO_BRL_USD",
    "compute_alocacao_derived",
    "compute_aporte_derived",
    "compute_dolar_derived",
    "compute_if_derived",
    "create_goal_version",
    "create_if_goal_version",
    "get_current_goal",
    "get_current_goal_typed",
    "get_current_goal_with_author",
    "get_goal_history",
    "get_goal_history_typed",
    "get_goal_history_with_authors",
    "get_latest_report_patrimonio_liquido",
    "_goal_to_response",
    "_goal_to_typed_response",
]
