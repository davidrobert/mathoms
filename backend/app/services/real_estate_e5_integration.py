"""Integração P-B (ADR-216) — popula `e5_data['real_estate']` a partir do DB + adapter."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.property_identity import PropertyIdentity, WorkspacePropertyOverride
from backend.app.services.real_estate_adapter import (
    CascadeSources,
    E4ReceitaAluguelEntry,
    IRPFAluguelEntry,
    calculate_for_workspace,
)
from pipeline.domain.services.real_estate_metrics_payload import result_to_payload

_ZERO = Decimal("0")


def populate_real_estate(
    *,
    workspace_id: str,
    e5_data: dict,
    irpf_payload: dict | None,
    db: Session,
    as_of_date: date | None = None,
    informe_payloads: Sequence[dict] | None = None,
    baseline_payload: dict | None = None,
) -> dict | None:
    """Calcula payload `real_estate` (None quando workspace sem property_identity)."""
    identities = _load_identities(db, workspace_id)
    if not identities:
        return None
    return result_to_payload(
        _calculate(
            db, identities, e5_data, irpf_payload, informe_payloads, as_of_date, baseline_payload
        )
    )


def _calculate(
    db: Session,
    identities: list[PropertyIdentity],
    e5_data: dict,
    irpf_payload: dict | None,
    informe_payloads: Sequence[dict] | None,
    as_of_date: date | None,
    baseline_payload: dict | None,
):
    """Resolve cascade D9 + chama service puro (boundary backend/ adapter)."""
    workspace_id = identities[0].workspace_id
    return calculate_for_workspace(
        db,
        identities=identities,
        overrides=_load_overrides(db, workspace_id),
        valor_by_property=_valor_by_property(identities, baseline_payload),
        sources=_build_cascade_sources(irpf_payload, e5_data, informe_payloads, identities),
        patrimonio_liquido=_to_decimal(_get_path(e5_data, "patrimonio", "liquido")),
        as_of_date=as_of_date or date.today(),
    )


def _load_identities(db: Session, workspace_id: str) -> list[PropertyIdentity]:
    stmt = (
        select(PropertyIdentity)
        .where(PropertyIdentity.workspace_id == workspace_id)
        .order_by(PropertyIdentity.first_seen_year.desc(), PropertyIdentity.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


def _load_overrides(db: Session, workspace_id: str) -> dict[str, WorkspacePropertyOverride]:
    stmt = select(WorkspacePropertyOverride).where(
        WorkspacePropertyOverride.workspace_id == workspace_id
    )
    return {o.property_id: o for o in db.execute(stmt).scalars().all()}


def _valor_by_property(
    identities: list[PropertyIdentity],
    baseline_payload: dict | None,
) -> dict[str, Decimal]:
    """Valor-por-imóvel do baseline E1.5c consolidado (join por property_id estável).

    Lê `imoveis_consolidados[].valores_31_12` — já deduplicado (ADR-246, sem
    double-count de comunhão) e chaveado por ano-base (ADR-274). É a mesma fonte
    que gerou os PropertyIdentity via property_identity_enricher, então o
    `property_id` casa por construção — sem re-matching frágil por codigo_rfb/role.
    """
    by_property: dict[str, Decimal] = {ident.id: _ZERO for ident in identities}
    if not baseline_payload:
        return by_property
    known = set(by_property)
    for imovel in baseline_payload.get("imoveis_consolidados") or []:
        pid = imovel.get("property_id")
        if pid in known:
            by_property[pid] += _imovel_valor_ano_base(imovel)
    return by_property


def _imovel_valor_ano_base(imovel: dict) -> Decimal:
    """Valor 31/12 do imóvel no ano-base (maior ano numérico em `valores_31_12`)."""
    vals = imovel.get("valores_31_12") or {}
    years = [y for y in vals if str(y).isdigit()]
    if not years:
        return _ZERO
    return _to_decimal(vals[max(years, key=int)])


def _extract_irpf_entries(irpf_payload: dict | None) -> tuple[IRPFAluguelEntry, ...]:
    """Filtra rendimentos_pf válidos do IRPF para CascadeSources."""
    if not irpf_payload:
        return ()
    out: list[IRPFAluguelEntry] = []
    for r in irpf_payload.get("rendimentos_pf") or []:
        valor = _to_decimal(r.get("valor_brl"))
        if valor <= _ZERO:
            continue
        out.append(
            IRPFAluguelEntry(
                pagador_nome=str(r.get("pagador_nome") or "(sem nome)"),
                pagador_cpf_masked=r.get("pagador_cpf_masked"),
                valor_brl=valor,
                ir_recolhido_brl=_to_decimal(r.get("ir_recolhido_brl")),
            )
        )
    return tuple(out)


def _extract_e4_aluguel(e5_data: dict) -> E4ReceitaAluguelEntry | None:
    """Lê receita_aluguel agregada do fluxo_caixa (E4)."""
    fluxo = e5_data.get("fluxo_caixa") or {}
    por_fonte = fluxo.get("receitas_por_fonte") or {}
    valor = _to_decimal(por_fonte.get("receita_aluguel"))
    n_meses = len(((fluxo.get("receita_despesa_mensal_detalhado") or {}).get("labels")) or []) or 0
    if valor <= _ZERO or n_meses <= 0:
        return None
    return E4ReceitaAluguelEntry(valor_total_brl=valor, n_meses_periodo=n_meses)


def _build_cascade_sources(
    irpf_payload: dict | None,
    e5_data: dict,
    informe_payloads: Sequence[dict] | None,
    identities: list[PropertyIdentity],
) -> CascadeSources:
    """Constrói CascadeSources de Informe (#1) + IRPF (#2) + E4 (#3) — ADR-216 D9."""
    return CascadeSources(
        informe_imobiliaria_by_property=_informe_by_property(informe_payloads, identities),
        irpf_carne_leao=_extract_irpf_entries(irpf_payload),
        e4_receita_aluguel_total=_extract_e4_aluguel(e5_data),
    )


def _informe_by_property(
    informe_payloads: Sequence[dict] | None,
    identities: list[PropertyIdentity],
) -> dict[str, dict[str, Any]]:
    """Agrupa imóveis de informes por property_id (cascade D9 #1 · ADR-216)."""
    if not informe_payloads:
        return {}
    by_property: dict[str, dict[str, Decimal]] = {}
    for payload in informe_payloads:
        for imovel in payload.get("imoveis") or []:
            ident = _match_property_to_informe_imovel(identities, imovel)
            if ident is not None:
                _accumulate_informe_imovel(by_property, ident.id, imovel)
    return {pid: dict(agg) for pid, agg in by_property.items()}


def _accumulate_informe_imovel(
    by_property: dict[str, dict[str, Decimal]], property_id: str, imovel: dict
) -> None:
    """Soma aluguel/IR de um imóvel-do-informe ao agregado (n informes → mesma property)."""
    agg = by_property.setdefault(
        property_id, {"aluguel_bruto_anual": _ZERO, "ir_retido_anual": _ZERO}
    )
    agg["aluguel_bruto_anual"] += _to_decimal(imovel.get("aluguel_bruto_anual"))
    agg["ir_retido_anual"] += _to_decimal(imovel.get("ir_retido_anual"))


def _match_property_to_informe_imovel(
    identities: Iterable[PropertyIdentity], imovel: dict
) -> PropertyIdentity | None:
    """Match heurístico imóvel-do-informe → PropertyIdentity por endereço (substring)."""
    endereco_informe = (imovel.get("endereco") or "").strip().lower()
    if not endereco_informe:
        return None
    candidates = [i for i in identities if (i.endereco_canonical or "").strip()]
    for ident in candidates:
        canonical = ident.endereco_canonical.strip().lower()
        if canonical in endereco_informe or endereco_informe in canonical:
            return ident
    return None


def _get_path(data: dict, *keys: str) -> Any:
    cur: Any = data
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _to_decimal(v: Any) -> Decimal:
    if v is None or isinstance(v, bool):
        return _ZERO
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, str)):
        try:
            return Decimal(v)
        except Exception:
            return _ZERO
    if isinstance(v, float):
        return Decimal(str(v))
    return _ZERO


__all__ = ["populate_real_estate"]
