"""``GoalsBundle`` TypedDict consumido pelos stages do pipeline (ADR-180, A10.6)."""

# Substitui o `goals.json` materializado em filesystem (deletado em Sprint A10.6).
# Boundary: este módulo importa apenas ``typing`` — nenhum ``sqlalchemy``/``fastapi``/
# ``celery``. Adapter (``backend/app/services/pipeline_adapter.py``) faz a montagem
# DB→bundle; pipeline lê via ``ctx.load_config("goals.json")``.
#
# Convenção de nomes: as chaves preservam o **shape legado do `goals.json`** para
# manter byte-paridade dos goldens E5/E5.N. ADR-180 propôs renomear semanticamente
# (``aporte``/``if_meta``), mas a lane A10.6 escolheu manter as keys legadas — o
# ganho de clareza não compensa o custo de refatorar 11 sites em E5 + 2 em E5.N
# + 4 em domain services (rejeitada na §Alternativas da ADR-180).

from __future__ import annotations

from typing import Any, Optional, TypedDict


class IFGoalSection(TypedDict, total=False):
    """``independencia_financeira`` — sub-dict do bundle (vem do Goal IF)."""

    _ref: str
    if_meta: Optional[float]
    trs_pct: Optional[float]
    renda_passiva_meta_mensal: Optional[float]
    retorno_real_anual_pct: Optional[float]
    taxa_retirada_segura_classica_pct: float
    _nota_taxa_retirada: str
    _source: str


class AporteGoalSection(TypedDict, total=False):
    """``aportes`` — sub-dict do bundle (vem do Goal APORTE_MENSAL)."""

    _ref: str
    meta_aporte_mensal: Optional[float]
    dia_aporte: Optional[int]
    periodo_inicio: str
    distribuicao: dict[str, float]
    _source: str


class DolarizacaoGoalSection(TypedDict, total=False):
    """``dolarizacao`` — sub-dict do bundle (vem do Goal DOLARIZACAO)."""

    _ref: str
    meta_usd: Optional[float]
    aporte_mensal_brl: Optional[float]
    _source: str


class AlocacaoGoalSection(TypedDict, total=False):
    """``alocacao_alvo`` — sub-dict do bundle (vem do Goal ALOCACAO_ALVO)."""

    renda_fixa_pct: Optional[float]
    acoes_pct: Optional[float]
    imoveis_reits_pct: Optional[float]
    liquidez_usd_pct: Optional[float]
    instrumentos_rf: str
    instrumentos_rv: str
    rebalanceamento: str
    _source: str


class DecisionTop5Projection(TypedDict):
    """Projeção Decision para card S10 (ADR-179, montada em A10.5)."""

    title: str
    rationale: Optional[str]
    impact_1y_brl_cents: Optional[int]
    horizon: str
    status: str


class RiskBubbleProjection(TypedDict):
    """Projeção Risk para bubble chart S9 (ADR-178, montada em A10.5)."""

    name: str
    code: str
    probability: Optional[str]
    impact_level: str
    impact_brl_cents: Optional[int]


class GoalsBundle(TypedDict, total=False):
    """Bundle tipado consumido pelos stages E5/E5.N (ADR-180; total=False — chaves opcionais)."""

    independencia_financeira: IFGoalSection
    aportes: AporteGoalSection
    dolarizacao: DolarizacaoGoalSection
    alocacao_alvo: AlocacaoGoalSection
    # Sub-dicts ainda dict-shaped (sub-tipagem postponed — não bloqueia A10.6).
    seguros: dict[str, Any]
    tributario: dict[str, Any]
    fase_f1f2: dict[str, Any]
    # Projeções A10.5 — sempre presentes (lista vazia se DB vazio).
    top5_decisoes_projection: list[DecisionTop5Projection]
    risks_projection: list[RiskBubbleProjection]
    _adapter_version: int


__all__ = [
    "AlocacaoGoalSection",
    "AporteGoalSection",
    "DecisionTop5Projection",
    "DolarizacaoGoalSection",
    "GoalsBundle",
    "IFGoalSection",
    "RiskBubbleProjection",
]
