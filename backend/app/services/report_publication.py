"""ReportPublication service — ADR-187 (mês fechado imutável)."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.app.application.base.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.report import Report
from backend.app.models.report_publication import ReportPublication
from backend.app.repositories.report_publication_repository import (
    ReportPublicationRepository,
)
from backend.app.services.security.crypto import read_artifact_content

_PERIOD_RE = re.compile(r"^[0-9]{6}$")

# Campos voláteis omitidos do hash imutável — variam entre runs sem
# afetar conteúdo de produto. Mantido conservador: o hash existe pra
# detectar mudança real no relatório, não diff de geração.
_VOLATILE_HASH_KEYS: frozenset[str] = frozenset(
    {"generated_at", "rendered_at", "computed_at", "schema_version"}
)


def _validate_period(period_yyyymm: str) -> None:
    if not _PERIOD_RE.match(period_yyyymm):
        raise ValidationError(
            f"period_yyyymm inválido: esperado 6 dígitos, recebido {period_yyyymm!r}",
            code="invalid_period",
        )


def _strip_volatile(value: Any) -> Any:
    """Remove chaves voláteis recursivamente. Listas/escalares passam direto."""
    if isinstance(value, dict):
        return {k: _strip_volatile(v) for k, v in value.items() if k not in _VOLATILE_HASH_KEYS}
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


def compute_immutable_hash(snapshot: dict) -> str:
    """SHA-256 do snapshot E5 normalizado (chaves ordenadas, voláteis removidas)."""
    normalized = _strip_volatile(snapshot)
    payload = json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_REPORT_V2_PREFIX = "mathoms.report-v2\n"


def compute_report_v2_hash(e5_snapshot: dict, protection_snapshot: dict) -> str:
    """Hash do digest E5 legado + serialização canônica integral do snapshot."""
    e5_digest = compute_immutable_hash(e5_snapshot)
    canonical = json.dumps(
        protection_snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    payload = f"{_REPORT_V2_PREFIX}{e5_digest}\n{canonical}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def is_month_closed(
    workspace_id: str,
    period_yyyymm: str,
    *,
    db: AsyncSession,
) -> bool:
    """``True`` se há ``report_publication`` viva para ``(workspace, period)``."""
    _validate_period(period_yyyymm)
    repo = ReportPublicationRepository(db)
    publication = await repo.get_active(workspace_id, period_yyyymm)
    return publication is not None


def is_month_closed_sync(
    workspace_id: str,
    period_yyyymm: str,
    *,
    db: Session,
) -> bool:
    """Sync version of :func:`is_month_closed` — pipeline E4 (ADR-187 A12.P2)."""
    _validate_period(period_yyyymm)
    stmt = select(ReportPublication).where(
        ReportPublication.workspace_id == workspace_id,
        ReportPublication.period_yyyymm == period_yyyymm,
        ReportPublication.unpublished_at.is_(None),
    )
    return db.execute(stmt).scalar_one_or_none() is not None


async def _load_artifact(
    workspace_id: str, artifact_id: int, *, db: AsyncSession
) -> PipelineArtifact:
    result = await db.execute(
        select(PipelineArtifact).where(
            PipelineArtifact.id == artifact_id,
            PipelineArtifact.workspace_id == workspace_id,
        )
    )
    artifact = result.scalar_one_or_none()
    if artifact is None:
        raise NotFoundError(
            f"PipelineArtifact id={artifact_id} não existe no workspace",
            code="artifact_not_found",
        )
    return artifact


async def _load_report_for_artifact(
    workspace_id: str, artifact_id: int, *, db: AsyncSession
) -> Report | None:
    result = await db.execute(
        select(Report).where(
            Report.workspace_id == workspace_id,
            Report.analysis_artifact_id == artifact_id,
        )
    )
    return result.scalar_one_or_none()


def _publication_hash_fields(
    artifact: PipelineArtifact, report: Report | None
) -> tuple[str, str | None, str]:
    e5 = read_artifact_content(artifact.content_json) or {}
    if report is None or report.protection_snapshot_json is None:
        return compute_immutable_hash(e5), None if report is None else report.id, "e5-v1"
    if report.analysis_artifact_id != artifact.id:
        raise ValidationError(
            "report.analysis_artifact_id não coincide com o artefato publicado",
            code="report_artifact_mismatch",
        )
    return (
        compute_report_v2_hash(e5, report.protection_snapshot_json),
        report.id,
        "report-v2",
    )


def _build_publication(
    *,
    workspace_id: str,
    period_yyyymm: str,
    artifact: PipelineArtifact,
    actor: str,
    report: Report | None,
) -> ReportPublication:
    digest, report_id, hash_version = _publication_hash_fields(artifact, report)
    return ReportPublication(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        period_yyyymm=period_yyyymm,
        artifact_id=artifact.id,
        report_id=report_id,
        hash_version=hash_version,
        published_at=datetime.now(timezone.utc),
        published_by=actor,
        immutable_hash=digest,
    )


async def _ensure_month_open(repo: ReportPublicationRepository, workspace_id: str, period: str):
    if await repo.get_active(workspace_id, period) is not None:
        raise ConflictError(
            f"Período {period} já está publicado para este workspace",
            code="already_published",
        )


async def publish_month(
    workspace_id: str, period_yyyymm: str, artifact_id: int, *, actor: str, db: AsyncSession
) -> ReportPublication:
    """Publica o relatório do período (cria linha viva)."""
    _validate_period(period_yyyymm)
    artifact = await _load_artifact(workspace_id, artifact_id, db=db)
    repo = ReportPublicationRepository(db)
    await _ensure_month_open(repo, workspace_id, period_yyyymm)
    report = await _load_report_for_artifact(workspace_id, artifact.id, db=db)
    publication = _build_publication(
        workspace_id=workspace_id,
        period_yyyymm=period_yyyymm,
        artifact=artifact,
        actor=actor,
        report=report,
    )
    return await repo.add(publication)


async def unpublish_month(
    workspace_id: str, period_yyyymm: str, *, actor: str, db: AsyncSession
) -> ReportPublication:
    """Revoga publicação viva (soft-delete: grava ``unpublished_at``)."""
    del actor  # reservado para V2; signature estável para call-sites.
    _validate_period(period_yyyymm)
    repo = ReportPublicationRepository(db)
    publication = await repo.get_active(workspace_id, period_yyyymm)
    if publication is None:
        raise ConflictError(
            f"Período {period_yyyymm} não está publicado para este workspace",
            code="not_published",
        )
    publication.unpublished_at = datetime.now(timezone.utc)
    await db.flush()
    return publication


async def list_publications(workspace_id: str, *, db: AsyncSession) -> list[ReportPublication]:
    """Histórico completo de publicações (vivas + revogadas) do workspace."""
    repo = ReportPublicationRepository(db)
    return await repo.list_by_workspace(workspace_id)


async def get_active_publication(
    workspace_id: str, period_yyyymm: str, *, db: AsyncSession
) -> Optional[ReportPublication]:
    """Publicação viva do (workspace, period), ou None."""
    _validate_period(period_yyyymm)
    repo = ReportPublicationRepository(db)
    return await repo.get_active(workspace_id, period_yyyymm)
