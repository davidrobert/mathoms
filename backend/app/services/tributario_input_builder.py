"""Agrega inputs do ``CascataInput`` a partir de DB + artifacts (ADR-236 §D2/§D4; A17 L1 plumbing)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as SyncSession

from backend.app.application.informes.informe_query import InformeQuery
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun
from backend.app.models.workspace import Workspace
from backend.app.schemas.business_profile import BusinessProfile
from pipeline.domain.models.transaction import Money
from pipeline.domain.services.fiscal_source import FiscalSource
from pipeline.domain.services.tributario.cascata_calculator import (
    CascataInput,
    FinanceiroPJSnapshot,
    PrevidenciaSnapshot,
)
from pipeline.domain.services.tributario.irpf_renda_tributavel import (
    extract_renda_tributavel_pf,
)

#: Stages legacy + descritivos (janela compat F9.2→F9.6 · ADR-093).
_E3_STAGES: tuple[str, ...] = ("E3", "reconcile_transactions")
_E4_STAGES: tuple[str, ...] = ("E4", "categorize_transactions")
_IRPF_STAGES: tuple[str, ...] = ("extract_irpf_full",)


@dataclass(frozen=True)
class _PJTotals:
    # Totais PJ agregados da última run E4 (BRL nominais sobre todo o período).
    pro_labore: Decimal
    lucros_distribuidos: Decimal
    das_simples: Decimal
    iss: Decimal
    folha_pj: Decimal
    receita_pj: Decimal
    n_meses: int

    @classmethod
    def empty(cls) -> "_PJTotals":
        zero = Decimal("0")
        return cls(zero, zero, zero, zero, zero, zero, 0)


def build_cascata_input_sync(workspace_id: str, *, db: SyncSession) -> CascataInput:
    """Constrói ``CascataInput`` a partir de DB+artifacts (ADR-236 §D4 + A17 L1+L2)."""
    bp = _load_business_profile(workspace_id, db=db)
    irpf_total = _load_irpf_renda_tributavel(workspace_id, db=db)
    pj_totals = _load_pj_totals(workspace_id, db=db)
    imoveis = _load_imoveis(workspace_id, db=db)
    previdencia = _load_previdencia_snapshot(workspace_id, db=db)
    financeiro_pj = _load_financeiro_pj_snapshot(workspace_id, db=db)
    return _assemble_input(bp, irpf_total, pj_totals, imoveis, previdencia, financeiro_pj)


def _load_previdencia_snapshot(
    workspace_id: str, *, db: SyncSession
) -> Optional[PrevidenciaSnapshot]:
    """ADR-238 plumbing E5: snapshot agregado de informes previdência via FiscalSource."""
    informes = InformeQuery(db).list_previdencia(workspace_id)
    if not informes:
        return None
    summaries = FiscalSource.from_informes(informes).previdencia_summaries()
    if not summaries:
        return None
    pgbl = [s for s in summaries if s.plano_tipo == "pgbl"]
    vgbl_n = sum(1 for s in summaries if s.plano_tipo == "vgbl")
    return PrevidenciaSnapshot(
        planos_pgbl_count=len(pgbl),
        planos_vgbl_count=vgbl_n,
        aporte_pgbl_realizado_anual=Money.brl(
            sum((s.contribuicoes_anuais for s in pgbl), Decimal("0"))
        ),
        saldo_total_31_12=Money.brl(sum((s.saldo_31_12 for s in summaries), Decimal("0"))),
    )


def _load_financeiro_pj_snapshot(
    workspace_id: str, *, db: SyncSession
) -> Optional[FinanceiroPJSnapshot]:
    """A17 L2 P3 (ADR-238 D5 · ADR-236 cascata): snapshot de informes financeiro_pj via FiscalSource."""
    informes = InformeQuery(db).list_for_workspace(workspace_id, tipo_informe="financeiro_pj")
    if not informes:
        return None
    summaries = FiscalSource.from_informes(informes).financeiro_pj_summaries()
    return _build_financeiro_pj_snapshot(summaries) if summaries else None


def _build_financeiro_pj_snapshot(summaries: list) -> FinanceiroPJSnapshot:
    regimes = [s.regime_tributario for s in summaries]
    return FinanceiroPJSnapshot(
        informes_count=len(summaries),
        receita_bruta_total_anual=Money.brl(
            sum((s.receita_bruta_anual for s in summaries), Decimal("0"))
        ),
        retencoes_totais_anuais=Money.brl(
            sum((s.retencoes_totais_anuais for s in summaries), Decimal("0"))
        ),
        regime_declarado=max(set(regimes), key=regimes.count),
        ano_base_coberto=max(s.ano_base for s in summaries),
    )


# =============================================================================
# Carregadores
# =============================================================================


def _load_business_profile(workspace_id: str, *, db: SyncSession) -> Optional[BusinessProfile]:
    # Optional retorno: workspace recém-criado / payload corrompido degrada
    # gracefully — calculator vai retornar fallback ``perfil_incompleto``.
    ws = db.get(Workspace, workspace_id)
    if ws is None or not ws.business_profile_json:
        return None
    try:
        return BusinessProfile(**ws.business_profile_json)
    except (ValueError, TypeError):
        return None


def _load_irpf_renda_tributavel(workspace_id: str, *, db: SyncSession) -> Money:
    irpf_artifact = _read_latest_workspace_artifact(workspace_id, _IRPF_STAGES, db=db)
    return extract_renda_tributavel_pf(irpf_artifact).total


def _load_pj_totals(workspace_id: str, *, db: SyncSession) -> _PJTotals:
    run_id = _latest_run_id(workspace_id, db=db)
    if run_id is None:
        return _PJTotals.empty()
    receita_totals = _category_totals(_read_run_artifact(run_id, _E4_STAGES, "receitas", db=db))
    despesa_totals = _category_totals(_read_run_artifact(run_id, _E4_STAGES, "despesas", db=db))
    n_meses = _count_months(_read_run_artifact(run_id, _E4_STAGES, "fluxo_mensal_detalhado", db=db))
    return _build_pj_totals(receita_totals, despesa_totals, n_meses)


def _build_pj_totals(
    receita_totals: dict[str, Any], despesa_totals: dict[str, Any], n_meses: int
) -> _PJTotals:
    return _PJTotals(
        pro_labore=_pos_dec(receita_totals.get("pro_labore")),
        lucros_distribuidos=_pos_dec(receita_totals.get("lucros_distribuidos")),
        das_simples=_pos_dec(despesa_totals.get("das_simples")),
        iss=_pos_dec(despesa_totals.get("iss")),
        folha_pj=_pos_dec(despesa_totals.get("folha_pj")),
        receita_pj=_pos_dec(receita_totals.get("receita_pj"))
        + _pos_dec(receita_totals.get("pro_labore"))
        + _pos_dec(receita_totals.get("lucros_distribuidos")),
        n_meses=n_meses,
    )


def _load_imoveis(workspace_id: str, *, db: SyncSession) -> tuple[int, Decimal]:
    """Retorna ``(imoveis_alugados_count, receita_aluguel_anual_brl)`` da última run E4."""
    run_id = _latest_run_id(workspace_id, db=db)
    if run_id is None:
        return 0, Decimal("0")
    patrimonio = _read_run_artifact(run_id, _E4_STAGES, "patrimonio", db=db)
    return _extract_imoveis(patrimonio)


def _extract_imoveis(patrimonio: Optional[dict] = None) -> tuple[int, Decimal]:
    if not isinstance(patrimonio, dict):
        return 0, Decimal("0")
    imoveis = patrimonio.get("dados", {}).get("imoveis_investimento", []) or []
    if not isinstance(imoveis, list):
        return 0, Decimal("0")
    aluguel_anual = sum(
        _pos_dec(item.get("receita_aluguel_anual_brl"))
        for item in imoveis
        if isinstance(item, dict)
    )
    return len(imoveis), aluguel_anual


# =============================================================================
# Montagem do CascataInput
# =============================================================================


def _pj_fields(pj: _PJTotals) -> dict:
    annual = Decimal("12") / Decimal(pj.n_meses) if pj.n_meses else Decimal("0")
    monthly = Decimal(1) / Decimal(pj.n_meses) if pj.n_meses else Decimal("0")
    return {
        "receita_pj_anual": Money.brl(pj.receita_pj * annual),
        "pro_labore_mensal": Money.brl(pj.pro_labore * monthly),
        "lucros_distribuidos_mensal": Money.brl(pj.lucros_distribuidos * monthly),
        "folha_pj_mensal": Money.brl(pj.folha_pj * monthly),
        "das_pago_mensal": Money.brl(pj.das_simples * monthly),
        "iss_pago_mensal": Money.brl(pj.iss * monthly),
    }


def _bp_fields(bp: Optional[BusinessProfile] = None) -> dict:
    # ``bp=None`` quando workspace sem perfil → CascataInput cai em fallback "perfil_incompleto".
    return {
        "regime": bp.regime if bp else None,
        "anexo_simples": bp.anexo_simples if bp else None,
        "iss_aliquota_pct": _iss_aliquota(bp),
        "tipo_declaracao_ir": _tipo_declaracao(bp),
    }


def _assemble_input(
    # ``bp`` Optional: workspace sem perfil → calculator fallback "perfil_incompleto".
    bp: Optional[BusinessProfile],
    irpf_total: Money,
    pj: _PJTotals,
    imoveis: tuple[int, Decimal],
    previdencia: Optional[PrevidenciaSnapshot] = None,
    financeiro_pj: Optional[FinanceiroPJSnapshot] = None,
) -> CascataInput:
    return CascataInput(
        outras_rendas_tributaveis_pf_anual=irpf_total,
        imoveis_alugados_count=imoveis[0],
        receita_aluguel_anual=Money.brl(imoveis[1]),
        previdencia_snapshot=previdencia,
        financeiro_pj_snapshot=financeiro_pj,
        **_bp_fields(bp),
        **_pj_fields(pj),
    )


def _iss_aliquota(bp: Optional[BusinessProfile] = None) -> Optional[Decimal]:
    if bp is None or bp.iss_aliquota_pct is None:
        return None
    return Decimal(str(bp.iss_aliquota_pct))


def _tipo_declaracao(bp: Optional[BusinessProfile] = None) -> str:
    if bp is None or bp.tipo_declaracao_ir is None:
        return "completa"
    return bp.tipo_declaracao_ir


# =============================================================================
# DB helpers
# =============================================================================


def _latest_run_id(workspace_id: str, *, db: SyncSession) -> Optional[str]:
    return db.execute(
        select(PipelineRun.id)
        .where(PipelineRun.workspace_id == workspace_id)
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _read_run_artifact(
    pipeline_run_id: str, stages: tuple[str, ...], artifact_key: str, *, db: SyncSession
) -> Optional[dict]:
    row = (
        db.query(PipelineArtifact)
        .filter(
            PipelineArtifact.pipeline_run_id == pipeline_run_id,
            PipelineArtifact.stage.in_(stages),
            PipelineArtifact.artifact_key == artifact_key,
        )
        .order_by(PipelineArtifact.created_at.desc(), PipelineArtifact.id.desc())
        .first()
    )
    return row.content_json if row else None


def _read_latest_workspace_artifact(
    workspace_id: str, stages: tuple[str, ...], *, db: SyncSession
) -> Optional[dict]:
    row = (
        db.query(PipelineArtifact)
        .filter(
            PipelineArtifact.workspace_id == workspace_id,
            PipelineArtifact.stage.in_(stages),
        )
        .order_by(PipelineArtifact.created_at.desc(), PipelineArtifact.id.desc())
        .first()
    )
    return row.content_json if row else None


# =============================================================================
# Parsers
# =============================================================================


def _category_totals(artifact: Optional[dict] = None) -> dict[str, Any]:
    # Optional `artifact` permite passar None do `_read_*` sem checagem upstream.
    if not isinstance(artifact, dict):
        return {}
    totals = artifact.get("totais_por_categoria")
    return totals if isinstance(totals, dict) else {}


def _count_months(fluxo: Optional[dict] = None) -> int:
    # Optional `fluxo` segue mesmo padrão de `_category_totals`.
    if not isinstance(fluxo, dict):
        return 0
    meses = fluxo.get("meses_ordenados")
    return len(meses) if isinstance(meses, list) else 0


def _pos_dec(raw: Any) -> Decimal:
    """Coerce para ``Decimal`` não-negativo; NaN/None/garbage → 0."""
    if raw is None or isinstance(raw, bool):
        return Decimal("0")
    try:
        val = Decimal(str(raw))
    except Exception:
        return Decimal("0")
    return val if val > 0 else Decimal("0")
