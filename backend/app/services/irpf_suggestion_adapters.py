"""Adapters DB para ``get_irpf_suggestions`` (ADR-229 · ADR-097 boundary)."""

from __future__ import annotations

import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.family_member import IrpfArtifactPayload
from backend.app.models.family_member import WorkspaceIrpfSuggestionDismissal
from backend.app.models.institution_catalog import InstitutionCatalog
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.services.security.crypto import read_artifact_content
from pipeline.artifact_store import stage_aliases

_DIGITS_RE = re.compile(r"\D")


def normalize_account_digits(raw: Optional[str] = None) -> Optional[str]:
    """Digits-only do account_number (ADR-226 §1)."""
    if raw is None:
        return None
    digits = _DIGITS_RE.sub("", raw)
    return digits or None


def _payload_from_row(row: PipelineArtifact) -> IrpfArtifactPayload:
    content = read_artifact_content(row.content_json) or {}
    # V1 V0: ano-base derivado de ``created_at`` (IRPF Y declarado em Mar-Abr Y+1).
    irpf_year = (row.created_at.year - 1) if row.created_at else 0
    return IrpfArtifactPayload(
        irpf_year=irpf_year,
        processed_at=row.created_at,
        contas=list(content.get("contas") or []),
        membros=dict(content.get("membros") or {}),
    )


class DBIrpfArtifactSource:
    """Lê PipelineArtifact mais recente (stage=E1, key=members) do workspace."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_latest(self, workspace_id: str) -> Optional[IrpfArtifactPayload]:
        stmt = (
            select(PipelineArtifact)
            .where(
                PipelineArtifact.workspace_id == workspace_id,
                PipelineArtifact.stage.in_(stage_aliases("extract_members")),
                PipelineArtifact.artifact_key == "members",
            )
            .order_by(PipelineArtifact.created_at.desc(), PipelineArtifact.id.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        row = result.scalar_one_or_none()
        return _payload_from_row(row) if row is not None else None


class DBInstitutionLabelResolver:
    """Mapeia ``institution_code → name`` via ``institution_catalog``."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def resolve(self, codes: list[str]) -> dict[str, str]:
        if not codes:
            return {}
        stmt = select(InstitutionCatalog.code, InstitutionCatalog.name).where(
            InstitutionCatalog.code.in_(codes)
        )
        result = await self._db.execute(stmt)
        return {code: name for code, name in result.all()}


async def find_dismissal_for_account(
    db: AsyncSession,
    *,
    workspace_id: str,
    institution_code: str,
    account_number_norm: str,
) -> Optional[WorkspaceIrpfSuggestionDismissal]:
    """Descarte prévio (qualquer ano) para a tupla (ws, inst, num)."""
    stmt = select(WorkspaceIrpfSuggestionDismissal).where(
        WorkspaceIrpfSuggestionDismissal.workspace_id == workspace_id,
        WorkspaceIrpfSuggestionDismissal.institution_code == institution_code,
        WorkspaceIrpfSuggestionDismissal.account_number_norm == account_number_norm,
    )
    return (await db.execute(stmt)).scalar_one_or_none()
