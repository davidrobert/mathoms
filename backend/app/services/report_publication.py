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

from backend.app.application.base.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.report_publication import ReportPublication
from backend.app.repositories.report_publication_repository import (
    ReportPublicationRepository,
)

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
    """SHA-256 do snapshot normalizado (chaves ordenadas, voláteis removidas)."""
    normalized = _strip_volatile(snapshot)
    payload = json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
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


def _build_publication(
    *, workspace_id: str, period_yyyymm: str, artifact: PipelineArtifact, actor: str
) -> ReportPublication:
    return ReportPublication(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        period_yyyymm=period_yyyymm,
        artifact_id=artifact.id,
        published_at=datetime.now(timezone.utc),
        published_by=actor,
        immutable_hash=compute_immutable_hash(artifact.content_json or {}),
    )


async def publish_month(
    workspace_id: str, period_yyyymm: str, artifact_id: int, *, actor: str, db: AsyncSession
) -> ReportPublication:
    """Publica o relatório do período (cria linha viva)."""
    _validate_period(period_yyyymm)
    artifact = await _load_artifact(workspace_id, artifact_id, db=db)
    repo = ReportPublicationRepository(db)
    if await repo.get_active(workspace_id, period_yyyymm) is not None:
        raise ConflictError(
            f"Período {period_yyyymm} já está publicado para este workspace",
            code="already_published",
        )
    publication = _build_publication(
        workspace_id=workspace_id, period_yyyymm=period_yyyymm, artifact=artifact, actor=actor
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
