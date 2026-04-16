"""Goal service — ADR-073.

Contém:
- `compute_if_derived(inputs, patrimonio_atual_brl=None)` — função pura,
  fonte única dos valores derivados. Chamada pelo endpoint `/goals/if/compute`
  (preview live do frontend) e pelo pipeline adapter. Com patrimônio atual,
  calcula também o aporte mensal ajustado (gap até a meta).
- CRUD + versionamento append-only (edição cria novo registro, fecha o
  anterior com `effective_to = ontem`).

**Regra invariante**: para cada (workspace_id, type), existe no máximo
um registro com `effective_to IS NULL`. Garantido por unique index
parcial em [b1c2d3e4f5a6_f8_goals.py].
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from pydantic import BaseModel as BaseModel

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.goal import Goal, VALID_GOAL_TYPES
from backend.app.models.report import Report
from backend.app.models.user import User
from backend.app.schemas.goal import (
    IFGoalDerived,
    IFGoalInputs,
    IFGoalResponse,
    AporteGoalDerived,
    AporteGoalInputs,
    AporteGoalResponse,
    DolarGoalDerived,
    DolarGoalInputs,
    DolarGoalResponse,
    AlocacaoGoalDerived,
    AlocacaoGoalInputs,
    AlocacaoGoalResponse,
    _GoalResponseBase,
)


# ─── Função pura de derivação ──────────────────────────────────────────


def _pmt_constante_ate_fv(
    fv_alvo: float,
    n_meses: int,
    retorno_mensal: float,
) -> float:
    """Parcela mensal (início do período) para atingir FV_alvo em n meses,
    com taxa retorno_mensal, **sem** valor inicial (anuidade pura).
    """
    if fv_alvo <= 0:
        return 0.0
    if retorno_mensal < 1e-12:
        return fv_alvo / n_meses
    fator = (1 + retorno_mensal) ** n_meses - 1
    return fv_alvo * retorno_mensal / fator


def compute_if_derived(
    inputs: IFGoalInputs,
    patrimonio_atual_brl: Optional[float] = None,
) -> IFGoalDerived:
    """Deriva os valores da meta IF a partir dos inputs do usuário.

    Fórmulas:
        if_meta_brl = renda_passiva_mensal × 12 / (trs_pct / 100)
        if_meta_conservadora_brl = renda_passiva_mensal × 12 / (taxa_conservadora_pct / 100)
        aporte_necessario_mensal_brl = PMT para atingir if_meta **partindo de zero**
            (mesma fórmula de anuidade que antes — preserva persistência e testes).
        Se `patrimonio_atual_brl` é informado (ex.: patrimônio líquido do último
        relatório), também calcula `aporte_mensal_com_patrimonio_atual_brl`:
            FV do patrimônio hoje = PV × (1+r)^n
            gap = max(0, if_meta − FV_patrimonio)
            PMT_gap = PMT para acumular `gap` em n meses (mesma taxa).

    Casos especiais:
        - retorno_real_anual_pct == 0: aporte = meta / n_meses (sem juros)

    É **função pura**: mesmos inputs → mesmos outputs. Sem side-effects.
    Testada exaustivamente em `test_goal_service.py`.
    """
    renda_mensal = inputs.renda_passiva_mensal_brl
    trs_decimal = inputs.trs_pct / 100.0
    taxa_conserv_decimal = inputs.taxa_retirada_conservadora_pct / 100.0

    if_meta = renda_mensal * 12.0 / trs_decimal
    if_meta_conservadora = renda_mensal * 12.0 / taxa_conserv_decimal

    n_meses = inputs.horizonte_anos * 12
    retorno_mensal = (1 + inputs.retorno_real_anual_pct / 100.0) ** (1 / 12) - 1

    aporte_partindo_zero = _pmt_constante_ate_fv(if_meta, n_meses, retorno_mensal)

    aporte_com_pat: Optional[float] = None
    pat_util: Optional[float] = None
    if patrimonio_atual_brl is not None:
        pat_util = max(0.0, float(patrimonio_atual_brl))
        fv_patrimonio_hoje = pat_util * ((1 + retorno_mensal) ** n_meses)
        gap = max(0.0, if_meta - fv_patrimonio_hoje)
        aporte_com_pat = round(_pmt_constante_ate_fv(gap, n_meses, retorno_mensal), 2)

    return IFGoalDerived(
        if_meta_brl=round(if_meta, 2),
        aporte_necessario_mensal_brl=round(aporte_partindo_zero, 2),
        if_meta_conservadora_brl=round(if_meta_conservadora, 2),
        aporte_mensal_com_patrimonio_atual_brl=aporte_com_pat,
        patrimonio_atual_utilizado_brl=round(pat_util, 2) if pat_util is not None else None,
    )


# ─── Funções puras de derivação — Aporte, Dólar, Alocação ────────────

DEFAULT_CAMBIO_BRL_USD = 5.70  # MVP — override via compute request


def compute_aporte_derived(inputs: AporteGoalInputs) -> AporteGoalDerived:
    """Deriva aporte anual e % de distribuição."""
    anual = inputs.meta_aporte_mensal_brl * 12
    pct: dict[str, float] = {}
    if inputs.distribuicao:
        pct = {
            k: round(100 * v / inputs.meta_aporte_mensal_brl, 2)
            for k, v in inputs.distribuicao.items()
        }
    return AporteGoalDerived(
        aporte_anual_brl=round(anual, 2),
        distribuicao_pct=pct,
    )


def compute_dolar_derived(
    inputs: DolarGoalInputs,
    cambio_brl_usd: Optional[float] = None,
) -> DolarGoalDerived:
    """Estima meses para atingir meta USD dado aporte mensal em BRL."""
    cambio = cambio_brl_usd or DEFAULT_CAMBIO_BRL_USD
    aporte_usd = inputs.aporte_mensal_brl / cambio
    if aporte_usd <= 0:
        meses = 0.0
    else:
        meses = inputs.meta_usd / aporte_usd
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


# ─── CRUD versionado ──────────────────────────────────────────────────


def _goal_to_typed_response(
    goal: Goal,
    *,
    response_cls: type[_GoalResponseBase],
    inputs_cls: type,
    derived_cls: type,
    created_by_name: Optional[str] = None,
) -> _GoalResponseBase:
    """Conversor genérico entity → response Pydantic (qualquer goal type)."""
    return response_cls(
        id=goal.id,
        workspace_id=goal.workspace_id,
        type=goal.type,  # type: ignore[arg-type]
        inputs=inputs_cls(**goal.params_json["inputs"]),
        derived=derived_cls(**goal.derived_json),
        effective_from=goal.effective_from,
        effective_to=goal.effective_to,
        is_template=goal.is_template,
        notes=goal.notes,
        created_by=goal.created_by,
        created_by_name=created_by_name,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


def _goal_to_response(
    goal: Goal, *, created_by_name: Optional[str] = None
) -> IFGoalResponse:
    """Converte entity → response Pydantic, re-parseando os JSON blobs.

    `created_by_name` é resolvido pelos callers que tenham uma `db` session
    à mão (ver `get_current_goal_with_author` / `get_goal_history_with_authors`).
    """
    return IFGoalResponse(
        id=goal.id,
        workspace_id=goal.workspace_id,
        type=goal.type,  # type: ignore[arg-type]
        inputs=IFGoalInputs(**goal.params_json["inputs"]),
        derived=IFGoalDerived(**goal.derived_json),
        effective_from=goal.effective_from,
        effective_to=goal.effective_to,
        is_template=goal.is_template,
        notes=goal.notes,
        created_by=goal.created_by,
        created_by_name=created_by_name,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


async def _resolve_author_names(
    user_ids: set[str], *, db: AsyncSession
) -> dict[str, str]:
    """Batch lookup de `user_id → full_name`. Usado para authorship nos
    goals. Retorna dict vazio se user_ids vazio."""
    if not user_ids:
        return {}
    # tenancy: global — User é auth-level, não tenant-scoped
    rows = await db.execute(select(User).where(User.id.in_(list(user_ids))))
    return {u.id: u.full_name for u in rows.scalars().all()}


async def get_current_goal_with_author(
    workspace_id: str,
    goal_type: str,
    *,
    db: AsyncSession,
) -> Optional[IFGoalResponse]:
    """Versão que já popula `created_by_name` — use em endpoints de leitura
    para expor autoria na UI (F9)."""
    goal = await get_current_goal(workspace_id, goal_type, db=db)
    if goal is None:
        return None
    names = await _resolve_author_names(
        {goal.created_by} if goal.created_by else set(), db=db
    )
    return _goal_to_response(goal, created_by_name=names.get(goal.created_by or ""))


async def get_goal_history_with_authors(
    workspace_id: str,
    goal_type: str,
    *,
    db: AsyncSession,
) -> list[IFGoalResponse]:
    goals = await get_goal_history(workspace_id, goal_type, db=db)
    ids = {g.created_by for g in goals if g.created_by}
    names = await _resolve_author_names(ids, db=db)
    return [
        _goal_to_response(g, created_by_name=names.get(g.created_by or ""))
        for g in goals
    ]


async def get_current_goal(
    workspace_id: str,
    goal_type: str,
    *,
    db: AsyncSession,
) -> Optional[Goal]:
    """Retorna o Goal vigente (effective_to IS NULL) ou None.

    Uso de `workspace_id` como primeiro filtro — obrigatório por ADR-072.
    """
    if goal_type not in VALID_GOAL_TYPES:
        raise ValueError(f"Tipo de goal inválido: {goal_type}")

    stmt = select(Goal).where(
        Goal.workspace_id == workspace_id,
        Goal.type == goal_type,
        Goal.effective_to.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_goal_history(
    workspace_id: str,
    goal_type: str,
    *,
    db: AsyncSession,
) -> list[Goal]:
    """Histórico completo ordenado cronologicamente (mais recente
    primeiro). Útil para gráficos de evolução da meta."""
    if goal_type not in VALID_GOAL_TYPES:
        raise ValueError(f"Tipo de goal inválido: {goal_type}")

    stmt = (
        select(Goal)
        .where(
            Goal.workspace_id == workspace_id,
            Goal.type == goal_type,
        )
        .order_by(Goal.effective_from.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


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
    """Cria nova versão da meta IF. Se já existir registro vigente,
    fecha-o com `effective_to = effective_from - 1 dia` antes.

    A atomicidade é importante: o unique index parcial
    `ux_goals_current_ws_type` **rejeitaria** o INSERT se houvesse dois
    vigentes simultaneamente. Fazemos UPDATE antes do INSERT dentro da
    mesma transação — caller deve chamar `db.commit()` depois.
    """
    eff_from = effective_from or date.today()

    # Fecha vigente anterior (se existir) — mesma transação
    current = await get_current_goal(
        workspace_id, "INDEPENDENCIA_FINANCEIRA", db=db
    )
    if current is not None:
        # effective_to = um dia antes do novo effective_from, para manter
        # histórico sem gaps nem sobreposição
        current.effective_to = eff_from - timedelta(days=1)
        db.add(current)
        await db.flush()

    derived = compute_if_derived(inputs)

    goal = Goal(
        workspace_id=workspace_id,
        type="INDEPENDENCIA_FINANCEIRA",
        params_json={
            "inputs": inputs.model_dump(),
            "meta_version": 1,
        },
        derived_json=derived.model_dump(exclude_none=True),
        effective_from=eff_from,
        effective_to=None,
        created_by=created_by,
        notes=notes,
        is_template=is_template,
    )
    db.add(goal)
    await db.flush()
    return goal


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

    Mesma lógica append-only que `create_if_goal_version`: fecha o vigente
    anterior antes de inserir o novo.
    """
    if goal_type not in VALID_GOAL_TYPES:
        raise ValueError(f"Tipo de goal inválido: {goal_type}")

    eff_from = effective_from or date.today()

    current = await get_current_goal(workspace_id, goal_type, db=db)
    if current is not None:
        current.effective_to = eff_from - timedelta(days=1)
        db.add(current)
        await db.flush()

    goal = Goal(
        workspace_id=workspace_id,
        type=goal_type,
        params_json={
            "inputs": inputs.model_dump(),
            "meta_version": 1,
        },
        derived_json=derived.model_dump(exclude_none=True),
        effective_from=eff_from,
        effective_to=None,
        created_by=created_by,
        notes=notes,
        is_template=is_template,
    )
    db.add(goal)
    await db.flush()
    return goal


# Mapeia goal_type → (response_cls, inputs_cls, derived_cls) para helpers
_GOAL_TYPE_CLASSES: dict[str, tuple[type, type, type]] = {
    "INDEPENDENCIA_FINANCEIRA": (IFGoalResponse, IFGoalInputs, IFGoalDerived),
    "APORTE_MENSAL": (AporteGoalResponse, AporteGoalInputs, AporteGoalDerived),
    "DOLARIZACAO": (DolarGoalResponse, DolarGoalInputs, DolarGoalDerived),
    "ALOCACAO_ALVO": (AlocacaoGoalResponse, AlocacaoGoalInputs, AlocacaoGoalDerived),
}


async def get_current_goal_typed(
    workspace_id: str,
    goal_type: str,
    *,
    db: AsyncSession,
):
    """Retorna o Goal vigente como response tipada (qualquer goal type)."""
    goal = await get_current_goal(workspace_id, goal_type, db=db)
    if goal is None:
        return None
    cls = _GOAL_TYPE_CLASSES.get(goal_type)
    if cls is None:
        return None
    resp_cls, inp_cls, der_cls = cls
    names = await _resolve_author_names(
        {goal.created_by} if goal.created_by else set(), db=db
    )
    return _goal_to_typed_response(
        goal,
        response_cls=resp_cls,
        inputs_cls=inp_cls,
        derived_cls=der_cls,
        created_by_name=names.get(goal.created_by or ""),
    )


async def get_goal_history_typed(
    workspace_id: str,
    goal_type: str,
    *,
    db: AsyncSession,
) -> list:
    """Histórico tipado de qualquer goal type."""
    goals = await get_goal_history(workspace_id, goal_type, db=db)
    cls = _GOAL_TYPE_CLASSES.get(goal_type)
    if cls is None:
        return []
    resp_cls, inp_cls, der_cls = cls
    ids = {g.created_by for g in goals if g.created_by}
    names = await _resolve_author_names(ids, db=db)
    return [
        _goal_to_typed_response(
            g,
            response_cls=resp_cls,
            inputs_cls=inp_cls,
            derived_cls=der_cls,
            created_by_name=names.get(g.created_by or ""),
        )
        for g in goals
    ]


async def get_latest_report_patrimonio_liquido(
    workspace_id: str,
    *,
    db: AsyncSession,
) -> Optional[float]:
    """Último `patrimonio_liquido` não nulo do workspace (por `created_at`)."""
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
    return float(row)


__all__ = [
    "compute_if_derived",
    "compute_aporte_derived",
    "compute_dolar_derived",
    "compute_alocacao_derived",
    "get_current_goal",
    "get_goal_history",
    "create_if_goal_version",
    "create_goal_version",
    "get_current_goal_typed",
    "get_goal_history_typed",
    "get_latest_report_patrimonio_liquido",
    "_goal_to_response",
    "_goal_to_typed_response",
    "DEFAULT_CAMBIO_BRL_USD",
]
