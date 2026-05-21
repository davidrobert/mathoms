"""Reconciliação fuzzy IRPF G02 ↔ vehicles (ADR-239 D3 + D4; gate triplo 2026-05-21)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Literal, Optional

# ===========================================================================
# Config (ADR-097 D3 — value object tipado)
# ===========================================================================


@dataclass(frozen=True)
class ReconciliationConfig:
    """Parâmetros calibráveis (gate financial-planner 2026-05-21: dual threshold)."""

    auto_merge_threshold: float = 0.90  # acima → FK preenchida
    review_threshold: float = 0.75  # entre review_threshold e auto_merge → needs_review
    tiebreaker_gap_min: float = 0.05  # top1-top2 mínimo para auto_merge
    ano_modelo_boost: float = 0.10  # ano em descricao bate com ano_modelo ±1
    ano_modelo_penalty: float = 0.15  # diferença ≥ 2 anos


# ===========================================================================
# Resultado tipado
# ===========================================================================


ReconciliationOutcome = Literal["auto_merge", "needs_review", "no_candidate", "stale_cleared"]


@dataclass(frozen=True)
class ReconciliationCandidate:
    """Veículo candidato pré-decisão (audit trail)."""

    vehicle_id: str
    score: float
    boosts: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ReconciliationResult:
    """1 entry de baseline.veiculos_consolidados[] reconciliada."""

    baseline_index: int
    outcome: ReconciliationOutcome
    veiculo_id: Optional[str]
    score: float
    candidates: list[ReconciliationCandidate]
    reason: Optional[str] = None


# ===========================================================================
# Normalização (gate financial-planner — agressiva por padrão DENATRAN)
# ===========================================================================


# Expansão de abreviações comuns no G02 do IRPF (string livre do contribuinte).
_ABREVIACOES = {
    "vw": "volkswagen",
    "gm": "chevrolet",
    "mb": "mercedes-benz",
    "fia": "fiat",
}

_ANO_RE = re.compile(r"\b(19|20)\d{2}\b")


def _normalize(text: str) -> str:
    """lowercase + sem acentos + dedupe spaces + expansão abreviações."""
    text = text.strip().lower()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [_ABREVIACOES.get(t, t) for t in text.split()]
    return " ".join(tokens)


def _extract_ano(text: str) -> Optional[int]:
    """Extrai ano embedded (1900-2099); retorna None se nenhum."""
    m = _ANO_RE.search(text)
    return int(m.group(0)) if m else None


# ===========================================================================
# Score fuzzy + boosts
# ===========================================================================


def _strip_ano(text: str) -> str:
    """Remove ano embedded (4 dígitos) — ano é signal separado em boost/penalty."""
    return re.sub(r"\b(19|20)\d{2}\b", "", text).strip()


def _base_score(descricao_norm: str, vehicle_label_norm: str) -> float:
    """Fuzzy ratio de marca+modelo (ano removido — tratado separadamente em adjustment)."""
    return SequenceMatcher(None, _strip_ano(descricao_norm), _strip_ano(vehicle_label_norm)).ratio()


def _apply_ano_adjustment(
    base_score: float,
    ano_descricao: int | None = None,
    ano_modelo: int = 0,
    cfg: ReconciliationConfig = ReconciliationConfig(),
) -> tuple[float, dict]:
    """Boost/penalty pelo ano embedded em descricao vs ano_modelo CRLV."""
    if ano_descricao is None or ano_modelo == 0:
        return base_score, {}
    diff = abs(ano_descricao - ano_modelo)
    if diff <= 1:
        return min(1.0, base_score + cfg.ano_modelo_boost), {"ano_boost": cfg.ano_modelo_boost}
    if diff >= 2:
        return max(0.0, base_score - cfg.ano_modelo_penalty), {
            "ano_penalty": -cfg.ano_modelo_penalty
        }
    return base_score, {}


def _score_candidate(
    baseline_item: dict, vehicle: dict, cfg: ReconciliationConfig
) -> ReconciliationCandidate:
    """Computa score de 1 candidato (fuzzy descricao × marca+modelo) + ano adjustment."""
    descricao_norm = _normalize(baseline_item.get("descricao", ""))
    label = f"{vehicle.get('marca', '')} {vehicle.get('modelo', '')}"
    label_norm = _normalize(label)
    base = _base_score(descricao_norm, label_norm)
    ano_desc = _extract_ano(baseline_item.get("descricao", ""))
    ano_modelo = int(vehicle.get("ano_modelo", 0))
    final, boosts = _apply_ano_adjustment(base, ano_desc, ano_modelo, cfg)
    return ReconciliationCandidate(
        vehicle_id=vehicle["id"], score=final, boosts={**boosts, "base": base}
    )


# ===========================================================================
# Decisão por entry
# ===========================================================================


def _decide_outcome(
    baseline_index: int, candidates: list[ReconciliationCandidate], cfg: ReconciliationConfig
) -> ReconciliationResult:
    """3 outcomes: auto_merge / needs_review / no_candidate."""
    if not candidates:
        return ReconciliationResult(baseline_index, "no_candidate", None, 0.0, [], None)
    ranked = sorted(candidates, key=lambda c: c.score, reverse=True)
    top = ranked[0]
    if top.score < cfg.review_threshold:
        return ReconciliationResult(baseline_index, "no_candidate", None, top.score, ranked, None)
    if top.score >= cfg.auto_merge_threshold and _gap_ok(ranked, cfg):
        return ReconciliationResult(
            baseline_index, "auto_merge", top.vehicle_id, top.score, ranked, None
        )
    return ReconciliationResult(
        baseline_index, "needs_review", None, top.score, ranked, _ambiguity_reason(ranked, cfg)
    )


def _gap_ok(ranked: list[ReconciliationCandidate], cfg: ReconciliationConfig) -> bool:
    """True quando top1 - top2 ≥ gap_min (sem ambiguidade)."""
    if len(ranked) < 2:
        return True
    return (ranked[0].score - ranked[1].score) >= cfg.tiebreaker_gap_min


def _ambiguity_reason(
    ranked: list[ReconciliationCandidate], cfg: ReconciliationConfig
) -> Optional[str]:
    if len(ranked) >= 2 and (ranked[0].score - ranked[1].score) < cfg.tiebreaker_gap_min:
        return f"ambiguous_top_match:gap<{cfg.tiebreaker_gap_min}"
    return f"score_in_review_band:{ranked[0].score:.2f}<{cfg.auto_merge_threshold}"


# ===========================================================================
# Blocking por proprietario (gate financial-planner — reduz N×M)
# ===========================================================================


def _filter_by_proprietario(baseline_proprietario: str, vehicles: list[dict]) -> list[dict]:
    """Bloqueia candidatos do mesmo member_key (gate financial-planner Q3+Q5)."""
    if not baseline_proprietario:
        return list(vehicles)  # sem blocking quando proprietario ausente
    return [v for v in vehicles if v.get("member_key") == baseline_proprietario]


# ===========================================================================
# Eager FK stale check (gate data-engineer Q4)
# ===========================================================================


def _existing_fk_is_stale(
    veiculo_id: str, vehicles_by_id: dict[str, dict], workspace_id: str
) -> bool:
    """True se veiculo_id existente aponta para row inexistente ou outro workspace."""
    v = vehicles_by_id.get(veiculo_id)
    if v is None:
        return True
    return v.get("workspace_id") != workspace_id


# ===========================================================================
# Reconciliador principal
# ===========================================================================


def reconcile_baseline_veiculos(
    baseline: dict,
    vehicles: list[dict],
    workspace_id: str,
    *,
    config: Optional[ReconciliationConfig] = None,
) -> tuple[dict, list[ReconciliationResult]]:
    """Reconcilia ``baseline.veiculos_consolidados[]`` contra ``vehicles`` (ADR-239 D3+D4)."""
    cfg = config or ReconciliationConfig()
    vehicles_by_id = {v["id"]: v for v in vehicles}
    items = baseline.get("veiculos_consolidados") or []
    new_items, results = [], []
    for idx, item in enumerate(items):
        new_item, result = _reconcile_one(idx, item, vehicles, vehicles_by_id, workspace_id, cfg)
        new_items.append(new_item)
        results.append(result)
    return {**baseline, "veiculos_consolidados": new_items}, results


def _check_idempotent(
    idx: int, item: dict, vehicles_by_id: dict[str, dict], workspace_id: str
) -> tuple[dict, ReconciliationResult] | None:
    """Retorna tupla idempotente quando FK existe + válida; None caso contrário."""
    existing_fk = item.get("veiculo_id")
    if existing_fk and not _existing_fk_is_stale(existing_fk, vehicles_by_id, workspace_id):
        return item, ReconciliationResult(
            idx, "auto_merge", existing_fk, 1.0, [], "idempotent_skip"
        )
    return None


def _reconcile_one(
    idx: int,
    item: dict,
    vehicles: list[dict],
    vehicles_by_id: dict[str, dict],
    workspace_id: str,
    cfg: ReconciliationConfig,
) -> tuple[dict, ReconciliationResult]:
    """Processa 1 entry; idempotente (skip se já FK válida)."""
    idempotent = _check_idempotent(idx, item, vehicles_by_id, workspace_id)
    if idempotent is not None:
        return idempotent
    if item.get("veiculo_id"):
        item = {**item, "veiculo_id": None}  # FK stale → limpa
    candidates_pool = _filter_by_proprietario(item.get("proprietario", ""), vehicles)
    candidates = [_score_candidate(item, v, cfg) for v in candidates_pool]
    result = _decide_outcome(idx, candidates, cfg)
    new_item = dict(item)
    new_item["veiculo_id"] = result.veiculo_id if result.outcome == "auto_merge" else None
    return new_item, result


# ===========================================================================
# Audit summary (telemetria)
# ===========================================================================


@dataclass(frozen=True)
class ReconciliationSummary:
    """Sumário agregado para telemetria (sem PII)."""

    total_items: int
    matched_count: int
    needs_review_count: int
    no_candidate_count: int
    stale_fk_cleared_count: int


def summarize(results: list[ReconciliationResult]) -> ReconciliationSummary:
    matched = sum(1 for r in results if r.outcome == "auto_merge" and r.reason != "idempotent_skip")
    review = sum(1 for r in results if r.outcome == "needs_review")
    no_cand = sum(1 for r in results if r.outcome == "no_candidate")
    stale = sum(1 for r in results if r.outcome == "stale_cleared")
    return ReconciliationSummary(
        total_items=len(results),
        matched_count=matched,
        needs_review_count=review,
        no_candidate_count=no_cand,
        stale_fk_cleared_count=stale,
    )
