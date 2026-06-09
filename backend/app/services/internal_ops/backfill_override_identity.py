"""Backfill da identidade v2 de ``TransactionOverride`` (ADR-282 slice 3) — reancora
overrides legados (``natural_key_hash IS NULL``) ao ``natural_key`` v2 recomputado da
linha E4, report-only por default, quiesce-aware, idempotente. Políticas órfão/ambíguo/
colisão em ADR-282 §5/§6/§6b (resumidas nos comentários de cada função abaixo)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.transaction._loading import tenant_root
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.transaction_override import OVERRIDE_SOURCE_MANUAL, TransactionOverride
from backend.app.models.workspace import Workspace
from backend.app.services.feature_flags_service import is_enabled
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.results import OpResult
from backend.app.services.override_identity import identity_from_transaction_item
from backend.app.services.transaction_service import load_transactions

__all__ = ["backfill_override_identity", "resolve_collision", "BackfillReport"]

_ACTIVE_RUN_STATUSES = (PipelineRunStatus.running.value, PipelineRunStatus.resuming.value)


@dataclass(frozen=True)
class ReanchorPlan:
    """Override legado → colunas v2 (snapshot = E4-at-backfill-time)."""

    override_id: str
    natural_key_hash: str
    columns: dict


@dataclass(frozen=True)
class CollisionPlan:
    """N overrides colapsam num ``natural_key_hash``; vencedor reancora, perdedores soft-delete."""

    natural_key_hash: str
    winner_id: str
    columns: dict
    loser_ids: tuple[str, ...]


@dataclass(frozen=True)
class BackfillReport:
    """Plano report-only (IDs + escalares, nunca ORM) — consumido por ``_apply``."""

    workspace_id: str
    overrides_total: int
    reanchor: tuple[ReanchorPlan, ...]
    collisions: tuple[CollisionPlan, ...]
    orphaned_ids: tuple[str, ...]
    ambiguous_ids: tuple[str, ...]

    def counts(self) -> dict[str, int]:
        return {
            "overrides_total": self.overrides_total,
            "reanchored": len(self.reanchor) + len(self.collisions),
            "orphaned": len(self.orphaned_ids),
            "ambiguous": len(self.ambiguous_ids),
            "collided": sum(len(c.loser_ids) for c in self.collisions),
        }


def _winner_first(overrides: list[TransactionOverride]) -> list[TransactionOverride]:
    """Chave total: ``manual`` antes de ``rule``; ``created_at`` recente; ``id`` desempata."""
    return sorted(
        overrides,
        key=lambda o: (
            0 if o.source == OVERRIDE_SOURCE_MANUAL else 1,
            -o.created_at.timestamp(),
            o.id,
        ),
    )


def resolve_collision(
    overrides: list[TransactionOverride],
) -> tuple[TransactionOverride, list[TransactionOverride]]:
    """Vencedor (mantém) + perdedores (soft-delete). Determinístico (ADR-282 §6)."""
    ordered = _winner_first(overrides)
    return ordered[0], ordered[1:]


async def _legacy_overrides(db: AsyncSession, workspace_id: str) -> list[TransactionOverride]:
    """Ativos, ainda não reancorados nem quarentenados (checkpoint idempotente)."""
    stmt = select(TransactionOverride).where(
        TransactionOverride.workspace_id == workspace_id,
        TransactionOverride.deleted_at.is_(None),
        TransactionOverride.natural_key_hash.is_(None),
        TransactionOverride.orphaned_at.is_(None),
    )
    return list((await db.execute(stmt)).scalars().all())


def _v1_to_identities(workspace_id: str) -> dict[str, dict[str, dict]]:
    """Mapa ``v1 -> {natural_key_hash: columns}`` do E4 atual. >1 entrada = v1 ambíguo."""
    out: dict[str, dict[str, dict]] = {}
    for item in load_transactions(workspace_id, tenant_root(workspace_id)):
        identity = identity_from_transaction_item(item)
        out.setdefault(item.transaction_hash, {})[identity.natural_key_hash] = identity.as_columns()
    return out


def _classify_one(
    ovr: TransactionOverride, v1_map: dict[str, dict[str, dict]]
) -> tuple[str, str | None, dict | None]:
    """``(bucket, nk_hash, columns)`` — bucket ``reanchor`` | ``orphan`` | ``ambiguous``."""
    identities = v1_map.get(ovr.transaction_hash)
    if not identities:
        return "orphan", None, None
    if len(identities) > 1:
        return "ambiguous", None, None
    nk_hash, columns = next(iter(identities.items()))
    return "reanchor", nk_hash, columns


def _classify(
    overrides: list[TransactionOverride], v1_map: dict[str, dict[str, dict]]
) -> tuple[list[tuple[TransactionOverride, str, dict]], list[str], list[str]]:
    """Particiona em (candidatos a reancorar, órfãos, ambíguos) — dispatch achatado."""
    buckets: dict[str, list[tuple[TransactionOverride, str | None, dict | None]]] = {
        "reanchor": [],
        "orphan": [],
        "ambiguous": [],
    }
    for ovr in overrides:
        bucket, nk_hash, columns = _classify_one(ovr, v1_map)
        buckets[bucket].append((ovr, nk_hash, columns))
    candidates = [(o, nk, c) for o, nk, c in buckets["reanchor"]]
    return (
        candidates,
        [o.id for o, _, _ in buckets["orphan"]],
        [o.id for o, _, _ in buckets["ambiguous"]],
    )


def _split_collisions(
    candidates: list[tuple[TransactionOverride, str, dict]],
) -> tuple[list[ReanchorPlan], list[CollisionPlan]]:
    """Agrupa candidatos por ``natural_key_hash``: 1 = reancor; N = colisão."""
    by_hash: dict[str, list[tuple[TransactionOverride, dict]]] = {}
    for ovr, nk_hash, columns in candidates:
        by_hash.setdefault(nk_hash, []).append((ovr, columns))
    reanchor: list[ReanchorPlan] = []
    collisions: list[CollisionPlan] = []
    for nk_hash, group in by_hash.items():
        if len(group) == 1:
            ovr, columns = group[0]
            reanchor.append(ReanchorPlan(ovr.id, nk_hash, columns))
        else:
            collisions.append(_collision_plan(nk_hash, group))
    return reanchor, collisions


def _collision_plan(nk_hash: str, group: list[tuple[TransactionOverride, dict]]) -> CollisionPlan:
    winner, losers = resolve_collision([ovr for ovr, _ in group])
    columns = next(cols for ovr, cols in group if ovr.id == winner.id)
    return CollisionPlan(nk_hash, winner.id, columns, tuple(o.id for o in losers))


async def _plan(db: AsyncSession, workspace_id: str) -> BackfillReport:
    overrides = await _legacy_overrides(db, workspace_id)
    v1_map = _v1_to_identities(workspace_id)
    candidates, orphaned, ambiguous = _classify(overrides, v1_map)
    reanchor, collisions = _split_collisions(candidates)
    return BackfillReport(
        workspace_id=workspace_id,
        overrides_total=len(overrides),
        reanchor=tuple(reanchor),
        collisions=tuple(collisions),
        orphaned_ids=tuple(orphaned),
        ambiguous_ids=tuple(ambiguous),
    )


async def _fresh_legacy(db: AsyncSession, override_id: str) -> TransactionOverride | None:
    """Re-resolve por id, revalidando ``natural_key_hash IS NULL`` (TOCTOU plan→apply)."""
    ovr = await db.get(TransactionOverride, override_id)
    if ovr is None or ovr.natural_key_hash is not None or ovr.deleted_at is not None:
        return None
    return ovr


async def _apply_reanchor(db: AsyncSession, plan: ReanchorPlan) -> bool:
    ovr = await _fresh_legacy(db, plan.override_id)
    if ovr is None:
        return False
    for column, value in plan.columns.items():
        setattr(ovr, column, value)
    return True


async def _apply_collision(db: AsyncSession, plan: CollisionPlan) -> int:
    winner = await _fresh_legacy(db, plan.winner_id)
    if winner is None:
        return 0
    for column, value in plan.columns.items():
        setattr(winner, column, value)
    return await _soft_delete_losers(db, plan)


async def _soft_delete_losers(db: AsyncSession, plan: CollisionPlan) -> int:
    note = f"colapsado em {plan.winner_id} durante migração natural_key v2 (ADR-282)"
    deleted = 0
    for loser_id in plan.loser_ids:
        loser = await _fresh_legacy(db, loser_id)
        if loser is None:
            continue
        loser.deleted_at = datetime.now(timezone.utc)
        loser.notes = note
        deleted += 1
    return deleted


async def _quarantine(db: AsyncSession, override_ids: tuple[str, ...]) -> None:
    for override_id in override_ids:
        ovr = await _fresh_legacy(db, override_id)
        if ovr is not None:
            ovr.orphaned_at = datetime.now(timezone.utc)


async def _apply(db: AsyncSession, report: BackfillReport) -> None:
    for plan in report.reanchor:
        await _apply_reanchor(db, plan)
    for collision in report.collisions:
        await _apply_collision(db, collision)
    await _quarantine(db, report.orphaned_ids)
    await _quarantine(db, report.ambiguous_ids)


async def _active_run_exists(db: AsyncSession, workspace_id: str) -> bool:
    stmt = select(PipelineRun.id).where(
        PipelineRun.workspace_id == workspace_id,
        PipelineRun.status.in_(_ACTIVE_RUN_STATUSES),
    )
    return (await db.execute(stmt)).first() is not None


async def _advisory_lock(db: AsyncSession, workspace_id: str) -> None:
    """Serializa backfills do mesmo workspace (no-op em SQLite — só Postgres)."""
    if db.bind and db.bind.dialect.name == "postgresql":
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended('override_backfill:' || :ws, 0))"),
            {"ws": workspace_id},
        )


async def _preflight(db: AsyncSession, workspace_id: str) -> OpResult | None:
    """Guards: workspace existe, cutover ainda não ligou, nenhum run ativo (E4 estável)."""
    if await db.get(Workspace, workspace_id) is None:
        return OpResult.failure("workspace_not_found", workspace_id=workspace_id)
    if await is_enabled(workspace_id, "override_natural_key_v2_enabled", db=db):
        return OpResult.failure("cutover_already_active", workspace_id=workspace_id)
    if await _active_run_exists(db, workspace_id):
        return OpResult.failure("workspace_busy", workspace_id=workspace_id)
    return None


async def _execute(db: AsyncSession, workspace_id: str, actor: str) -> OpResult:
    """Escreve sob advisory lock + re-check de quiesce (TOCTOU)."""
    await _advisory_lock(db, workspace_id)
    if await _active_run_exists(db, workspace_id):
        return OpResult.failure("workspace_busy", workspace_id=workspace_id)
    report = await _plan(db, workspace_id)
    await _apply(db, report)
    _audit(actor, report)
    return OpResult.success(preview=False, **report.counts())


async def backfill_override_identity(
    db: AsyncSession, *, workspace_id: str, actor: str, preview: bool = True
) -> OpResult:
    """Reancora overrides legados ao ``natural_key`` v2 — report-only se ``preview`` (ADR-282)."""
    guard = await _preflight(db, workspace_id)
    if guard is not None:
        return guard
    if preview:
        report = await _plan(db, workspace_id)
        return OpResult.success(preview=True, **report.counts())
    return await _execute(db, workspace_id, actor)


def _audit(actor: str, report: BackfillReport) -> None:
    append_audit(
        AuditRecord(
            action="override.backfill_natural_key",
            actor=actor,
            target_type="workspace",
            target_id=report.workspace_id,
            details=report.counts(),
        )
    )
