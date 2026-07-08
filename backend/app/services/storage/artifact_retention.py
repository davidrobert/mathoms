"""Política de retenção de pipeline_artifacts (A33.l6 · W6-T05 · ADR-212): value object tipado (ADR-089) + loader de ``config/pipeline.json → artifact_retention`` com env override; calibração data-engineer 2026-07-07 — ``retention_until IS NULL`` é fail-safe permanente (corrente nunca ganha data; só superseded marca), 180d uniforme, ``prune_mode="dry_run"`` default (DELETE só em ``"delete"``; flip em PR separado gated no dry-run)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta

PRUNE_MODE_DRY_RUN = "dry_run"
PRUNE_MODE_DELETE = "delete"
_VALID_PRUNE_MODES = frozenset({PRUNE_MODE_DRY_RUN, PRUNE_MODE_DELETE})

_DEFAULT_SUPERSEDED_DAYS = 180

_ENV_SUPERSEDED_DAYS = "MATHOMS_ARTIFACT_RETENTION_SUPERSEDED_DAYS"
_ENV_PRUNE_MODE = "MATHOMS_ARTIFACT_PRUNE_MODE"


@dataclass(frozen=True)
class ArtifactRetentionPolicy:
    """Config tipada da retenção — nunca dict solto (ADR-089)."""

    superseded_days: int = _DEFAULT_SUPERSEDED_DAYS
    prune_mode: str = PRUNE_MODE_DRY_RUN

    def __post_init__(self) -> None:
        if self.superseded_days < 1:
            raise ValueError(f"expected superseded_days >= 1, got {self.superseded_days!r}")
        if self.prune_mode not in _VALID_PRUNE_MODES:
            raise ValueError(
                f"expected prune_mode in {sorted(_VALID_PRUNE_MODES)}, got {self.prune_mode!r}"
            )

    def retention_until(self, *, now: datetime) -> datetime:
        """Data de expiração para uma row que acabou de virar superseded."""
        return now + timedelta(days=self.superseded_days)

    @property
    def delete_enabled(self) -> bool:
        return self.prune_mode == PRUNE_MODE_DELETE


def _int_or_default(raw: object, default: int) -> int:
    try:
        return int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def load_artifact_retention_policy() -> ArtifactRetentionPolicy:
    """Resolve a policy — env (ops escape hatch) > pipeline.json > default, mesmo padrão de precedência do ``schema_validation.mode`` (``scripts.pipeline_common._effective_schema_validation_mode``)."""
    from scripts.pipeline_common import load_json_config

    section = load_json_config("pipeline.json").get("artifact_retention", {})
    days = _int_or_default(
        os.environ.get(_ENV_SUPERSEDED_DAYS) or section.get("superseded_days"),
        _DEFAULT_SUPERSEDED_DAYS,
    )
    mode = os.environ.get(_ENV_PRUNE_MODE) or section.get("prune_mode") or PRUNE_MODE_DRY_RUN
    if mode not in _VALID_PRUNE_MODES:
        mode = PRUNE_MODE_DRY_RUN
    if days < 1:
        days = _DEFAULT_SUPERSEDED_DAYS
    return ArtifactRetentionPolicy(superseded_days=days, prune_mode=mode)
