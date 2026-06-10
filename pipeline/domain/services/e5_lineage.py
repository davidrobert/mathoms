"""Bloco ``_lineage`` dos agregados de decisão E5 além do patrimônio (ADR-279 · A24.l6): reserva de emergência e total investido são baseline/position-fed (chave própria ADR-271, não K4) → ``member_hashes: []`` + inputs reais; despesa total é transaction-fed e emite K4 (``natural_key.hash`` v2, Q3/B8) das txs de E4 ``despesas`` sobreviventes pós-dedup quando a cobertura é total e ≤ teto inline — cobertura parcial (artefatos antigos/sintéticos, ou E4 pré-cutover que só propaga ``transaction_hash`` v1, ADR-278 B4) → ``member_hashes: []`` + ``signals.k4_coverage="partial"`` e a soma verifica pelos inputs por categoria. Views tipadas sobre os dicts serializados — nunca recálculo paralelo (co-design l5)."""

from __future__ import annotations

from typing import Any

from pipeline.domain.lineage_registry import LINEAGE_RULE_REFS
from pipeline.domain.services.lineage_fields import (
    LineageBlock,
    LineageField,
    e5_input_ref,
    lineage_block,
    money_str,
    sorted_inputs,
)
from pipeline.domain.services.patrimonio_lineage import (
    PatrimonioReport,
    componentes_from_report,
    patrimonio_lineage_fields,
)
from pipeline.domain.services.patrimonio_types import MemberIdentity

# Teto de member_hashes inline (co-design l5/l6) — acima disso a saída
# provável é a edge-table artifact_lineage_edge (F5), não decidir aqui.
_INLINE_HASH_CAP = 200
_K4_HASH_VERSION = 2

# Payloads JSON wire-shaped (mesmo padrão de PatrimonioReport na l5) — shape
# canônico dos dicts serializados que cada builder espelha.
ReservaReport = dict[str, Any]
FluxoLegacyDict = dict[str, Any]
InvestimentosLegacyDict = dict[str, Any]
DespesasE4Payload = dict[str, Any]
TransacaoE4 = dict[str, Any]


def build_e5_lineage(
    *,
    patrimonio_report: PatrimonioReport,
    reserva: ReservaReport,
    fluxo_legacy: FluxoLegacyDict,
    investimentos_legacy: InvestimentosLegacyDict,
    despesas_e4: DespesasE4Payload,
    identity: MemberIdentity,
) -> LineageBlock:
    """Funde os fields de patrimônio (l5) + reserva/despesa/investido (l6)."""
    fields = patrimonio_lineage_fields(componentes_from_report(patrimonio_report))
    fields["reserva_emergencia.total_liquida"] = reserva_total_liquida_field(reserva, identity)
    fields["fluxo_caixa.despesa_total"] = despesa_total_field(fluxo_legacy, despesas_e4)
    fields["investimentos.total"] = total_investido_field(investimentos_legacy)
    return lineage_block(fields)


def reserva_total_liquida_field(reserva: ReservaReport, identity: MemberIdentity) -> LineageField:
    """Topologia honesta: a aritmética consumiu os campos do dict ``patrimonio``."""
    refs = [
        e5_input_ref(f"patrimonio.{identity.key_inv_titular}"),
        e5_input_ref("patrimonio.caixa_moeda_estrangeira"),
    ]
    if identity.conjuge_key:
        refs.append(e5_input_ref(f"patrimonio.{identity.key_inv_conjuge}"))
    return {
        "value": money_str(reserva["total_liquida"]),
        "label": "Reserva de emergência — total líquido",
        "transform": "investimentos líquidos por membro + caixa em moeda estrangeira",
        "rule_ref": dict(LINEAGE_RULE_REFS["reserva_emergencia.total_liquida"]),
        "edge_type": "aggregation",
        "member_hashes": [],
        "inputs": sorted_inputs(refs),
    }


def _despesa_refs(fluxo_legacy: FluxoLegacyDict) -> list[dict[str, str]]:
    return [
        e5_input_ref(f"fluxo_caixa.despesas_por_categoria.{categoria}")
        for categoria in fluxo_legacy.get("despesas_por_categoria") or {}
    ]


def despesa_total_field(
    fluxo_legacy: FluxoLegacyDict, despesas_e4: DespesasE4Payload
) -> LineageField:
    refs = _despesa_refs(fluxo_legacy)
    hashes, signals = despesa_member_hashes(despesas_e4)
    signals = {**signals, **conferencia_signals_from_e4(despesas_e4)}
    field: LineageField = {
        "value": money_str(fluxo_legacy["despesa_total"]),
        "label": "Despesa total do período",
        "transform": "soma das despesas por categoria",
        "rule_ref": dict(LINEAGE_RULE_REFS["fluxo_caixa.despesa_total"]),
        "edge_type": "aggregation",
        "member_hashes": hashes,
        "inputs": sorted_inputs(refs),
    }
    if signals:
        field["signals"] = signals
    return field


def total_investido_field(investimentos_legacy: InvestimentosLegacyDict) -> LineageField:
    refs = [
        e5_input_ref(f"investimentos.tabela_classes[{classe['categoria']}].valor")
        for classe in investimentos_legacy.get("tabela_classes") or []
    ]
    return {
        "value": money_str(investimentos_legacy["total"]),
        "label": "Total investido",
        "transform": "soma das classes de ativo da carteira",
        "rule_ref": dict(LINEAGE_RULE_REFS["investimentos.total"]),
        "edge_type": "aggregation",
        "member_hashes": [],
        "inputs": sorted_inputs(refs),
    }


_CONFERENCIA_SIGNAL_KEYS = ("tx_total", "dedup_collapsed", "dedup_review")


def conferencia_signals_from_e4(despesas_e4: DespesasE4Payload) -> dict[str, str]:
    """Propaga sinais de conferência do ``_lineage`` do artefato E4 ``despesas``
    (ADR-279 · A25.l5 N2). Artefato pré-A25 sem o bloco → ``{}`` (popover N2
    degrada para verbo sem número). Valor não-string-int é descartado."""
    e4_lineage = despesas_e4.get("_lineage")
    if not isinstance(e4_lineage, dict):
        return {}
    e4_signals = e4_lineage.get("signals")
    if not isinstance(e4_signals, dict):
        return {}
    return {
        key: e4_signals[key]
        for key in _CONFERENCIA_SIGNAL_KEYS
        if isinstance(e4_signals.get(key), str) and e4_signals[key].isdigit()
    }


def despesa_member_hashes(despesas_e4: DespesasE4Payload) -> tuple[list[str], dict[str, str]]:
    """K4 sobreviventes pós-dedup (Q3/B8) — contrato all-or-nothing: hash
    parcial não vale (soma furaria silenciosamente); teto inline ≤ 200."""
    txs = [tx for cat_txs in (despesas_e4.get("dados") or {}).values() for tx in cat_txs]
    keyed = [_k4_hash(tx) for tx in txs]
    if any(h is None for h in keyed):
        return [], {"k4_coverage": "partial"}
    hashes = sorted(set(keyed))
    if len(hashes) > _INLINE_HASH_CAP:
        return [], {"k4_coverage": "full", "inline_cap": "exceeded"}
    return hashes, {}


def _k4_hash(tx: TransacaoE4) -> str | None:
    """``natural_key.hash`` v2 (K4); ``transaction_hash`` v1 NÃO conta (ADR-278 B4)."""
    natural_key = tx.get("natural_key")
    if not isinstance(natural_key, dict):
        return None
    if natural_key.get("hash_version") != _K4_HASH_VERSION:
        return None
    hash_value = natural_key.get("hash")
    return hash_value if isinstance(hash_value, str) and hash_value else None
