"""``ScoreReader`` — recompute on-read de score em artifacts E5 antigos (ADR-217 D6)."""

from __future__ import annotations

from typing import Any

from pipeline.domain.services.financial_score_calculator import (
    FinancialScoreCalculator,
    FinancialScoreConfig,
)


def has_canonical_score(score: dict[str, Any] | None) -> bool:
    """True quando o score já está no formato ADR-217 (score_version presente)."""
    if not isinstance(score, dict):
        return False
    return "score_version" in score and "componentes" in score


def ensure_score_present(e5_payload: dict[str, Any]) -> dict[str, Any]:
    """Retorna payload com score canônico — recomputa se ausente/legado (ADR-217)."""
    score = e5_payload.get("score")
    if has_canonical_score(score):
        return e5_payload
    recomputed = _recompute_from_legacy(e5_payload)
    if recomputed is None:
        return e5_payload
    enriched = dict(e5_payload)
    enriched["score"] = recomputed
    return enriched


def _recompute_from_legacy(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Recompute usando inputs canônicos do payload. None se inputs ausentes."""
    ratios = payload.get("ratios") or {}
    patrimonio = payload.get("patrimonio") or {}
    goals = payload.get("goals") or {}
    if not ratios and not patrimonio:
        return None
    calculator = FinancialScoreCalculator(FinancialScoreConfig.default())
    return calculator.calculate(ratios=ratios, patrimonio=patrimonio, goals=goals)
