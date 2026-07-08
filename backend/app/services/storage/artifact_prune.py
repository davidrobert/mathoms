"""Prune por idade de ``pipeline_artifacts`` (A33.l6 · W6-T05 · ADR-212).

Predicado de 1 ramo (co-design data-engineer 2026-07-07, reconciliado com a
ADR-311 — o tombstone do #837 é DELETE destrutivo, não existe tombstone-row):

    retention_until IS NOT NULL AND retention_until < now
    AND NOT (row é a versão corrente do grupo (workspace, stage-alias, key))

Defesas em profundidade além do predicado:

- Rows referenciadas por FK — ``reports.analysis_artifact_id`` (SET NULL),
  ``report_publications.artifact_id`` (RESTRICT),
  ``planner_review_metadata.pipeline_artifact_id`` (CASCADE) e
  ``.e5_artifact_id`` (RESTRICT) — nunca entram no conjunto prunável:
  RESTRICT abortaria o batch inteiro; SET NULL/CASCADE quebrariam report
  ou parecer publicado em silêncio.
- GATE (aceite da lane): se qualquer versão **corrente** tem
  ``retention_until ≠ NULL``, o delete é bloqueado mesmo em
  ``prune_mode=delete`` — invariante do write-path foi violada.

Backfill contínuo idempotente (roda dentro da task diária): rows com
``retention_until IS NULL`` comprovadamente superseded ganham
``created_at do sucessor + superseded_days`` — o relógio conta do momento
real de supersessão, não do deploy. Grupamento alias-aware (ADR-093):
``E5`` e ``analyze_finances`` são o mesmo grupo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Sequence

import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.planner_review import PlannerReview
from backend.app.models.report import Report
from backend.app.models.report_publication import ReportPublication
from backend.app.services.storage.artifact_retention import ArtifactRetentionPolicy
from backend.app.services.storage.artifact_tombstone import e2_tombstone_stage_names
from pipeline.artifact_store import stage_aliases
from pipeline.stage_spec import resolve_stage_name

_GroupKey = tuple[str, tuple[str, ...], str]

_TOP_GROUPS_LIMIT = 10
_DELETE_BATCH_SIZE = 1000


@dataclass(frozen=True)
class ArtifactMeta:
    """Projeção metadata-only de uma row de ``pipeline_artifacts`` (sem payload)."""

    id: int
    workspace_id: str
    stage: str
    artifact_key: str
    created_at: datetime
    retention_until: Optional[datetime]
    document_id: Optional[str]
    payload_bytes: int


@dataclass(frozen=True)
class ArtifactPruneReport:
    """Relatório do dry-run/prune — calibra a política antes do flip (aceite #2)."""

    scanned_rows: int
    gate_current_with_retention: int
    candidates_total: int
    candidates_bytes: int
    expired_total: int
    expired_bytes: int
    referenced_excluded: int
    orphan_document_candidates: int
    by_workspace_stage: tuple[dict, ...]
    created_at_by_stage: tuple[dict, ...]
    top_superseded_groups: tuple[dict, ...]
    expired_prunable_ids: tuple[int, ...] = field(repr=False)

    def to_log_extra(self) -> dict:
        """Payload para log estruturado — sem ids nem conteúdo financeiro."""
        return {
            "scanned_rows": self.scanned_rows,
            "gate_current_with_retention": self.gate_current_with_retention,
            "candidates_total": self.candidates_total,
            "candidates_bytes": self.candidates_bytes,
            "expired_total": self.expired_total,
            "expired_bytes": self.expired_bytes,
            "referenced_excluded": self.referenced_excluded,
            "orphan_document_candidates": self.orphan_document_candidates,
            "by_workspace_stage": list(self.by_workspace_stage),
            "created_at_by_stage": list(self.created_at_by_stage),
            "top_superseded_groups": list(self.top_superseded_groups),
        }


@dataclass(frozen=True)
class ArtifactPruneOutcome:
    marked: int
    deleted: int
    delete_blocked_by_gate: bool
    report: ArtifactPruneReport


def _as_utc(value: Optional[datetime] = None) -> Optional[datetime]:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _group_key(row: ArtifactMeta) -> _GroupKey:
    return (row.workspace_id, tuple(sorted(stage_aliases(row.stage))), row.artifact_key)


def _metadata_select() -> sa.Select:
    size_expr = sa.func.coalesce(
        PipelineArtifact.byte_size,
        sa.func.length(sa.cast(PipelineArtifact.content_json, sa.Text())),
        0,
    )
    return sa.select(
        PipelineArtifact.id,
        PipelineArtifact.workspace_id,
        PipelineArtifact.stage,
        PipelineArtifact.artifact_key,
        PipelineArtifact.created_at,
        PipelineArtifact.retention_until,
        PipelineArtifact.document_id,
        size_expr,
    )


def _meta_from_row(r) -> ArtifactMeta:
    return ArtifactMeta(
        id=r[0],
        workspace_id=r[1],
        stage=r[2],
        artifact_key=r[3],
        created_at=_as_utc(r[4]) or datetime.now(timezone.utc),
        retention_until=_as_utc(r[5]),
        document_id=r[6],
        payload_bytes=int(r[7] or 0),
    )


def load_artifact_metadata(db: Session) -> list[ArtifactMeta]:
    """Scan metadata-only — payload nunca sai do DB (``length()`` computa lá)."""
    return [_meta_from_row(r) for r in db.execute(_metadata_select()).all()]


def _rows_by_group(rows: Sequence[ArtifactMeta]) -> dict[_GroupKey, list[ArtifactMeta]]:
    """Agrupa alias-aware; membros ordenados por (created_at, id) ascendente —
    o último espelha o "corrente" de ``_get_latest_in_workspace`` (ADR-241)."""
    groups: dict[_GroupKey, list[ArtifactMeta]] = {}
    for row in rows:
        groups.setdefault(_group_key(row), []).append(row)
    for members in groups.values():
        members.sort(key=lambda r: (r.created_at, r.id))
    return groups


def referenced_artifact_ids(db: Session) -> frozenset[int]:
    """Ids referenciados por reports / publicações / pareceres — nunca prunáveis."""
    stmts = (
        sa.select(Report.analysis_artifact_id).where(Report.analysis_artifact_id.is_not(None)),
        sa.select(ReportPublication.artifact_id),
        sa.select(PlannerReview.pipeline_artifact_id),
        sa.select(PlannerReview.e5_artifact_id),
    )
    ids: set[int] = set()
    for stmt in stmts:
        ids.update(i for (i,) in db.execute(stmt) if i is not None)
    return frozenset(ids)


def mark_superseded_rows(db: Session, *, policy: ArtifactRetentionPolicy) -> int:
    """Backfill contínuo idempotente: NULL + comprovadamente superseded →
    ``retention_until = created_at do sucessor + superseded_days``."""
    groups = _rows_by_group(load_artifact_metadata(db))
    marked = 0
    for members in groups.values():
        marked += _mark_group(db, members, policy)
    return marked


def _mark_group(db: Session, members: list[ArtifactMeta], policy: ArtifactRetentionPolicy) -> int:
    marked = 0
    for row, successor in zip(members[:-1], members[1:]):
        if row.retention_until is not None:
            continue
        until = policy.retention_until(now=successor.created_at)
        db.execute(
            sa.update(PipelineArtifact)
            .where(PipelineArtifact.id == row.id, PipelineArtifact.retention_until.is_(None))
            .values(retention_until=until)
        )
        marked += 1
    return marked


def _split_candidates(
    groups: dict[_GroupKey, list[ArtifactMeta]],
) -> tuple[list[ArtifactMeta], int]:
    """Candidatas = rows não-correntes com retention ≠ NULL; conta violações
    do gate (corrente com retention ≠ NULL — write-path quebrou a invariante)."""
    candidates: list[ArtifactMeta] = []
    gate_violations = 0
    for members in groups.values():
        if members[-1].retention_until is not None:
            gate_violations += 1
        candidates.extend(r for r in members[:-1] if r.retention_until is not None)
    return candidates, gate_violations


def _count_orphan_document_rows(candidates: Sequence[ArtifactMeta]) -> int:
    e2_stages = set(e2_tombstone_stage_names())
    return sum(1 for r in candidates if r.stage in e2_stages and r.document_id is None)


def _aggregate_workspace_stage(
    candidates: Sequence[ArtifactMeta], *, now: datetime
) -> tuple[dict, ...]:
    acc: dict[tuple[str, str], dict] = {}
    for row in candidates:
        key = (row.workspace_id, resolve_stage_name(row.stage))
        entry = acc.setdefault(
            key,
            {"workspace_id": key[0], "stage": key[1], "count": 0, "bytes": 0, "expired": 0},
        )
        entry["count"] += 1
        entry["bytes"] += row.payload_bytes
        if row.retention_until is not None and row.retention_until < now:
            entry["expired"] += 1
    return tuple(sorted(acc.values(), key=lambda e: (-e["bytes"], e["workspace_id"], e["stage"])))


def _created_at_stats(candidates: Sequence[ArtifactMeta]) -> tuple[dict, ...]:
    by_stage: dict[str, list[datetime]] = {}
    for row in candidates:
        by_stage.setdefault(resolve_stage_name(row.stage), []).append(row.created_at)
    stats = []
    for stage, values in sorted(by_stage.items()):
        values.sort()
        stats.append(
            {
                "stage": stage,
                "count": len(values),
                "created_min": values[0].isoformat(),
                "created_p50": values[len(values) // 2].isoformat(),
                "created_max": values[-1].isoformat(),
            }
        )
    return tuple(stats)


def _top_superseded_groups(groups: dict[_GroupKey, list[ArtifactMeta]]) -> tuple[dict, ...]:
    ranked = sorted(
        ((key, len(members) - 1) for key, members in groups.items() if len(members) > 1),
        key=lambda kv: (-kv[1], kv[0]),
    )[:_TOP_GROUPS_LIMIT]
    return tuple(
        {
            "workspace_id": ws,
            "stage": resolve_stage_name(stages[0]),
            "artifact_key": key,
            "superseded": n,
        }
        for (ws, stages, key), n in ranked
    )


def _expired_prunable(
    candidates: Sequence[ArtifactMeta], referenced: frozenset[int], *, now: datetime
) -> tuple[list[ArtifactMeta], tuple[int, ...]]:
    expired = [r for r in candidates if r.retention_until is not None and r.retention_until < now]
    return expired, tuple(r.id for r in expired if r.id not in referenced)


def build_prune_report(db: Session, *, now: datetime) -> ArtifactPruneReport:
    rows = load_artifact_metadata(db)
    groups = _rows_by_group(rows)
    candidates, gate_violations = _split_candidates(groups)
    expired, prunable = _expired_prunable(candidates, referenced_artifact_ids(db), now=now)
    return ArtifactPruneReport(
        scanned_rows=len(rows),
        gate_current_with_retention=gate_violations,
        candidates_total=len(candidates),
        candidates_bytes=sum(r.payload_bytes for r in candidates),
        expired_total=len(expired),
        expired_bytes=sum(r.payload_bytes for r in expired),
        referenced_excluded=len(expired) - len(prunable),
        orphan_document_candidates=_count_orphan_document_rows(candidates),
        by_workspace_stage=_aggregate_workspace_stage(candidates, now=now),
        created_at_by_stage=_created_at_stats(candidates),
        top_superseded_groups=_top_superseded_groups(groups),
        expired_prunable_ids=prunable,
    )


def _delete_batch(db: Session, batch: Sequence[int], now: datetime) -> int:
    result = db.execute(
        sa.delete(PipelineArtifact).where(
            PipelineArtifact.id.in_(batch),
            PipelineArtifact.retention_until.is_not(None),
            PipelineArtifact.retention_until < now,
        )
    )
    return int(result.rowcount or 0)


def delete_expired_rows(
    db: Session,
    ids: Sequence[int],
    *,
    now: datetime,
    batch_size: int = _DELETE_BATCH_SIZE,
) -> int:
    """DELETE em lotes, re-checando o predicado temporal na própria cláusula."""
    id_list = list(ids)
    return sum(
        _delete_batch(db, id_list[start : start + batch_size], now)
        for start in range(0, len(id_list), batch_size)
    )


def run_artifact_prune(
    db: Session, *, policy: ArtifactRetentionPolicy, now: datetime
) -> ArtifactPruneOutcome:
    """Backfill → relatório → (delete apenas em ``prune_mode=delete`` com gate zerado)."""
    marked = mark_superseded_rows(db, policy=policy)
    report = build_prune_report(db, now=now)
    blocked = policy.delete_enabled and report.gate_current_with_retention > 0
    deleted = 0
    if policy.delete_enabled and not blocked:
        deleted = delete_expired_rows(db, report.expired_prunable_ids, now=now)
    return ArtifactPruneOutcome(
        marked=marked, deleted=deleted, delete_blocked_by_gate=blocked, report=report
    )
