"""Adapter SQLAlchemy → ``AnalyzeFinancesSnapshot`` para o ``SnapshotChangelogBuilder`` (v2.D.1 · ADR-148; compat stage E5/analyze_finances ADR-093; hash on-read não persistido)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.services.crypto import read_artifact_content
from pipeline.domain.types.snapshot_changelog import AnalyzeFinancesSnapshot

# ADR-093: F9 mapeou E5 → analyze_finances; janela de compat ainda aberta.
_ANALYZE_STAGES: tuple[str, ...] = ("analyze_finances", "E5")
_ANALYZE_ARTIFACT_KEY: str = "analise_financeira"

# Regex para extrair YYYYMM do final de `periodo_dados` (formato livre).
_PERIOD_END_PATTERNS: tuple[str, ...] = (
    r"(\d{4})-(\d{2})\b(?!.*\d{4})",  # último YYYY-MM
    r"(\d{4})(\d{2})\b(?!.*\d{4})",  # último YYYYMM
)


def load_snapshot_pair(
    session: Session,
    *,
    workspace_id: str,
    current_artifact_id: int,
) -> tuple[AnalyzeFinancesSnapshot | None, AnalyzeFinancesSnapshot]:
    """Carrega snapshot atual + anterior do mesmo workspace; prev=None se primeiro."""
    current_row = _fetch_current(session, current_artifact_id)
    prev_row = _fetch_previous(session, workspace_id, current_row.created_at)
    current = _to_snapshot(current_row)
    prev = _to_snapshot(prev_row) if prev_row is not None else None
    return prev, current


def _fetch_current(session: Session, artifact_id: int) -> PipelineArtifact:
    """Busca artefato `analyze_finances` por id; raise se inexistente ou stage diferente."""
    row = session.get(PipelineArtifact, artifact_id)
    if row is None:
        raise ValueError(f"PipelineArtifact id={artifact_id} não encontrado")
    if row.stage not in _ANALYZE_STAGES:
        raise ValueError(
            f"PipelineArtifact id={artifact_id} tem stage={row.stage!r}, "
            f"esperado um de {_ANALYZE_STAGES!r}"
        )
    return row


def _fetch_previous(
    session: Session,
    workspace_id: str,
    current_created_at: datetime,
) -> PipelineArtifact | None:
    """Snapshot anterior — `analyze_finances` mais recente com `created_at < current`."""
    stmt = (
        select(PipelineArtifact)
        .where(
            PipelineArtifact.workspace_id == workspace_id,
            PipelineArtifact.stage.in_(_ANALYZE_STAGES),
            PipelineArtifact.artifact_key == _ANALYZE_ARTIFACT_KEY,
            PipelineArtifact.created_at < current_created_at,
        )
        .order_by(PipelineArtifact.created_at.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def _to_snapshot(row: PipelineArtifact) -> AnalyzeFinancesSnapshot:
    """Converte row SQLAlchemy → `AnalyzeFinancesSnapshot` (hash on-read)."""
    content = read_artifact_content(row.content_json) or {}
    return AnalyzeFinancesSnapshot(
        workspace_id=row.workspace_id,
        period_yyyymm=_extract_period_yyyymm(content),
        analysis_hash=_compute_analysis_hash(content),
        content_json=content,
        created_at=row.created_at,
    )


def _extract_period_yyyymm(content: Mapping[str, Any]) -> str:
    """Extrai YYYYMM do `periodo_dados` (key real do E5; fallback `periodo`)."""
    raw = content.get("periodo_dados") or content.get("periodo") or ""
    if not isinstance(raw, str):
        return ""
    for pattern in _PERIOD_END_PATTERNS:
        matches = list(re.finditer(pattern, raw))
        if matches:
            year, month = matches[-1].groups()
            return f"{year}{month}"
    return ""


def _compute_analysis_hash(content: Mapping[str, Any]) -> str:
    """`sha256(canonical_json(content))[:16]` — identidade derivada on-read."""
    canonical = _canonical_json(content)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _canonical_json(value: Any) -> str:
    """Serialização canônica: chaves ordenadas, separadores compactos, ASCII off."""
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=_json_default,
    )


def _json_default(obj: Any) -> Any:
    """Coerção determinística para `json.dumps`: Decimal → str (ADR-090)."""
    from decimal import Decimal

    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"não serializável: {type(obj).__name__}")


__all__ = ["load_snapshot_pair"]
