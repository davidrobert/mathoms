"""Backfill heurístico de Suggestions Pendentes pré-ADR-290 (F4 do PLAN-suggestion-lifecycle) — linhas antigas não têm thesis_key recomputável, então agrupa por (section_id, título normalizado), mantém a mais recente e supersede o resto; padrão pipeline_reset (workspace obrigatório, dry-run default, audit em apply); runbook em docs/reference/runbooks/suggestion_backfill.md."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.suggestion import Suggestion
from backend.app.models.workspace import Workspace
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.results import OpResult

__all__ = ["backfill_supersede_pending_suggestions"]

_SUGGESTION_KIND = "parecer_planejador"

# Modos de reconciliação. "heuristic" (default) agrupa por (section_id,
# título normalizado) — conservador, mas no-op quando o LLM re-redigiu o
# título em todos os runs (caso dogfood 2026-06-12: 165 pendentes → 0
# grupos). "latest_batch" aplica a semântica ADR-290 "último parecer
# vence": mantém o lote mais recente (janela de 1h cobre o burst de um
# persist) e supersede o resto — aprovado pelo owner em 2026-06-12.
_VALID_MODES = frozenset({"heuristic", "latest_batch"})
_LATEST_BATCH_WINDOW = timedelta(hours=1)


def _normalized_title(title: str) -> str:
    """lower + whitespace colapsado + [:100] — espelha a normalização do dedup_key."""
    return re.sub(r"\s+", " ", title.strip().lower())[:100]


async def _load_backfillable_pendings(
    db: AsyncSession, *, workspace_id: str, started_at: datetime
) -> list[Suggestion]:
    """Pendentes LLM do parecer criadas ANTES do início do backfill (concorrência:
    run de pipeline em paralelo não entra no agrupamento)."""
    rows = await db.execute(
        select(Suggestion)
        .where(
            Suggestion.workspace_id == workspace_id,
            Suggestion.status == "Pendente",
            Suggestion.origin == "llm",
            Suggestion.kind == _SUGGESTION_KIND,
            Suggestion.accepted_decision_id.is_(None),
            Suggestion.created_at < started_at,
        )
        .order_by(Suggestion.created_at.desc())
    )
    return list(rows.scalars().all())


def _group_by_heuristic(pendings: list[Suggestion]) -> dict[tuple[str, str], list[Suggestion]]:
    """Agrupa por (section_id, título normalizado); listas já em created_at desc."""
    groups: dict[tuple[str, str], list[Suggestion]] = {}
    for s in pendings:
        groups.setdefault((s.section_id, _normalized_title(s.title)), []).append(s)
    return groups


def _group_report(groups: dict[tuple[str, str], list[Suggestion]]) -> list[dict]:
    """Relatório (grupo → mantém / supersede) para revisão humana pré-apply."""
    report = []
    for (section_id, norm_title), members in sorted(groups.items()):
        keep, rest = members[0], members[1:]
        report.append(
            {
                "section_id": section_id,
                "titulo_normalizado": norm_title,
                "mantem": {"id": keep.id, "created_at": keep.created_at.isoformat()},
                "supersede_ids": [s.id for s in rest],
                "supersede_count": len(rest),
            }
        )
    return report


def _apply_supersede(groups: dict[tuple[str, str], list[Suggestion]], now: datetime) -> int:
    return sum(_supersede_rows(members[1:], now) for members in groups.values())


def _audit_backfill(actor: str, workspace_id: str, superseded: int, kept: int) -> None:
    append_audit(
        AuditRecord(
            action="suggestions.backfill_supersede",
            actor=actor,
            target_type="workspace",
            target_id=workspace_id,
            details={"superseded": superseded, "groups_kept": kept},
        )
    )


def _dry_run_result(workspace_id: str, pendings: list, groups: dict) -> OpResult:
    report = _group_report(groups)
    return OpResult.success(
        dry_run=True,
        workspace_id=workspace_id,
        pendentes=len(pendings),
        groups=len(groups),
        superseded_planned=sum(g["supersede_count"] for g in report),
        report=report,
    )


async def _apply_and_audit(
    db: AsyncSession, *, workspace_id: str, actor: str, pendings: list, groups: dict, now: datetime
) -> OpResult:
    superseded = _apply_supersede(groups, now)
    await db.flush()
    _audit_backfill(actor, workspace_id, superseded, len(groups))
    return OpResult.success(
        dry_run=False,
        workspace_id=workspace_id,
        pendentes=len(pendings),
        groups=len(groups),
        superseded=superseded,
        report=_group_report(groups),
    )


def _latest_batch_partition(
    pendings: list[Suggestion],
) -> tuple[list[Suggestion], list[Suggestion], Optional[datetime]]:
    """(mantidas, a_superseder, cutoff) — mantém o burst mais recente (janela 1h)."""
    if not pendings:
        return [], [], None
    cutoff = max(p.created_at for p in pendings) - _LATEST_BATCH_WINDOW
    kept = [p for p in pendings if p.created_at >= cutoff]
    return kept, [p for p in pendings if p.created_at < cutoff], cutoff


def _supersede_rows(rows: list[Suggestion], now: datetime) -> int:
    for s in rows:
        s.status = "Superseded"
        s.superseded_at = now
        # superseded_by_run_id fica NULL — não há run; proveniência no audit.
    return len(rows)


async def _run_latest_batch(
    db: AsyncSession, *, workspace_id: str, actor: str, pendings: list, apply: bool, now: datetime
) -> OpResult:
    kept, to_supersede, cutoff = _latest_batch_partition(pendings)
    details = {
        "mode": "latest_batch",
        "workspace_id": workspace_id,
        "pendentes": len(pendings),
        "kept": len(kept),
        "cutoff": cutoff.isoformat() if cutoff else None,
        "kept_ids": [s.id for s in kept],
    }
    if not apply:
        return OpResult.success(dry_run=True, superseded_planned=len(to_supersede), **details)
    superseded = _supersede_rows(to_supersede, now)
    await db.flush()
    _audit_backfill(actor, workspace_id, superseded, len(kept))
    return OpResult.success(dry_run=False, superseded=superseded, **details)


async def _run_heuristic(
    db: AsyncSession, *, workspace_id: str, actor: str, pendings: list, apply: bool, now: datetime
) -> OpResult:
    groups = _group_by_heuristic(pendings)
    if not apply:
        return _dry_run_result(workspace_id, pendings, groups)
    return await _apply_and_audit(
        db, workspace_id=workspace_id, actor=actor, pendings=pendings, groups=groups, now=now
    )


async def _validate(db: AsyncSession, *, workspace_id: str, mode: str) -> Optional[OpResult]:
    if mode not in _VALID_MODES:
        return OpResult.failure("invalid_mode", mode=mode, valid_modes=sorted(_VALID_MODES))
    if await db.get(Workspace, workspace_id) is None:
        return OpResult.failure("workspace_not_found", workspace_id=workspace_id)
    return None


async def backfill_supersede_pending_suggestions(
    db: AsyncSession,
    *,
    workspace_id: str,
    actor: str,
    apply: bool = False,
    mode: str = "heuristic",
) -> OpResult:
    """Reconcilia Pendentes antigas — 'heuristic' (grupo por título) ou 'latest_batch' (último parecer vence); dry-run default; caller controla commit/rollback (ver runbook)."""
    invalid = await _validate(db, workspace_id=workspace_id, mode=mode)
    if invalid is not None:
        return invalid
    started_at = datetime.now(timezone.utc)
    pendings = await _load_backfillable_pendings(
        db, workspace_id=workspace_id, started_at=started_at
    )
    run = _run_latest_batch if mode == "latest_batch" else _run_heuristic
    return await run(
        db, workspace_id=workspace_id, actor=actor, pendings=pendings, apply=apply, now=started_at
    )
