"""Expiração por parecer-fonte (ADR-376) — aceite F5 do PLAN-suggestion-lifecycle: run ENTREGUE expira todas as pendentes anteriores (inclusive thesis_key NULL) e insere o conjunto vigente; retido/vazio não expira; reafirmação re-entra fresca; contadores KR4."""

from __future__ import annotations

from typing import Generator

import pytest
from sqlalchemy.orm import Session

from backend.app.core.database import SyncSessionLocal
from backend.app.services.parecer_finalization import compute_suggestion_dedup_key
from backend.app.services.planner_review_persistence import persist_planner_review
from backend.tests import factories
from backend.tests.parecer_suggestion_fixtures import (
    all_suggestions,
    by_status,
    expire_stats_for_run,
    make_detail,
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


# ADR-376 §D1: dedup_key não cobre rationale/valor — manter a row antiga
# preservaria conteúdo defasado (o contrato pré-376 mantinha a original).
@pytest.mark.asyncio
async def test_reappearing_same_wording_reissued_fresh(db, sync_session):
    """Mesma tese + mesma redação no run novo → antiga Superseded, nova Pendente do run vigente."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva"}])
    run2 = await make_run_with_acoes(
        db, workspace, [{"acao": "aumentar reserva", "impacto": "impacto atualizado de agosto"}]
    )
    await db.commit()
    persist_run(sync_session, workspace.id, run1.id)
    persist_run(sync_session, workspace.id, run2.id)

    pendentes = by_status(sync_session, workspace.id, "Pendente")
    superseded = by_status(sync_session, workspace.id, "Superseded")
    assert len(pendentes) == 1 and len(superseded) == 1
    assert pendentes[0].dedup_key == superseded[0].dedup_key
    assert pendentes[0].pipeline_run_id == run2.id
    assert pendentes[0].rationale == "impacto atualizado de agosto"


@pytest.mark.asyncio
async def test_accepted_dedup_key_blocks_reissue(db, sync_session):
    """ADR-376 §D2: reemissão byte-idêntica de texto já Aceito é skipada como dup — a Decision carrega o trabalho; não nasce Pendente concorrente."""
    workspace = await factories.make_workspace(db)
    acao = "rever alocacao em renda fixa"
    run2 = await make_run_with_acoes(db, workspace, [{"acao": acao}])
    await db.commit()
    dedup = compute_suggestion_dedup_key(
        workspace_id=workspace.id, ancora="convergencia", acao=acao
    )
    seed_suggestion(sync_session, workspace.id, title=acao, dedup_key=dedup, status="Aceita")
    persist_run(sync_session, workspace.id, run2.id)

    assert len(by_status(sync_session, workspace.id, "Pendente")) == 0
    assert len(by_status(sync_session, workspace.id, "Aceita")) == 1


@pytest.mark.asyncio
async def test_null_thesis_key_expired_on_delivered_run(db, sync_session):
    """ADR-376 §D1: pendente com thesis_key NULL (zumbi pós-backfill F4) EXPIRA em run entregue — inverte o fallback pré-376 que a deixava imortal."""
    workspace = await factories.make_workspace(db)
    run2 = await make_run_with_acoes(db, workspace, [{"acao": "rever alocacao"}])
    await db.commit()
    seed_suggestion(
        sync_session, workspace.id, title="legada sem thesis", dedup_key="1" * 64, thesis_key=None
    )
    persist_run(sync_session, workspace.id, run2.id)

    rows = {s.title: s.status for s in all_suggestions(sync_session, workspace.id)}
    assert rows["legada sem thesis"] == "Superseded"
    assert rows["rever alocacao"] == "Pendente"


@pytest.mark.asyncio
async def test_retido_run_does_not_expire_inbox(db, sync_session):
    """ADR-376 §D1 guard (senior-cto B-1): run retido não entregou — pendentes anteriores sobrevivem e nada é inserido."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva"}])
    run2 = await make_run_with_acoes(db, workspace, [{"acao": "rever alocacao"}])
    await db.commit()
    persist_run(sync_session, workspace.id, run1.id)
    persist_run(
        sync_session,
        workspace.id,
        run2.id,
        status="needs_review",
        retention_reason="citation_verification_failed",
    )

    pendentes = by_status(sync_session, workspace.id, "Pendente")
    assert [s.title for s in pendentes] == ["aumentar reserva"]
    assert len(by_status(sync_session, workspace.id, "Superseded")) == 0


@pytest.mark.asyncio
async def test_empty_delivered_artifact_does_not_expire(db, sync_session):
    """Defesa em profundidade: artifact entregue porém sem sugestões não expira nada — nunca é legítimo esvaziar o inbox sem conjunto substituto."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva"}])
    run2 = await make_run_with_acoes(db, workspace, [])
    await db.commit()
    persist_run(sync_session, workspace.id, run1.id)
    persist_run(sync_session, workspace.id, run2.id)

    assert len(by_status(sync_session, workspace.id, "Pendente")) == 1
    assert len(by_status(sync_session, workspace.id, "Superseded")) == 0


# 3 runs: X → X reafirmada → Y. O UNIQUE full antigo quebrava na 2ª Superseded
# de mesma dedup_key; o índice parcial (só status ativos) permite (ADR-376 §D3).
@pytest.mark.asyncio
async def test_same_dedup_key_superseded_twice_no_constraint_violation(db, sync_session):
    """2 Superseded com a MESMA dedup_key coexistem; Pendente final é só a do run 3."""
    workspace = await factories.make_workspace(db)
    runs = [
        await make_run_with_acoes(db, workspace, [{"acao": acao}])
        for acao in ("aumentar reserva", "aumentar reserva", "rever alocacao")
    ]
    await db.commit()
    for run in runs:
        persist_run(sync_session, workspace.id, run.id)

    superseded = by_status(sync_session, workspace.id, "Superseded")
    dups = [s for s in superseded if s.title == "aumentar reserva"]
    assert len(dups) == 2
    assert dups[0].dedup_key == dups[1].dedup_key
    assert [s.title for s in by_status(sync_session, workspace.id, "Pendente")] == [
        "rever alocacao"
    ]


@pytest.mark.asyncio
async def test_horizon_persisted_per_bucket(db, sync_session):
    """ADR-376 §D4: bucket do artifact vira horizon canônico na row — antes era descartado em _iter_sugestoes."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(
        db,
        workspace,
        [{"acao": "acao de execucao"}],
        taticas=[{"acao": "acao tatica", "tema": "Alocação"}],
        estrategicas=[{"acao": "acao estrategica", "tema": "Sucessão", "section_id": "S9"}],
    )
    await db.commit()
    persist_run(sync_session, workspace.id, run1.id)

    horizons = {s.title: s.horizon for s in all_suggestions(sync_session, workspace.id)}
    assert horizons == {
        "acao de execucao": "execucao",
        "acao tatica": "tatica",
        "acao estrategica": "estrategica",
    }


@pytest.mark.asyncio
async def test_expire_insert_survives_no_autoflush(db, sync_session):
    """Senior-cto B-2: a ordem expire→flush→insert é do CÓDIGO, não do autoflush da sessão — sob no_autoflush a reafirmação não viola o índice único parcial."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva"}])
    run2 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva"}])
    await db.commit()
    persist_run(sync_session, workspace.id, run1.id)
    with sync_session.no_autoflush:
        persist_planner_review(
            sync_session, workspace_id=workspace.id, run_id=run2.id, detail=make_detail()
        )
    sync_session.commit()

    assert len(by_status(sync_session, workspace.id, "Pendente")) == 1
    assert len(by_status(sync_session, workspace.id, "Superseded")) == 1


# Run que expira 2, recria 1 reafirmada e insere 1 nova. pending_after é o
# único contador que enxerga "inbox esvaziou" (senior-cto M-1).
@pytest.mark.asyncio
async def test_stats_counters_kr4(db, sync_session):
    """KR4 (ADR-376 §D5): superseded/created/reemitted/pending_after/skipped_dup."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(
        db, workspace, [{"acao": "aumentar reserva"}, {"acao": "rever alocacao"}]
    )
    run2 = await make_run_with_acoes(
        db, workspace, [{"acao": "aumentar reserva"}, {"acao": "dolarizar parte da carteira"}]
    )
    await db.commit()
    persist_run(sync_session, workspace.id, run1.id)
    stats = expire_stats_for_run(sync_session, workspace.id, run2.id)

    expected = {"suggestions_superseded": 2, "suggestions_created": 2, "reemitted": 1}
    expected.update({"pending_after": 2, "skipped_dup": 0})
    assert {k: stats[k] for k in expected} == expected
