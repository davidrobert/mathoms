"""Backfill heurístico de Suggestions Pendentes pré-ADR-290 (F4 do PLAN-suggestion-lifecycle) — linhas antigas não têm thesis_key recomputável, então agrupa por (section_id, título normalizado), mantém a mais recente e supersede o resto; padrão pipeline_reset (workspace obrigatório, dry-run default, audit em apply); runbook em docs/reference/runbooks/suggestion_backfill.md."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.suggestion import Suggestion
from backend.app.models.workspace import Workspace
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.results import OpResult

__all__ = ["backfill_supersede_pending_suggestions"]

_SUGGESTION_KIND = "parecer_planejador"


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
    count = 0
    for members in groups.values():
        for s in members[1:]:
            s.status = "Superseded"
            s.superseded_at = now
            # superseded_by_run_id fica NULL — não há run; proveniência no audit.
            count += 1
    return count


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


async def backfill_supersede_pending_suggestions(
    db: AsyncSession,
    *,
    workspace_id: str,
    actor: str,
    apply: bool = False,
) -> OpResult:
    """Agrupa Pendentes heuristicamente e supersede duplicatas antigas — dry-run default; caller controla commit/rollback (ver runbook)."""
    if await db.get(Workspace, workspace_id) is None:
        return OpResult.failure("workspace_not_found", workspace_id=workspace_id)
    started_at = datetime.now(timezone.utc)
    pendings = await _load_backfillable_pendings(
        db, workspace_id=workspace_id, started_at=started_at
    )
    groups = _group_by_heuristic(pendings)
    if not apply:
        return _dry_run_result(workspace_id, pendings, groups)
    return await _apply_and_audit(
        db, workspace_id=workspace_id, actor=actor, pendings=pendings, groups=groups, now=started_at
    )
