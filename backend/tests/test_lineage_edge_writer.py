"""Writer do índice reverso ``artifact_lineage_edge`` (ADR-279 · A25.l3): derivação a partir do E5 persistido, retenção N=1 (B6 — 2 runs → só edges do run 2; run sem E5 preserva anteriores; rerun idempotente), query reversa por ``source_document_id`` (teto run→doc — agregados do run R que dependem dos documentos consumidos por R, não atribuição fina doc→campo) e hook best-effort em ``_run_post_processing``. DB real em arquivo SQLite (nunca mock), mesmo padrão file-backed de ``test_pipeline_task.py``."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.models.artifact_lineage_edge import ArtifactLineageEdge
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services.lineage_edge_writer import (
    aggregates_depending_on_source_document,
    materialize_lineage_edges,
)

_E5_PAYLOAD = {
    "patrimonio": {"bruto": 100.0, "dividas": 20.0, "liquido": 80.0},
    "_lineage": {
        "lineage_version": "1.0",
        "fields": {
            "patrimonio.liquido": {
                "value": "80.00",
                "label": "Patrimônio líquido",
                "transform": "bruto − dividas",
                "rule_ref": {"adr": "ADR-145", "ref": "x:PatrimonioCalculator.calculate"},
                "edge_type": "formula",
                "member_hashes": [],
                "inputs": [
                    {
                        "stage": "E5",
                        "artifact_key": "analise_financeira",
                        "field": "patrimonio.bruto",
                    },
                    {
                        "stage": "E5",
                        "artifact_key": "analise_financeira",
                        "field": "patrimonio.dividas",
                    },
                ],
            },
        },
    },
}
_DOC_ID = "11111111-1111-1111-1111-111111111111"


def _seed_workspace(factory) -> str:
    with factory() as db:
        user = User(
            id=str(uuid.uuid4()), email="edge@test.com", hashed_password="x", full_name="Edge"
        )
        db.add(user)
        db.flush()
        ws = Workspace(id=str(uuid.uuid4()), owner_id=user.id, name="Edge WS")
        db.add(ws)
        db.commit()
        return ws.id


@pytest.fixture
def edge_db(tmp_path):
    """Engine sync file-backed + schema completo via ``Base.metadata.create_all``."""
    import backend.app.models  # noqa: F401 — registra todos os models no Base
    from backend.app.core.database import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'lineage_edge.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory, _seed_workspace(factory)
    engine.dispose()


def _e5_artifact(ws_id: str, run_id: str) -> PipelineArtifact:
    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="E5",
        artifact_key="analise_financeira",
        content_json=_E5_PAYLOAD,
    )


def _e2_artifact_with_doc(ws_id: str, run_id: str) -> PipelineArtifact:
    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="E2-extratos",
        artifact_key="itau_extratoconta_202601",
        document_id=_DOC_ID,
        data_source_id="ds-1",
        content_json={"transacoes": []},
    )


def _seed_run(factory, ws_id: str, *, with_e5: bool = True, with_e2_doc: bool = False) -> str:
    run_id = str(uuid.uuid4())
    with factory() as db:
        db.add(PipelineRun(id=run_id, workspace_id=ws_id, status=PipelineRunStatus.completed))
        if with_e5:
            db.add(_e5_artifact(ws_id, run_id))
        if with_e2_doc:
            db.add(_e2_artifact_with_doc(ws_id, run_id))
        db.commit()
    return run_id


def _edge_rows(factory, ws_id: str) -> list[ArtifactLineageEdge]:
    with factory() as db:
        return list(
            db.execute(
                select(ArtifactLineageEdge)
                .where(ArtifactLineageEdge.workspace_id == ws_id)
                .order_by(ArtifactLineageEdge.id)
            ).scalars()
        )


def test_materialize_derives_edges_from_persisted_e5(edge_db):
    factory, ws_id = edge_db
    run_id = _seed_run(factory, ws_id, with_e2_doc=True)
    with factory() as db:
        count = materialize_lineage_edges(db, workspace_id=ws_id, run_id=run_id)
    rows = _edge_rows(factory, ws_id)
    # 2 inputs intra-E5 + 1 folha source_document (1 doc × 1 field com lineage)
    assert count == len(rows) == 3
    assert {r.run_id for r in rows} == {run_id}
    leaf = [r for r in rows if r.edge_type == "source_document"]
    assert len(leaf) == 1
    assert leaf[0].source_document_id == _DOC_ID
    assert leaf[0].data_source_id == "ds-1"
    assert leaf[0].src_field == ""
    intra = [r for r in rows if r.edge_type == "formula"]
    assert {r.src_field for r in intra} == {"patrimonio.bruto", "patrimonio.dividas"}
    assert all(r.rule_ref == "ADR-145 x:PatrimonioCalculator.calculate" for r in intra)
    assert all(r.winner for r in rows)


def _materialize(factory, ws_id: str, run_id: str) -> int:
    with factory() as db:
        return materialize_lineage_edges(db, workspace_id=ws_id, run_id=run_id)


def test_edge_retention_n1(edge_db):
    """B6: 2 runs materializados → só edges do run 2 permanecem."""
    factory, ws_id = edge_db
    run1 = _seed_run(factory, ws_id)
    run2 = _seed_run(factory, ws_id, with_e2_doc=True)
    _materialize(factory, ws_id, run1)
    _materialize(factory, ws_id, run2)
    assert {r.run_id for r in _edge_rows(factory, ws_id)} == {run2}


def test_run_without_e5_preserves_previous_edges(edge_db):
    """Run falho não roda o hook; run sem E5 retorna 0 sem deletar — nunca 0 edges."""
    factory, ws_id = edge_db
    run1 = _seed_run(factory, ws_id)
    _materialize(factory, ws_id, run1)
    run2 = _seed_run(factory, ws_id, with_e5=False)
    assert _materialize(factory, ws_id, run2) == 0
    assert {r.run_id for r in _edge_rows(factory, ws_id)} == {run1}


def test_rerun_same_run_id_is_idempotent(edge_db):
    factory, ws_id = edge_db
    run_id = _seed_run(factory, ws_id, with_e2_doc=True)
    first = _materialize(factory, ws_id, run_id)
    second = _materialize(factory, ws_id, run_id)
    assert first == second == len(_edge_rows(factory, ws_id))


def test_reverse_query_by_source_document(edge_db):
    """F5: "números que dependem da fonte X" — teto run→doc (folha coarse)."""
    factory, ws_id = edge_db
    run_id = _seed_run(factory, ws_id, with_e2_doc=True)
    _materialize(factory, ws_id, run_id)
    with factory() as db:
        aggregates = aggregates_depending_on_source_document(
            db, workspace_id=ws_id, document_id=_DOC_ID
        )
    assert aggregates == [
        {
            "dst_stage": "E5",
            "dst_key": "analise_financeira",
            "dst_field": "patrimonio.liquido",
            "run_id": run_id,
        }
    ]


def test_reverse_query_unknown_document_is_empty(edge_db):
    factory, ws_id = edge_db
    _materialize(factory, ws_id, _seed_run(factory, ws_id, with_e2_doc=True))
    with factory() as db:
        assert (
            aggregates_depending_on_source_document(
                db, workspace_id=ws_id, document_id=str(uuid.uuid4())
            )
            == []
        )


def test_hook_in_run_post_processing_materializes_edges(edge_db, tmp_path, monkeypatch):
    """Hook ADR-279 ligado em ``_run_post_processing`` (best-effort, pós-sucesso)."""
    import backend.app.tasks.pipeline_task as task_module

    factory, ws_id = edge_db
    monkeypatch.setattr(task_module, "SyncSessionLocal", factory)
    run_id = _seed_run(factory, ws_id, with_e2_doc=True)

    task_module._run_post_processing(ws_id, run_id, tmp_path)

    assert {r.run_id for r in _edge_rows(factory, ws_id)} == {run_id}


def test_hook_is_best_effort_when_writer_raises(edge_db, tmp_path, monkeypatch, caplog):
    """Falha do writer vira warning — nunca aborta o pós-processamento do run."""
    import backend.app.tasks.pipeline_task as task_module

    factory, ws_id = edge_db
    monkeypatch.setattr(task_module, "SyncSessionLocal", factory)
    run_id = _seed_run(factory, ws_id)

    def _boom(ws: str, run: str) -> None:
        raise RuntimeError("edge writer exploded")

    monkeypatch.setattr(task_module, "_materialize_lineage_edges", _boom)
    with caplog.at_level("WARNING", logger="pipeline_task.post"):
        task_module._run_post_processing(ws_id, run_id, tmp_path)

    assert any("materialize lineage edges" in m for m in caplog.messages)
    assert _edge_rows(factory, ws_id) == []
