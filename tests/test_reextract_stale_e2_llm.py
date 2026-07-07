"""Tests — ``dev/reextract_stale_e2_llm.py`` (A32.l5, ADR-311).

Fixture sintética PII-zero em SQLite real (DB nunca mocado), padrão
``tests/test_purge_orphan_e2_artifacts.py`` (A32.l1). O script só
seleciona/invalida-e-dispara — nenhuma chamada LLM é feita.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models import Document, PipelineArtifact, PipelineRun, User, Workspace
from dev.reextract_stale_e2_llm import (
    find_stale_artifacts,
    invalidate_stale,
    main,
    parse_semver,
)

_HASH_STALE_A = "aaaaaaaaaaaa"
_HASH_STALE_B = "bbbbbbbbbbbb"
_HASH_CURRENT = "cccccccccccc"
_DT = datetime(2026, 5, 23, 13, 0, 0)


@pytest.fixture
def sync_db(tmp_path):
    db_file = tmp_path / "test_reextract_stale.db"
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


def _seed_document(session, ws_id: str, *, content_hash12: str) -> str:
    doc = Document(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        original_name=f"{content_hash12}_bancox_doc-0_original.pdf",
        doc_type="investment_report",
        content_hash=content_hash12 + "0" * 52,
        pipeline_last_run_at=_DT,
        pipeline_e2_extract_ok=True,
    )
    session.add(doc)
    session.flush()
    return doc.id


def _seed_artifact(session, ws_id, run_id, *, stage, key, prompt_version, created_at=_DT) -> int:
    art = PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage=stage,
        artifact_key=key,
        prompt_version=prompt_version,
        content_json={"synthetic": True},
        created_at=created_at,
    )
    session.add(art)
    session.flush()
    return art.id


# label → (stage, artifact_key, prompt_version). NULL e semver antigo são
# stale; versão corrente e stage E3 ficam fora.
_CORPUS = {
    "stale_null_legacy": ("E2-llm", f"{_HASH_STALE_A}_bancox_cdbdetalhes_2025", None),
    "stale_old_descriptive": (
        "extract_with_llm",
        f"{_HASH_STALE_B}_bancox_investimentosposicao_202603",
        "1.2.0",
    ),
    "current": ("extract_with_llm", f"{_HASH_CURRENT}_bancox_extratoconta_202607", "1.3.0"),
    "e3_untouched": ("reconcile_transactions", f"{_HASH_STALE_A}_bancox_cdbdetalhes_2025", None),
}


def _seed_corpus(session) -> tuple[str, dict[str, int]]:
    ws_id, run_id = _seed_workspace_and_run(session)
    for hash12 in (_HASH_STALE_A, _HASH_STALE_B, _HASH_CURRENT):
        _seed_document(session, ws_id, content_hash12=hash12)
    ids = {
        label: _seed_artifact(session, ws_id, run_id, stage=stage, key=key, prompt_version=pv)
        for label, (stage, key, pv) in _CORPUS.items()
    }
    session.commit()
    return ws_id, ids


def _artifact_ids(session) -> set[int]:
    return {r[0] for r in session.execute(text("SELECT id FROM pipeline_artifacts")).all()}


def test_parse_semver_orders_null_below_any_target():
    assert parse_semver(None) == (0,)
    assert parse_semver("garbage") == (0,)
    assert parse_semver("1.3.0") == (1, 3, 0)
    assert parse_semver(None) < parse_semver("1.3.0")
    assert parse_semver("1.2.0") < parse_semver("1.3.0")
    assert parse_semver("1.10.0") > parse_semver("1.3.0")  # não-lexicográfico


def test_find_stale_selects_null_and_older_versions_only(sync_db):
    with sync_db() as session:
        _, ids = _seed_corpus(session)
        stale_ids = {a.artifact_id for a in find_stale_artifacts(session, target_version="1.3.0")}
    assert stale_ids == {ids["stale_null_legacy"], ids["stale_old_descriptive"]}


def _document_pipeline_flags(session) -> dict[str, tuple]:
    rows = session.execute(
        text(
            "SELECT content_hash, pipeline_last_run_at, pipeline_e2_extract_ok "
            "FROM documents ORDER BY content_hash"
        )
    ).all()
    return {r[0][:12]: (r[1], r[2]) for r in rows}


def test_invalidate_deletes_stale_and_requeues_documents(sync_db):
    with sync_db() as session:
        _, ids = _seed_corpus(session)
        stale = find_stale_artifacts(session, target_version="1.3.0")
        deleted, requeued = invalidate_stale(session, stale, max_invalidate=15)
        session.commit()
        remaining = _artifact_ids(session)
        by_hash = _document_pipeline_flags(session)
    assert (deleted, requeued) == (2, 2)
    assert ids["stale_null_legacy"] not in remaining
    assert ids["stale_old_descriptive"] not in remaining
    assert {ids["current"], ids["e3_untouched"]} <= remaining
    assert by_hash[_HASH_STALE_A] == (None, None)
    assert by_hash[_HASH_STALE_B] == (None, None)
    assert by_hash[_HASH_CURRENT] != (None, None)


def test_max_invalidate_guard_aborts_without_mutation(sync_db):
    with sync_db() as session:
        _, ids = _seed_corpus(session)
        stale = find_stale_artifacts(session, target_version="1.3.0")
        with pytest.raises(RuntimeError, match="max-invalidate"):
            invalidate_stale(session, stale, max_invalidate=1)
        session.rollback()
        assert set(ids.values()) <= _artifact_ids(session)


def test_second_execution_is_idempotent(sync_db):
    with sync_db() as session:
        _seed_corpus(session)
        first = find_stale_artifacts(session, target_version="1.3.0")
        invalidate_stale(session, first, max_invalidate=15)
        session.commit()
        second = find_stale_artifacts(session, target_version="1.3.0")
        deleted, requeued = invalidate_stale(session, second, max_invalidate=15)
        session.commit()
    assert second == []
    assert (deleted, requeued) == (0, 0)


def test_cli_dry_run_is_default_and_mutates_nothing(sync_db, tmp_path, capsys):
    db_file = tmp_path / "test_reextract_stale.db"
    with sync_db() as session:
        _, ids = _seed_corpus(session)
    rc = main(["--db-url", f"sqlite:///{db_file}", "--target-version", "1.3.0"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "DRY-RUN" in out
    assert "nada foi invalidado" in out
    with sync_db() as session:
        assert set(ids.values()) <= _artifact_ids(session)


def test_cli_execute_invalidates_and_reports_no_llm_call(sync_db, tmp_path, capsys):
    db_file = tmp_path / "test_reextract_stale.db"
    with sync_db() as session:
        _, ids = _seed_corpus(session)
    rc = main(["--db-url", f"sqlite:///{db_file}", "--target-version", "1.3.0", "--execute"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Invalidados: 2 artifact(s)" in out
    assert "Nenhuma chamada LLM" in out
    with sync_db() as session:
        remaining = _artifact_ids(session)
    assert ids["stale_null_legacy"] not in remaining
    assert {ids["current"], ids["e3_untouched"]} <= remaining


def _make_pre_migration_db(db_file) -> None:
    """SQLite com schema atual MENOS a coluna prompt_version + 1 row E2-llm."""
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE pipeline_artifacts DROP COLUMN prompt_version"))
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory() as session:
        ws_id, run_id = _seed_workspace_and_run(session)
        session.execute(
            text(
                "INSERT INTO pipeline_artifacts "
                "(workspace_id, pipeline_run_id, stage, artifact_key, content_json, created_at) "
                "VALUES (:ws, :run, 'E2-llm', 'aaaaaaaaaaaa_bancox_doc_2026', '{}', :dt)"
            ),
            {"ws": ws_id, "run": run_id, "dt": _DT},
        )
        session.commit()


def test_pre_migration_db_lists_all_as_unknown_but_refuses_execute(tmp_path, capsys):
    """DB sem a coluna (pré ``a32l5promptver``): dry-run trata tudo como versão 0; --execute aborta pedindo migration."""
    db_file = tmp_path / "pre_migration.db"
    _make_pre_migration_db(db_file)

    rc = main(["--db-url", f"sqlite:///{db_file}", "--target-version", "1.3.0"])
    assert rc == 0
    assert "NULL(=0)" in capsys.readouterr().out

    rc = main(["--db-url", f"sqlite:///{db_file}", "--target-version", "1.3.0", "--execute"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "migration a32l5promptver" in out


def _seed_two_generations(session) -> int:
    """Row antiga (mai) + row de hoje, ambas prompt_version NULL. Retorna o id da antiga."""
    ws_id, run_id = _seed_workspace_and_run(session)
    old_key = f"{_HASH_STALE_A}_bancox_cdbdetalhes_2025"
    new_key = f"{_HASH_CURRENT}_bancox_extratoconta_202607"
    today = datetime(2026, 7, 7, 10, 0, 0)
    old = _seed_artifact(session, ws_id, run_id, stage="E2-llm", key=old_key, prompt_version=None)
    _seed_artifact(
        session,
        ws_id,
        run_id,
        stage="extract_with_llm",
        key=new_key,
        prompt_version=None,
        created_at=today,
    )
    session.commit()
    return old


def test_created_before_filter_separates_generations(sync_db):
    """Rows pré-migration são todas NULL; --created-before separa os stale de mai/jun das rows de vocabulário atual (mesmo NULL) — precisão do gate l7."""
    with sync_db() as session:
        old = _seed_two_generations(session)
        selected = {
            a.artifact_id
            for a in find_stale_artifacts(
                session, target_version="1.3.0", created_before="2026-07-06"
            )
        }
    assert selected == {old}
