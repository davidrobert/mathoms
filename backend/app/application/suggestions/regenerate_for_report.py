"""Use case: re-gera Suggestions para um Report (ADR-153).

Boundary do pipeline: o gerador
(:class:`pipeline.domain.services.suggestion_generator.SuggestionGenerator`)
é puro — recebe snapshot dict + current_date, devolve drafts. Backend
orquestra: lê snapshot E5 do ``analysis_artifact``, chama generator,
aplica dedup contra existentes, persiste em transação.

Idempotente: re-rodar é seguro (drafts duplicadas viram skip silencioso).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError, ValidationError
from backend.app.application.report._common import fetch_report
from backend.app.application.suggestions._protocols import (
    SuggestionRepositoryProtocol,
)
from backend.app.models.suggestion import Suggestion
from backend.app.schemas.dto.decision.mapper import brl_to_cents
from backend.app.schemas.dto.suggestion import (
    SuggestionRegenerateResponse,
    suggestion_to_response,
)
from pipeline.domain.services.suggestion_generator import (
    DISMISS_RESPECT_WINDOW_DAYS,
    SUGGESTION_CAP,
    SuggestionGenerator,
    SuggestionGeneratorConfig,
)
from pipeline.domain.types.suggestion import SuggestionDraft


async def regenerate_for_report(
    *,
    workspace_id: str,
    report_id: str,
    db: AsyncSession,
    repo: SuggestionRepositoryProtocol,
) -> SuggestionRegenerateResponse:
    report = await fetch_report(workspace_id, report_id, db=db)
    artifact = report.analysis_artifact
    if artifact is None or not artifact.content_json:
        raise NotFoundError(
            "Este relatório não tem snapshot E5 — não é possível gerar sugestões.",
            code="report_without_snapshot",
        )

    snapshot = artifact.content_json
    if not isinstance(snapshot, dict):
        raise ValidationError(
            f"Snapshot inválido: esperado dict, recebido {type(snapshot).__name__}",
            code="snapshot_not_dict",
        )

    drafts = SuggestionGenerator(SuggestionGeneratorConfig()).generate(snapshot)
    drafts = drafts[:SUGGESTION_CAP]

    return await _persist_drafts(
        drafts,
        workspace_id=workspace_id,
        report_id=report_id,
        repo=repo,
    )


async def _persist_drafts(
    drafts: Iterable[SuggestionDraft],
    *,
    workspace_id: str,
    report_id: str,
    repo: SuggestionRepositoryProtocol,
) -> SuggestionRegenerateResponse:
    drafts_list = list(drafts)
    created: list[Suggestion] = []
    skipped_dedup = 0
    now = datetime.now(timezone.utc)

    for draft in drafts_list:
        existing = await repo.get_by_dedup_key(workspace_id, draft.dedup_key)
        if _should_skip(existing, now=now):
            skipped_dedup += 1
            continue
        suggestion = Suggestion(
            workspace_id=workspace_id,
            report_id=report_id,
            section_id=draft.section_id,
            kind=draft.kind,
            origin=draft.origin,
            severity=draft.severity,
            title=draft.title,
            rationale=draft.rationale,
            amount_brl_cents=brl_to_cents(draft.amount_brl),
            dedup_key=draft.dedup_key,
            status="Pendente",
        )
        await repo.add(suggestion)
        created.append(suggestion)

    return SuggestionRegenerateResponse(
        created=len(created),
        skipped_dedup=skipped_dedup,
        skipped_cap=0,  # cap já aplicado no caller — cosmético no payload
        total_drafts=len(drafts_list),
        suggestions=[suggestion_to_response(s) for s in created],
    )


def _should_skip(existing: list[Suggestion], *, now: datetime) -> bool:
    """Política de dedup (ADR-153 §2):

    - Pendente/Aceita/Modificada existente → skip (idempotência).
    - Descartada existente:
        - dismissed_at < ``DISMISS_RESPECT_WINDOW_DAYS`` atrás → skip.
        - dismissed_at ≥ ``DISMISS_RESPECT_WINDOW_DAYS`` atrás → permite
          recriar (revisitar tese).
    """
    if not existing:
        return False
    for row in existing:
        if row.status in ("Pendente", "Aceita", "Modificada"):
            return True
        if row.status == "Descartada":
            if row.dismissed_at is None:
                return True
            age_days = (now - row.dismissed_at).total_seconds() / 86400
            if age_days < DISMISS_RESPECT_WINDOW_DAYS:
                return True
    return False
