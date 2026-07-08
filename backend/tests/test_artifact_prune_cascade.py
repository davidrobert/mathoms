"""Cascade DB-level pré-existente sob a coluna ``retention_until`` (A33.l6,
aceite #3): workspace/run delete cascam artifacts com retention populada;
document delete faz SET NULL sem apagar a row (predicado segue governando);
RESTRICT protege artifact publicado no nível do DB.

O engine da suíte roda com PRAGMA foreign_keys OFF (decisão histórica em
``core/database.py``). Cascade de DDL é validado aqui num engine dedicado
com FK ON — DB real, nunca mock (regra do repo)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from backend.app.models import PipelineArtifact, PipelineRun, PipelineRunStatus, User, Workspace
from backend.app.services.storage.artifact_prune import build_prune_report

_PAST = datetime.now(timezone.utc) - timedelta(days=1)
_FUTURE = datetime.now(timezone.utc) + timedelta(days=30)


@pytest.fixture
def fk_session(tmp_path):
    from sqlalchemy.orm import Session

    engine = sa.create_engine(f"sqlite:///{tmp_path}/fk_cascade.db")

    @sa.event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    from backend.app.core.database import Base

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _artifact(
    s,
    *,
    ws_id: str,
    run_id: str,
    stage: str = "E5",
    key: str = "analise",
    retention_until: datetime | None = None,
    document_id: str | None = None,
) -> int:
    row = PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage=stage,
        artifact_key=key,
        content_json={"payload": "x" * 32},
        retention_until=retention_until,
        document_id=document_id,
    )
    s.add(row)
    s.flush()
    return row.id


def _fk_seed(s) -> tuple[str, str]:
    user = User(email="fk@test.com", hashed_password="x", full_name="U")
    s.add(user)
    s.flush()
    ws = Workspace(name="WS", owner_id=user.id)
    s.add(ws)
    s.flush()
    run = PipelineRun(workspace_id=ws.id, status=PipelineRunStatus.completed)
    s.add(run)
    s.flush()
    return ws.id, run.id


def test_workspace_delete_cascades_artifacts_with_retention_populated(fk_session) -> None:
    s = fk_session
    ws_id, run_id = _fk_seed(s)
    _artifact(s, ws_id=ws_id, run_id=run_id, retention_until=_PAST)
    _artifact(s, ws_id=ws_id, run_id=run_id, key="corrente")
    s.commit()

    s.execute(sa.text("DELETE FROM workspaces WHERE id = :w"), {"w": ws_id})
    s.commit()
    assert s.query(PipelineArtifact).count() == 0, "ON DELETE CASCADE de workspace intacto"


def test_run_delete_cascades_artifacts_with_retention_populated(fk_session) -> None:
    s = fk_session
    ws_id, run_id = _fk_seed(s)
    _artifact(s, ws_id=ws_id, run_id=run_id, retention_until=_FUTURE)
    s.commit()

    s.execute(sa.text("DELETE FROM pipeline_runs WHERE id = :r"), {"r": run_id})
    s.commit()
    assert s.query(PipelineArtifact).count() == 0, "ON DELETE CASCADE de run intacto"


def test_document_delete_sets_null_and_predicate_still_governs(fk_session) -> None:
    from backend.app.models.document import Document

    s = fk_session
    ws_id, run_id = _fk_seed(s)
    doc = Document(workspace_id=ws_id, original_name="extrato.pdf")
    s.add(doc)
    s.flush()
    art_id = _artifact(
        s,
        ws_id=ws_id,
        run_id=run_id,
        stage="E2-extratos",
        key="itau_202601",
        retention_until=None,
        document_id=doc.id,
    )
    s.commit()

    s.execute(sa.text("DELETE FROM documents WHERE id = :d"), {"d": doc.id})
    s.commit()
    row = s.get(PipelineArtifact, art_id)
    assert row is not None, "delete de documento não apaga o artifact (SET NULL)"
    assert row.document_id is None
    # Órfã continua governada pelo predicado: NULL nunca é prunado.
    report = build_prune_report(s, now=datetime.now(timezone.utc))
    assert report.expired_total == 0


def test_restrict_fk_protects_published_artifact_at_db_level(fk_session) -> None:
    """A exclusão de referenciadas no service tem lastro real: RESTRICT do DB
    aborta DELETE de artifact publicado."""
    from backend.app.models.report_publication import ReportPublication

    s = fk_session
    ws_id, run_id = _fk_seed(s)
    art_id = _artifact(s, ws_id=ws_id, run_id=run_id, retention_until=_PAST)
    s.add(
        ReportPublication(
            workspace_id=ws_id,
            period_yyyymm="202606",
            artifact_id=art_id,
            published_at=datetime.now(timezone.utc),
            published_by="ops",
            immutable_hash="h" * 64,
        )
    )
    s.commit()

    with pytest.raises(sa.exc.IntegrityError):
        s.execute(sa.text("DELETE FROM pipeline_artifacts WHERE id = :a"), {"a": art_id})
    s.rollback()
