"""A40.l27 item 4 — `failure_reason` deixa de ser coluna write-only.

A [[ADR-172]] decidiu em 2026-05 que "a UI consome `failure_reason` e mostra mensagem
honesta". O campo nunca entrou em `PipelineRunResponse`, e `rg 'failure_reason' frontend/src`
retornava **zero**. A [[ADR-359]] então acrescentou **três** valores ao vocabulário — sem
read path, os quatro são legíveis só por SQL direto, e a distinção que eles compram
(postmortem: *falhou* vs. *sem dono*) não chega a operador nem a usuário.

Independente do PR1 desta lane de propósito: exercita o **read path**, não a varredura.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.schemas.pipeline import PipelineRunResponse
from backend.app.services.pipeline.pipeline_failure_reasons import ALL_REASONS
from backend.tests.factories.builders import make_user, make_workspace


def test_failure_reason_esta_no_response_model() -> None:
    assert "failure_reason" in PipelineRunResponse.model_fields


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", sorted(ALL_REASONS))
async def test_todo_motivo_do_vocabulario_serializa(db: AsyncSession, reason: str) -> None:
    """Parametrizado por `ALL_REASONS`: valor novo no vocabulário entra no teste sozinho,
    em vez de exigir que alguém lembre de acrescentá-lo."""
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    run = PipelineRun(
        workspace_id=ws.id,
        status=PipelineRunStatus.failed,
        failure_reason=reason,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.commit()
    # `stage_logs` é relationship lazy: sem o refresh explícito, `model_validate` tenta IO
    # sync dentro da sessão async e estoura `MissingGreenlet`. O endpoint real eager-loada.
    await db.refresh(run, attribute_names=["stage_logs"])

    dto = PipelineRunResponse.model_validate(run)

    assert dto.failure_reason == reason


@pytest.mark.asyncio
async def test_run_sem_motivo_serializa_none(db: AsyncSession) -> None:
    """`None` é o caso normal (run bem-sucedido) — não pode virar string vazia nem sumir."""
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    run = PipelineRun(
        workspace_id=ws.id,
        status=PipelineRunStatus.completed,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run, attribute_names=["stage_logs"])

    assert PipelineRunResponse.model_validate(run).failure_reason is None
