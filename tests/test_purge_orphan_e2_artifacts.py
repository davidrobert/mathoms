"""Tests — ``dev/purge_orphan_e2_artifacts.py`` (A32.l1).

Fixture sintética PII-zero em SQLite real (DB nunca mocado), padrão
``tests/test_dedup_property_identity.py``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models import Document, PipelineArtifact, PipelineRun, User, Workspace
from dev.purge_orphan_e2_artifacts import (
    VERDICT_CURRENT,
    VERDICT_ORPHAN,
    VERDICT_STALE,
    VERDICT_UNMATCHED,
    delete_orphans,
    find_e2_llm_findings,
    main,
)

_HASH_ORPHAN_A = "aaaaaaaaaaaa"
_HASH_ORPHAN_B = "bbbbbbbbbbbb"
_HASH_STALE = "cccccccccccc"
_HASH_CURRENT = "dddddddddddd"
_STALE_DT = datetime(2026, 5, 23, 13, 0, 0)
_CURRENT_DT = datetime(2026, 7, 7, 10, 0, 0)


@pytest.fixture
def sync_db(tmp_path):
    db_file = tmp_path / "test_purge_orphans.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _seed_workspace_and_run(session) -> tuple[str, str]:
    user = User(
        id=str(uuid.uuid4()),
        email=f"u-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="x",
        full_name="Test",
    )
    session.add(user)
    session.flush()
    ws = Workspace(id=str(uuid.uuid4()), name="Test WS", owner_id=user.id)
    session.add(ws)
    session.flush()
    run = PipelineRun(id=str(uuid.uuid4()), workspace_id=ws.id, status="completed")
    session.add(run)
    session.flush()
    return ws.id, run.id


def _seed_document(session, ws_id: str, *, content_hash12: str, doc_type: str) -> str:
    doc = Document(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        original_name=f"{content_hash12}_bancox_doc-0_original.pdf",
        doc_type=doc_type,
        content_hash=content_hash12 + "0" * 52,
    )
    session.add(doc)
    session.flush()
    return doc.id


def _seed_artifact(
    session, ws_id: str, run_id: str, *, stage: str, key: str, created_at: datetime
) -> int:
    art = PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage=stage,
        artifact_key=key,
        content_json={"synthetic": True},
        created_at=created_at,
    )
    session.add(art)
    session.flush()
    return art.id


# (hash12, doc_type) dos documentos sintéticos do corpus.
_CORPUS_DOCS = (
    (_HASH_ORPHAN_A, "informe_rendimentos_anuais"),
    (_HASH_ORPHAN_B, "informe_rendimentos_anuais"),
    (_HASH_STALE, "bank_statement"),
    (_HASH_CURRENT, "bank_statement"),
)

# label → (stage, artifact_key, created_at). "e3_untouched" reusa a key do
# órfão em stage E3 — fora do escopo do script, nunca tocado.
_CORPUS_ARTIFACTS = {
    "orphan_legacy": ("E2-llm", f"{_HASH_ORPHAN_A}_bancox_cdbdetalhes_2025", _STALE_DT),
    "orphan_descriptive": (
        "extract_with_llm",
        f"{_HASH_ORPHAN_B}_bancox_investimentosposicao_202603",
        _STALE_DT,
    ),
    "stale": ("E2-llm", f"{_HASH_STALE}_bancox_cdbdetalhes_2026", _STALE_DT),
    "current": ("extract_with_llm", f"{_HASH_CURRENT}_bancox_extratoconta_202607", _CURRENT_DT),
    "unmatched": ("E2-llm", "sem_prefixo_hash_bancox_2026", _STALE_DT),
    "e3_untouched": (
        "reconcile_transactions",
        f"{_HASH_ORPHAN_A}_bancox_cdbdetalhes_2025",
        _STALE_DT,
    ),
}


def _seed_incident_corpus(session) -> dict[str, int]:
    """2 órfãos (ambas as grafias de stage) + 1 stale + 1 current + 1 unmatched + 1 E3."""
    ws_id, run_id = _seed_workspace_and_run(session)
    for hash12, doc_type in _CORPUS_DOCS:
        _seed_document(session, ws_id, content_hash12=hash12, doc_type=doc_type)
    ids = {
        label: _seed_artifact(session, ws_id, run_id, stage=stage, key=key, created_at=dt)
        for label, (stage, key, dt) in _CORPUS_ARTIFACTS.items()
    }
    session.commit()
    return ids


def _artifact_ids(session) -> set[int]:
    return {r[0] for r in session.execute(text("SELECT id FROM pipeline_artifacts")).all()}


def test_findings_classify_orphan_stale_current_unmatched(sync_db):
    with sync_db() as session:
        ids = _seed_incident_corpus(session)
        verdicts = {f.artifact_id: f.verdict for f in find_e2_llm_findings(session)}
    assert verdicts[ids["orphan_legacy"]] == VERDICT_ORPHAN
    assert verdicts[ids["orphan_descriptive"]] == VERDICT_ORPHAN
    assert verdicts[ids["stale"]] == VERDICT_STALE
    assert verdicts[ids["current"]] == VERDICT_CURRENT
    assert verdicts[ids["unmatched"]] == VERDICT_UNMATCHED
    assert ids["e3_untouched"] not in verdicts


def test_document_match_is_workspace_scoped(sync_db):
    """Doc com mesmo hash em outro workspace não pode tornar artifact órfão."""
    with sync_db() as session:
        ws_a, run_a = _seed_workspace_and_run(session)
        ws_b, _ = _seed_workspace_and_run(session)
        _seed_document(
            session, ws_b, content_hash12=_HASH_ORPHAN_A, doc_type="informe_rendimentos_anuais"
        )
        art = _seed_artifact(
            session,
            ws_a,
            run_a,
            stage="E2-llm",
            key=f"{_HASH_ORPHAN_A}_bancox_cdbdetalhes_2025",
            created_at=_STALE_DT,
        )
        session.commit()
        verdicts = {f.artifact_id: f.verdict for f in find_e2_llm_findings(session)}
    assert verdicts[art] == VERDICT_UNMATCHED


def test_delete_removes_only_orphans(sync_db):
    with sync_db() as session:
        ids = _seed_incident_corpus(session)
        findings = find_e2_llm_findings(session)
        orphans = [f for f in findings if f.verdict == VERDICT_ORPHAN]
        deleted = delete_orphans(session, orphans, max_delete=2)
        session.commit()
        remaining = _artifact_ids(session)
    assert deleted == 2
    assert ids["orphan_legacy"] not in remaining
    assert ids["orphan_descriptive"] not in remaining
    assert {ids["stale"], ids["current"], ids["unmatched"], ids["e3_untouched"]} <= remaining


def test_second_execution_is_idempotent(sync_db):
    with sync_db() as session:
        _seed_incident_corpus(session)
        first = [f for f in find_e2_llm_findings(session) if f.verdict == VERDICT_ORPHAN]
        delete_orphans(session, first, max_delete=2)
        session.commit()
        second = [f for f in find_e2_llm_findings(session) if f.verdict == VERDICT_ORPHAN]
        deleted_again = delete_orphans(session, second, max_delete=2)
        session.commit()
    assert second == []
    assert deleted_again == 0


def test_max_delete_guard_aborts_without_deleting(sync_db):
    with sync_db() as session:
        ids = _seed_incident_corpus(session)
        orphans = [f for f in find_e2_llm_findings(session) if f.verdict == VERDICT_ORPHAN]
        with pytest.raises(RuntimeError, match="max-delete"):
            delete_orphans(session, orphans, max_delete=1)
        session.rollback()
        remaining = _artifact_ids(session)
    assert {ids["orphan_legacy"], ids["orphan_descriptive"]} <= remaining


def test_cli_dry_run_is_default_and_mutates_nothing(sync_db, tmp_path, capsys):
    db_file = tmp_path / "test_purge_orphans.db"
    with sync_db() as session:
        ids = _seed_incident_corpus(session)
    rc = main(["--db-url", f"sqlite:///{db_file}"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "DRY-RUN" in out
    assert "nada foi deletado" in out
    with sync_db() as session:
        remaining = _artifact_ids(session)
    assert set(ids.values()) <= remaining


def test_cli_execute_deletes_orphans(sync_db, tmp_path, capsys):
    db_file = tmp_path / "test_purge_orphans.db"
    with sync_db() as session:
        ids = _seed_incident_corpus(session)
    rc = main(["--db-url", f"sqlite:///{db_file}", "--execute"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Deletados: 2 artifact(s)" in out
    with sync_db() as session:
        remaining = _artifact_ids(session)
    assert ids["orphan_legacy"] not in remaining
    assert ids["orphan_descriptive"] not in remaining
    assert {ids["stale"], ids["current"], ids["unmatched"], ids["e3_untouched"]} <= remaining
