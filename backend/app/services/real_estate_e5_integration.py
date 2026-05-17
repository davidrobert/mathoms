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
) -> dict | None:
    """Calcula payload `real_estate` (None quando workspace sem property_identity)."""
    identities = _load_identities(db, workspace_id)
    if not identities:
        return None
    return result_to_payload(
        _calculate(
            db, identities, e5_data, irpf_payload, informe_payloads, workspace_id, as_of_date
        )
    )


def _calculate(
    db: Session,
    identities: list[PropertyIdentity],
    e5_data: dict,
    irpf_payload: dict | None,
    informe_payloads: Sequence[dict] | None,
    workspace_id: str,
    as_of_date: date | None,
):
    """Resolve cascade D9 + chama service puro (boundary backend/ adapter)."""
    return calculate_for_workspace(
        db,
        identities=identities,
        overrides=_load_overrides(db, workspace_id),
        bens_direitos_by_property=_bens_direitos_by_property(identities, irpf_payload),
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


def _bens_direitos_by_property(
    identities: list[PropertyIdentity],
    irpf_payload: dict | None,
) -> dict[str, Decimal]:
    """Soma valor IRPF por property_id usando matching (titular_key, codigo_rfb, endereco)."""
    if not irpf_payload:
        return {ident.id: _ZERO for ident in identities}

    bens = irpf_payload.get("bens_direitos") or []
    by_property: dict[str, Decimal] = {ident.id: _ZERO for ident in identities}
    for bem in bens:
        codigo = (bem.get("codigo_rfb") or "").strip()
        descricao = (bem.get("descricao") or "").strip().lower()
        valor = _to_decimal(bem.get("valor_brl"))
        membro = (bem.get("membro_key") or "").strip()
        match = _match_identity(identities, codigo=codigo, descricao=descricao, membro=membro)
        if match is not None:
            by_property[match.id] += valor
    return by_property


def _match_identity(
    identities: list[PropertyIdentity], *, codigo: str, descricao: str, membro: str
) -> PropertyIdentity | None:
    """Match por (codigo_rfb, titular_key) + substring endereco_canonical (ADR-215 P2 espelho)."""
    cands = [
        i for i in identities if i.codigo_rfb == codigo and (not membro or i.titular_key == membro)
    ]
    if len(cands) <= 1:
        return cands[0] if cands else None
    for ident in cands:
        endereco = (ident.endereco_canonical or "").lower()
        if endereco and (endereco in descricao or descricao in endereco):
            return ident
    return cands[0]


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
