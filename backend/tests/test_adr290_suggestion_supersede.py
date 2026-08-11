"""Semântica ADR-290 que sobrevive à ADR-376: retry do mesmo run é no-op (B6), aceitas/deterministic intocadas (B3/B5), janela de dismiss por tese não recria (B4), thesis_key persistido na escrita (B1). Expiração por parecer-fonte vive em test_adr376_expiry_lifecycle.py."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from sqlalchemy.orm import Session

from backend.app.core.database import SyncSessionLocal
from backend.app.services.parecer_finalization import compute_suggestion_thesis_key
from backend.tests import factories
from backend.tests.parecer_suggestion_fixtures import (
    all_suggestions,
    by_status,
    default_thesis,
    make_run_with_acoes,
    persist_run,
    seed_suggestion,
)


@pytest.fixture
def sync_session() -> Generator[Session, None, None]:
    s = SyncSessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.mark.asyncio
async def test_second_run_supersedes_obsolete_thesis(db, sync_session):
    """Tese que não reaparece no run novo vira Superseded; count(Pendente) não cresce."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva"}])
    run2 = await make_run_with_acoes(
        db, workspace, [{"acao": "rever alocacao em renda fixa", "tema": "Alocação"}]
    )
    await db.commit()
    persist_run(sync_session, workspace.id, run1.id)
    persist_run(sync_session, workspace.id, run2.id)

    pendentes = by_status(sync_session, workspace.id, "Pendente")
    superseded = by_status(sync_session, workspace.id, "Superseded")
    assert [s.title for s in pendentes] == ["rever alocacao em renda fixa"]
    assert [s.title for s in superseded] == ["aumentar reserva"]
    assert superseded[0].superseded_by_run_id == run2.id


@pytest.mark.asyncio
async def test_same_run_retry_does_not_supersede(db, sync_session):
    """2ª chamada para o MESMO run é no-op (guard run-level, B6)."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva"}])
    await db.commit()
    persist_run(sync_session, workspace.id, run1.id)
    persist_run(sync_session, workspace.id, run1.id)

    assert len(by_status(sync_session, workspace.id, "Pendente")) == 1
    assert len(by_status(sync_session, workspace.id, "Superseded")) == 0


@pytest.mark.asyncio
async def test_reworded_thesis_supersedes_old_and_inserts_new(db, sync_session):
    """Mesma tese re-redigida (dedup novo) → antiga Superseded, nova Pendente (KR1)."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva para seis meses"}])
    run2 = await make_run_with_acoes(db, workspace, [{"acao": "elevar a reserva de emergencia"}])
    await db.commit()
    persist_run(sync_session, workspace.id, run1.id)
    persist_run(sync_session, workspace.id, run2.id)

    pendentes = by_status(sync_session, workspace.id, "Pendente")
    superseded = by_status(sync_session, workspace.id, "Superseded")
    assert [s.title for s in pendentes] == ["elevar a reserva de emergencia"]
    assert len(superseded) == 1
    assert pendentes[0].thesis_key == superseded[0].thesis_key


@pytest.mark.asyncio
async def test_accepted_suggestion_never_superseded(db, sync_session):
    """Aceita (histórico sagrado, B3) nunca entra no conjunto expirável."""
    workspace = await factories.make_workspace(db)
    run2 = await make_run_with_acoes(
        db, workspace, [{"acao": "rever alocacao", "tema": "Alocação"}]
    )
    await db.commit()
    seed_suggestion(
        sync_session,
        workspace.id,
        title="aceita historica",
        dedup_key="c" * 64,
        thesis_key="d" * 64,
        status="Aceita",
    )
    persist_run(sync_session, workspace.id, run2.id)

    aceitas = by_status(sync_session, workspace.id, "Aceita")
    assert len(aceitas) == 1
    assert aceitas[0].superseded_at is None


@pytest.mark.asyncio
async def test_deterministic_origin_untouched(db, sync_session):
    """origin='deterministic' tem ciclo de vida próprio (B5) — intocado."""
    workspace = await factories.make_workspace(db)
    run2 = await make_run_with_acoes(db, workspace, [{"acao": "rever alocacao"}])
    await db.commit()
    seed_suggestion(
        sync_session,
        workspace.id,
        title="deterministica",
        kind="reserva_insuficiente",
        origin="deterministic",
        dedup_key="e" * 64,
        thesis_key="f" * 64,
    )
    persist_run(sync_session, workspace.id, run2.id)

    rows = {s.title: s.status for s in all_suggestions(sync_session, workspace.id)}
    assert rows["deterministica"] == "Pendente"


@pytest.mark.asyncio
async def test_dismissed_thesis_within_window_not_recreated(db, sync_session):
    """Descartada <90d com mesma tese bloqueia recriação re-redigida (B4)."""
    workspace = await factories.make_workspace(db)
    run2 = await make_run_with_acoes(db, workspace, [{"acao": "elevar reserva com nova redacao"}])
    await db.commit()
    seed_suggestion(
        sync_session,
        workspace.id,
        title="descartada recente",
        dedup_key="2" * 64,
        thesis_key=default_thesis(workspace.id),
        status="Descartada",
        dismissed_reason="nao_se_aplica",
        dismissed_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    persist_run(sync_session, workspace.id, run2.id)

    assert len(by_status(sync_session, workspace.id, "Pendente")) == 0


@pytest.mark.asyncio
async def test_thesis_key_persisted_on_insert(db, sync_session):
    """B1 — thesis_key gravado na escrita = sha256(ws|tema|section|ancora); lineage do run gravada (ADR-376 §D1)."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva"}])
    await db.commit()
    persist_run(sync_session, workspace.id, run1.id)

    rows = all_suggestions(sync_session, workspace.id)
    assert rows[0].thesis_key == compute_suggestion_thesis_key(
        workspace_id=workspace.id, tema_canonico="Liquidez", section_id="S3", ancora="convergencia"
    )
    assert rows[0].pipeline_run_id == run1.id


@pytest.mark.asyncio
async def test_thesis_key_null_when_source_field_missing(db, sync_session):
    """Artifact sem tema_canonico → thesis_key=None (fallback seguro, B1)."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva", "tema": None}])
    await db.commit()
    persist_run(sync_session, workspace.id, run1.id)

    rows = all_suggestions(sync_session, workspace.id)
    assert len(rows) == 1
    assert rows[0].thesis_key is None
