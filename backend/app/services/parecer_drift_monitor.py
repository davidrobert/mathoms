"""Drift detection do Parecer sobre a telemetria do ``LLMCallLog`` (A22.l4).

5 sinais por janela ``(prompt_version, model_name)`` vs versão anterior:
confidence Δ e needs_review Δ (banda ``max(floor, 2·SE)`` — honesto com N
pequeno), tokens/custo Δ (±30% fixo), duration p95 Δ (±40%; proxy de reask
storm ADR-292/294), model swap sob a mesma prompt_version (warn imediato).
Observabilidade pura (Should, F3-O4): log estruturado, sem gate, fail-open.
Baseline relativo (``prev_version``); golden da [[A22.l1]] pluga como
``baseline_kind="golden"`` quando destravar. Co-design ``prompt-engineer``
2026-07-06.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.llm_call_log import LLMCallLog
from pipeline.artifact_store import stage_aliases

logger = logging.getLogger("mathoms.llm.parecer_drift")

#: Ambas as formas do stage do parecer (rows legadas + descritivo pós-F9.6).
PARECER_STAGES = stage_aliases("review_finances_holistic")

#: Piso de amostra por janela — abaixo disso proporção não distingue ruído.
MIN_WINDOW_N = 8
#: Rows consideradas por janela (recorte de recência).
WINDOW_LIMIT = 20

CONFIDENCE_FLOOR = 0.10
NEEDS_REVIEW_FLOOR_PP = 0.15
TOKENS_COST_REL_THRESHOLD = 0.30
DURATION_P95_REL_THRESHOLD = 0.40


@dataclass(frozen=True)
class DriftSignal:
    signal: str
    prompt_version: str
    model_name: str
    value: float
    baseline: Optional[float]
    baseline_kind: str
    n_current: int
    n_baseline: int
    verdict: str  # warn | ok | insufficient_data


@dataclass(frozen=True)
class _Window:
    prompt_version: str
    model_name: str
    confidences: tuple[float, ...]
    needs_review: tuple[bool, ...]
    tokens: tuple[int, ...]
    costs: tuple[float, ...]
    durations: tuple[int, ...]

    @property
    def n(self) -> int:
        return len(self.needs_review)


def _fetch_recent_rows(db: Session, workspace_id: str) -> Sequence:
    stmt = (
        select(
            LLMCallLog.prompt_version,
            LLMCallLog.model_name,
            LLMCallLog.confidence,
            LLMCallLog.needs_review,
            (LLMCallLog.tokens_in + LLMCallLog.tokens_out).label("tokens"),
            LLMCallLog.cost_usd,
            LLMCallLog.duration_ms,
        )
        .where(
            LLMCallLog.workspace_id == workspace_id,
            LLMCallLog.stage.in_(PARECER_STAGES),
        )
        .order_by(LLMCallLog.created_at.desc())
        .limit(WINDOW_LIMIT * 10)
    )
    return db.execute(stmt).all()


def _build_windows(rows: Sequence) -> list[_Window]:
    """Janelas na ordem de recência (rows já vêm desc); cap WINDOW_LIMIT."""
    grouped: dict[tuple[str, str], list] = {}
    order: list[tuple[str, str]] = []
    for r in rows:
        key = (r.prompt_version or "unversioned", r.model_name or "unknown")
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        if len(grouped[key]) < WINDOW_LIMIT:
            grouped[key].append(r)
    return [_window_from(key, grouped[key]) for key in order]


def _window_from(key: tuple[str, str], rows: list) -> _Window:
    return _Window(
        prompt_version=key[0],
        model_name=key[1],
        confidences=tuple(float(r.confidence) for r in rows if r.confidence is not None),
        needs_review=tuple(bool(r.needs_review) for r in rows),
        tokens=tuple(int(r.tokens or 0) for r in rows),
        costs=tuple(float(r.cost_usd or 0.0) for r in rows),
        durations=tuple(int(r.duration_ms or 0) for r in rows),
    )


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _p95(xs: Sequence[int]) -> float:
    if not xs:
        return 0.0
    ordered = sorted(xs)
    return float(ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)])


def _pooled_se_proportion(p_c: float, n_c: int, p_a: float, n_a: int) -> float:
    pooled = (p_c * n_c + p_a * n_a) / (n_c + n_a)
    return math.sqrt(max(pooled * (1 - pooled), 1e-9) * (1 / n_c + 1 / n_a))


def _pooled_se_mean(cur: Sequence[float], base: Sequence[float]) -> float:
    def var(xs: Sequence[float]) -> float:
        m = _mean(xs)
        return sum((x - m) ** 2 for x in xs) / max(len(xs) - 1, 1)

    return math.sqrt(var(cur) / len(cur) + var(base) / len(base))


def _verdict_banded(delta: float, floor: float, se: float) -> str:
    return "warn" if abs(delta) > max(floor, 2 * se) else "ok"


def _verdict_relative(value: float, baseline: float, threshold: float) -> str:
    if baseline <= 0:
        return "insufficient_data"
    return "warn" if abs(value - baseline) / baseline > threshold else "ok"


def _signal(
    name: str, cur: _Window, base: Optional[_Window] = None, *, value, baseline, verdict
) -> DriftSignal:
    return DriftSignal(
        signal=name,
        prompt_version=cur.prompt_version,
        model_name=cur.model_name,
        value=round(float(value), 4),
        baseline=None if baseline is None else round(float(baseline), 4),
        baseline_kind="prev_version",
        n_current=cur.n,
        n_baseline=base.n if base is not None else 0,
        verdict=verdict,
    )


def _confidence_signal(cur: _Window, base: _Window) -> Optional[DriftSignal]:
    if not (cur.confidences and base.confidences):
        return None
    d = _mean(cur.confidences) - _mean(base.confidences)
    se = _pooled_se_mean(cur.confidences, base.confidences)
    verdict = _verdict_banded(d, CONFIDENCE_FLOOR, se)
    return _signal(
        "confidence_delta", cur, base, value=d, baseline=_mean(base.confidences), verdict=verdict
    )


def _needs_review_signal(cur: _Window, base: _Window) -> DriftSignal:
    p_c = _mean([1.0 * x for x in cur.needs_review])
    p_a = _mean([1.0 * x for x in base.needs_review])
    se = _pooled_se_proportion(p_c, cur.n, p_a, base.n)
    verdict = _verdict_banded(p_c - p_a, NEEDS_REVIEW_FLOOR_PP, se)
    return _signal(
        "needs_review_rate_delta", cur, base, value=p_c - p_a, baseline=p_a, verdict=verdict
    )


def _banded_signals(cur: _Window, base: _Window) -> list[DriftSignal]:
    """Confidence e needs_review — banda ``max(floor, 2·SE)`` (N pequeno)."""
    conf = _confidence_signal(cur, base)
    head = [conf] if conf is not None else []
    return head + [_needs_review_signal(cur, base)]


def _relative_signals(cur: _Window, base: _Window) -> list[DriftSignal]:
    """Tokens/custo (±30%) e duration p95 (±40%) — thresholds fixos."""
    triples = (
        ("tokens_mean_delta", _mean(cur.tokens), _mean(base.tokens), TOKENS_COST_REL_THRESHOLD),
        ("cost_mean_delta", _mean(cur.costs), _mean(base.costs), TOKENS_COST_REL_THRESHOLD),
        (
            "duration_p95_delta",
            _p95(cur.durations),
            _p95(base.durations),
            DURATION_P95_REL_THRESHOLD,
        ),
    )
    return [
        _signal(name, cur, base, value=v, baseline=b, verdict=_verdict_relative(v, b, threshold))
        for name, v, b, threshold in triples
    ]


def _compare_windows(cur: _Window, base: _Window) -> list[DriftSignal]:
    return _banded_signals(cur, base) + _relative_signals(cur, base)


def _model_swap_signal(windows: list[_Window]) -> Optional[DriftSignal]:
    """Warn imediato (N=1) se a prompt_version corrente aparece com ≥2 models."""
    if not windows:
        return None
    cur = windows[0]
    models = {w.model_name for w in windows if w.prompt_version == cur.prompt_version}
    if len(models) < 2:
        return None
    return _signal(
        "model_swap_within_version", cur, value=float(len(models)), baseline=None, verdict="warn"
    )


def _baseline_window(windows: list[_Window]) -> Optional[_Window]:
    """Janela anterior com N≥MIN_WINDOW_N — pula baselines ruidosos."""
    for w in windows[1:]:
        if w.n >= MIN_WINDOW_N:
            return w
    return None


def _insufficient_sample_signal(cur: _Window, base: Optional[_Window] = None) -> DriftSignal:
    n_base = base.n if base is not None else 0
    return _signal(
        "window_sample", cur, base, value=cur.n, baseline=n_base, verdict="insufficient_data"
    )


def compute_parecer_drift_signals(db: Session, workspace_id: str) -> list[DriftSignal]:
    """5 sinais de drift do parecer; lista vazia quando não há geração."""
    windows = _build_windows(_fetch_recent_rows(db, workspace_id))
    if not windows:
        return []
    swap = _model_swap_signal(windows)
    signals: list[DriftSignal] = [swap] if swap is not None else []
    cur, base = windows[0], _baseline_window(windows)
    if base is None or cur.n < MIN_WINDOW_N:
        return signals + [_insufficient_sample_signal(cur, base)]
    return signals + _compare_windows(cur, base)


def emit_parecer_drift(db: Session, workspace_id: str) -> None:
    """Best-effort pós-persistência do parecer — nunca propaga exceção."""
    try:
        for s in compute_parecer_drift_signals(db, workspace_id):
            level = logging.WARNING if s.verdict == "warn" else logging.INFO
            logger.log(level, "parecer drift signal", extra={"drift": s.__dict__})
    except Exception:  # noqa: BLE001 — observabilidade não quebra a geração
        logger.exception("parecer_drift_monitor_failed", extra={"workspace_id": workspace_id})
