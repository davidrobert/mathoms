"""Testes dos use cases de Suggestion (ADR-153).

Cobrem felicidade + erros de domínio (NotFound, Conflict, Validation),
incluindo o fluxo accept que cria Decision via use case canônico.

Valores fictícios — nunca dados reais (CLAUDE.md §Dados sensíveis).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from backend.app.application.suggestions import (
    accept_suggestion,
    count_suggestions,
    dismiss_suggestion,
    get_suggestion,
    list_suggestions,
    modify_suggestion,
)
from backend.app.models.suggestion import Suggestion
from backend.app.repositories.decision_repository import DecisionRepository
from backend.app.repositories.suggestion_repository import SuggestionRepository
from backend.app.schemas.dto.suggestion import (
    AcceptSuggestionCommand,
    DismissSuggestionCommand,
    ModifySuggestionCommand,
)
from backend.tests.factories.builders import make_workspace


@pytest_asyncio.fixture
async def setup(db: AsyncSession):
    ws = await make_workspace(db, name="WS Sug")
    await db.commit()
    return ws, SuggestionRepository(db), DecisionRepository(db)


async def _seed_pending(
    db: AsyncSession,
    workspace_id: str,
    *,
    kind: str = "reserva_insuficiente",
    section: str = "S2",
    title: str = "Reforçar reserva",
    rationale: str = "Cobertura insuficiente",
    amount_cents: int | None = 500_000,
    dedup_key: str = "k1" * 16,
) -> Suggestion:
    s = Suggestion(
        workspace_id=workspace_id,
        section_id=section,
        kind=kind,
        origin="deterministic",
        severity="warning",
        title=title,
        rationale=rationale,
        amount_brl_cents=amount_cents,
        dedup_key=dedup_key,
        status="Pendente",
    )
    db.add(s)
    await db.flush()
    return s


@pytest.mark.asyncio
async def test_list_filters_by_status(db, setup):
    ws, repo, _ = setup
    await _seed_pending(db, ws.id, dedup_key="k1" * 16)
    await _seed_pending(db, ws.id, kind="trs_desalinhada", dedup_key="k2" * 16)
    await db.commit()

    resp = await list_suggestions(ws.id, status="Pendente", repo=repo)
    assert resp.total == 2
    assert all(s.status == "Pendente" for s in resp.suggestions)


@pytest.mark.asyncio
async def test_list_invalid_status_raises_validation(db, setup):
    ws, repo, _ = setup
    with pytest.raises(ValidationError):
        await list_suggestions(ws.id, status="naoExiste", repo=repo)


@pytest.mark.asyncio
async def test_count_default_pendente(db, setup):
    ws, repo, _ = setup
    await _seed_pending(db, ws.id)
    await db.commit()
    resp = await count_suggestions(ws.id, repo=repo)
    assert resp.count == 1
    assert resp.status == "Pendente"


@pytest.mark.asyncio
async def test_get_404_for_nonexistent(db, setup):
    ws, repo, _ = setup
    with pytest.raises(NotFoundError):
        await get_suggestion(ws.id, "00000000-0000-0000-0000-000000000000", repo=repo)


@pytest.mark.asyncio
async def test_dismiss_marks_descartada_with_reason(db, setup):
    ws, repo, _ = setup
    s = await _seed_pending(db, ws.id)
    resp = await dismiss_suggestion(
        DismissSuggestionCommand(reason="ja_considerei"),
        workspace_id=ws.id,
        suggestion_id=s.id,
        repo=repo,
    )
    assert resp.status == "Descartada"
    assert resp.dismissed_reason == "ja_considerei"
    assert resp.dismissed_at is not None


@pytest.mark.asyncio
async def test_dismiss_already_terminal_raises_conflict(db, setup):
    ws, repo, _ = setup
    s = await _seed_pending(db, ws.id)
    await dismiss_suggestion(
        DismissSuggestionCommand(reason="adiar"),
        workspace_id=ws.id,
        suggestion_id=s.id,
        repo=repo,
    )
    with pytest.raises(ConflictError):
        await dismiss_suggestion(
            DismissSuggestionCommand(reason="outro"),
            workspace_id=ws.id,
            suggestion_id=s.id,
            repo=repo,
        )


@pytest.mark.asyncio
async def test_accept_creates_decision_and_marks_aceita(db, setup):
    ws, sug_repo, dec_repo = setup
    s = await _seed_pending(db, ws.id, amount_cents=500_000)
    await db.commit()

    resp = await accept_suggestion(
        AcceptSuggestionCommand(),
        workspace_id=ws.id,
        suggestion_id=s.id,
        suggestion_repo=sug_repo,
        decision_repo=dec_repo,
        actor="user:t",
    )
    assert resp.status == "Aceita"
    assert resp.accepted_decision_id is not None
    assert resp.accepted_at is not None
    # ADR-214 — server gera code (workspace fresh → D01).
    assert resp.accepted_decision_code == "D01"

    decision = await dec_repo.get_by_code(ws.id, "D01")
    assert decision is not None
    assert decision.title == "Reforçar reserva"
    assert decision.amount_brl_cents == 500_000


@pytest.mark.asyncio
async def test_accept_rejects_non_pending(db, setup):
    ws, sug_repo, dec_repo = setup
    s = await _seed_pending(db, ws.id)
    await dismiss_suggestion(
        DismissSuggestionCommand(reason="adiar"),
        workspace_id=ws.id,
        suggestion_id=s.id,
        repo=sug_repo,
    )
    with pytest.raises(ConflictError):
        await accept_suggestion(
            AcceptSuggestionCommand(),
            workspace_id=ws.id,
            suggestion_id=s.id,
            suggestion_repo=sug_repo,
            decision_repo=dec_repo,
            actor="user:t",
        )


@pytest.mark.asyncio
async def test_modify_overrides_decision_fields(db, setup):
    ws, sug_repo, dec_repo = setup
    s = await _seed_pending(db, ws.id, amount_cents=500_000)
    await db.commit()

    resp = await modify_suggestion(
        ModifySuggestionCommand(
            title="Título customizado",
            amount_brl=Decimal("9000.00"),
        ),
        workspace_id=ws.id,
        suggestion_id=s.id,
        suggestion_repo=sug_repo,
        decision_repo=dec_repo,
        actor="user:t",
    )
    assert resp.status == "Modificada"
    # ADR-214 — server gera code (workspace fresh → D01).
    assert resp.accepted_decision_code == "D01"

    decision = await dec_repo.get_by_code(ws.id, "D01")
    assert decision is not None
    assert decision.title == "Título customizado"
    assert decision.amount_brl_cents == 900_000


@pytest.mark.asyncio
async def test_dismiss_invalid_reason_raises_validation(db, setup):
    ws, repo, _ = setup
    s = await _seed_pending(db, ws.id)
    with pytest.raises(ValueError):
        DismissSuggestionCommand(reason="reason_invalida")
