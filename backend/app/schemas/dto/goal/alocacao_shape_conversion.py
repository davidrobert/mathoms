"""Conversão on-read (permanente, não migration) de inputs de alocação-alvo v1/órfão → v2 (ADR-141 §Emenda).

Módulo ÚNICO de conversão — consumido pelo mapper da API e pelo adapter
E5 (duas tabelas divergem em 6 meses). Detecção por fingerprint de
key-set com precedência sobre ``meta_version``: as rows do seed antigo
carimbam ``meta_version: 1`` num shape que não é v1 nem v2.
"""

from __future__ import annotations

from typing import Literal, Mapping, Optional

from backend.app.schemas.dto.goal.alocacao import (
    ALOCACAO_V2_CLASS_FIELDS,
    AlocacaoGoalDerivedV2,
    AlocacaoGoalInputsV2,
)

AlocacaoShape = Literal["v1", "orphan", "v2", "unknown"]

_V1_FINGERPRINT = frozenset(
    {"renda_fixa_pct", "acoes_pct", "imoveis_reits_pct", "liquidez_usd_pct"}
)
_ORPHAN_FINGERPRINT = frozenset({"rf_pct", "rv_pct", "alternativos_pct"})
_V2_FINGERPRINT = frozenset(ALOCACAO_V2_CLASS_FIELDS)

# Splits heurísticos da ADR-141 (§Migração + emenda item 5).
_RF_SPLIT = (("rf_pos_pct", 0.50), ("rf_pre_pct", 0.25), ("rf_ipca_pct", 0.25))
_USD_SPLIT = (("acoes_int_pct", 0.70), ("caixa_pct", 0.30))
_RV_SPLIT = (("acoes_br_pct", 0.70), ("acoes_int_pct", 0.30))

_REBALANCEAMENTO_LEGADO: tuple[tuple[str, str], ...] = (
    ("aporte", "por_aporte"),
    ("10", "trigger_10pct"),
    ("5", "trigger_5pct"),
    ("trimestr", "trimestral"),
    ("semestr", "semestral"),
    ("anual", "anual"),
    ("ano", "anual"),
)


def detect_alocacao_shape(inputs: Optional[Mapping[str, object]] = None) -> AlocacaoShape:
    """Fingerprint por key-set; precedência sobre ``meta_version`` (que mente no seed)."""
    keys = set(inputs or {})
    if _V2_FINGERPRINT <= keys:
        return "v2"
    if _V1_FINGERPRINT & keys:
        return "v1"
    if _ORPHAN_FINGERPRINT & keys:
        return "orphan"
    return "unknown"


def _num(inputs: Mapping[str, object], key: str) -> float:
    value = inputs.get(key)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _inteiros_residuo_rf_pos(pesos: dict[str, float]) -> dict[str, int]:
    """Inteiros com Σ=100 exato: floor por classe, resíduo integral em rf_pos_pct."""
    # Decisão financial-planner 2026-07-08 (emenda ADR-141 item 5): viés
    # pró-pós-fixado é o default conservador (Selic é o piso da RF BR) —
    # deliberadamente NÃO é largest-remainder por fração.
    soma = sum(pesos.values())
    if soma <= 0:
        return {campo: 0 for campo in ALOCACAO_V2_CLASS_FIELDS}
    normalizados = {k: v / soma * 100.0 for k, v in pesos.items()}
    inteiros = {k: int(normalizados[k]) for k in ALOCACAO_V2_CLASS_FIELDS}
    inteiros["rf_pos_pct"] += 100 - sum(inteiros.values())
    return inteiros


def _spread(pesos: dict[str, float], origem: float, split: tuple[tuple[str, float], ...]) -> None:
    for campo, fracao in split:
        pesos[campo] += origem * fracao


def _pesos_v1(inputs: Mapping[str, object]) -> dict[str, float]:
    pesos = {campo: 0.0 for campo in ALOCACAO_V2_CLASS_FIELDS}
    _spread(pesos, _num(inputs, "renda_fixa_pct"), _RF_SPLIT)
    pesos["acoes_br_pct"] += _num(inputs, "acoes_pct")
    pesos["fiis_pct"] += _num(inputs, "imoveis_reits_pct")
    _spread(pesos, _num(inputs, "liquidez_usd_pct"), _USD_SPLIT)
    return pesos


def _pesos_orphan(inputs: Mapping[str, object]) -> dict[str, float]:
    # alternativos_pct → fiis integral; caixa = 0 (aprovado financial-planner 2026-07-08).
    pesos = {campo: 0.0 for campo in ALOCACAO_V2_CLASS_FIELDS}
    _spread(pesos, _num(inputs, "rf_pct"), _RF_SPLIT)
    _spread(pesos, _num(inputs, "rv_pct"), _RV_SPLIT)
    pesos["fiis_pct"] += _num(inputs, "alternativos_pct")
    return pesos


def map_rebalanceamento_legado(texto: Optional[str] = None) -> str:
    """String livre do v1 ('Quando desviar >5%') → enum v2; fallback = default AUVP."""
    normalizado = (texto or "").strip().lower()
    for fragmento, modo in _REBALANCEAMENTO_LEGADO:
        if fragmento in normalizado:
            return modo
    return "por_aporte"


def _instrumentos_v1(inputs: Mapping[str, object]) -> Optional[dict[str, str]]:
    out = {}
    rf = inputs.get("instrumentos_rf")
    rv = inputs.get("instrumentos_rv")
    if isinstance(rf, str) and rf.strip():
        out["renda_fixa"] = rf
    if isinstance(rv, str) and rv.strip():
        out["renda_variavel"] = rv
    return out or None


def convert_alocacao_inputs_to_v2(
    inputs: Optional[Mapping[str, object]] = None,
) -> tuple[Optional[dict], Optional[str]]:
    """Retorna ``(inputs_v2, converted_from)`` — ``"1"``/``"orphan"``/``None``; sem shape utilizável → ``(None, None)``."""
    shape = detect_alocacao_shape(inputs)
    if shape == "v2":
        return dict(inputs or {}), None
    if shape == "unknown":
        return None, None
    assert inputs is not None
    pesos = _pesos_v1(inputs) if shape == "v1" else _pesos_orphan(inputs)
    if sum(pesos.values()) <= 0:
        return None, None
    return _montar_v2(inputs, pesos), ("1" if shape == "v1" else "orphan")


def _montar_v2(inputs: Mapping[str, object], pesos: dict[str, float]) -> dict:
    v2: dict = dict(_inteiros_residuo_rf_pos(pesos))
    legado = inputs.get("rebalanceamento")
    v2["rebalanceamento_modo"] = map_rebalanceamento_legado(
        legado if isinstance(legado, str) else None
    )
    instrumentos = _instrumentos_v1(inputs)
    if instrumentos:
        v2["instrumentos"] = instrumentos
    return v2


def compute_alocacao_derived_v2(inputs: AlocacaoGoalInputsV2) -> AlocacaoGoalDerivedV2:
    """Derived write-time v2 magro (ADR-141 emenda item 4) — comparação atual-vs-alvo é run-time no E5."""
    return AlocacaoGoalDerivedV2(
        soma_percentuais=round(sum(getattr(inputs, c) for c in ALOCACAO_V2_CLASS_FIELDS), 2)
    )
