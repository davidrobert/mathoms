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
    PARECER_CITATION_DST_STAGE,
    aggregates_depending_on_source_document,
    materialize_lineage_edges,
    materialize_parecer_citation_edges,
    materialize_parecer_citation_from_artifact,
    sources_of_parecer_citation,
)
from pipeline.domain.services.lineage_edge_deriver import LineageEdge

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


# -- A27.l1 slice 3: coexistência de produtores por dst_stage (ADR-293 §Emenda) --


def _parecer_edge(*, dst_field: str = "risco[2]", src_field: str = "classe=Ações") -> LineageEdge:
    return LineageEdge(
        src_stage="E5",
        src_key="analise_financeira",
        src_field=src_field,
        dst_stage=PARECER_CITATION_DST_STAGE,
        dst_key="parecer_planejador",
        dst_field=dst_field,
        edge_type="parecer_citation",
        rule_ref="",
        source_document_id=None,
        data_source_id=None,
        winner=True,
    )


def _materialize_parecer(factory, ws_id: str, run_id: str, edges) -> int:
    with factory() as db:
        return materialize_parecer_citation_edges(
            db, workspace_id=ws_id, run_id=run_id, edges=edges
        )


def _e5_doc_edge_row(ws_id: str, run_id: str, *, edge_type: str) -> ArtifactLineageEdge:
    return ArtifactLineageEdge(
        workspace_id=ws_id,
        run_id=run_id,
        src_stage="E2-extratos",
        src_key="x",
        src_field="",
        dst_stage="E5",
        dst_key="analise_financeira",
        dst_field="patrimonio.liquido",
        edge_type=edge_type,
        rule_ref="",
        source_document_id=None,
        data_source_id=None,
        winner=True,
    )


def test_parecer_dst_stage_matches_stage_name():
    """DRY: a constante do writer casa com o STAGE_NAME real do parecer (sem magic-string solta)."""
    from pipeline.stages.parecer_planejador import STAGE_NAME

    assert PARECER_CITATION_DST_STAGE == STAGE_NAME


def test_producers_coexist_delete_scoped_by_dst_stage(edge_db):
    """E5→doc e parecer_citation coexistem; re-materializar um NUNCA apaga o outro (KR3)."""
    factory, ws_id = edge_db
    run_id = _seed_run(factory, ws_id, with_e2_doc=True)
    _materialize(factory, ws_id, run_id)
    assert _materialize_parecer(factory, ws_id, run_id, [_parecer_edge()]) == 1
    assert len(_edge_rows(factory, ws_id)) == 4
    _materialize(factory, ws_id, run_id)
    _materialize_parecer(factory, ws_id, run_id, [_parecer_edge()])
    rows = _edge_rows(factory, ws_id)
    assert {r.dst_stage for r in rows} == {"E5", PARECER_CITATION_DST_STAGE}
    assert len(rows) == 4


def test_parecer_delete_is_by_dst_stage_not_edge_type(edge_db):
    """DELETE do parecer não toca edge E5→doc com edge_type inédito — prova dst_stage, não allow-list."""
    factory, ws_id = edge_db
    run_id = _seed_run(factory, ws_id)
    with factory() as db:
        db.add(_e5_doc_edge_row(ws_id, run_id, edge_type="edge_type_novo_inedito"))
        db.commit()
    _materialize_parecer(factory, ws_id, run_id, [_parecer_edge()])
    types = {r.edge_type for r in _edge_rows(factory, ws_id)}
    assert "edge_type_novo_inedito" in types and "parecer_citation" in types


def test_parecer_citation_orphan_guard_without_e5(edge_db):
    """Sem E5 no run, o parecer_citation não é materializado (evita citação órfã)."""
    factory, ws_id = edge_db
    run_id = _seed_run(factory, ws_id, with_e5=False)
    assert _materialize_parecer(factory, ws_id, run_id, [_parecer_edge()]) == 0
    assert _edge_rows(factory, ws_id) == []


def test_parecer_citation_empty_edges_preserves_previous(edge_db):
    """Sem citações no run, preserva o parecer_citation do último run bom (espelha E5)."""
    factory, ws_id = edge_db
    run_id = _seed_run(factory, ws_id)
    _materialize_parecer(factory, ws_id, run_id, [_parecer_edge()])
    assert _materialize_parecer(factory, ws_id, run_id, []) == 0
    assert any(r.edge_type == "parecer_citation" for r in _edge_rows(factory, ws_id))


# -- A27.l1 slices 2+4: builder do artefato do parecer + reverse-lineage (ADR-293) --

_E5_TOP_ATIVOS = {
    "investimentos": {
        "top_ativos": [
            {"posicao": 0, "nome": "PETR4", "membro": "Ana", "instituicao": "XP", "valor": 100}
        ]
    }
}


def _e5_artifact_of(ws_id: str, run_id: str, payload: dict) -> PipelineArtifact:
    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="E5",
        artifact_key="analise_financeira",
        content_json=payload,
    )


def _parecer_artifact(ws_id: str, run_id: str, entries: list[dict]) -> PipelineArtifact:
    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage=PARECER_CITATION_DST_STAGE,
        artifact_key="parecer_planejador",
        content_json={"_meta": {"evidencia_verification": entries}},
    )


def _entry(item_type: str, index: int, path: str, outcome: str = "verified") -> dict:
    return {"item_type": item_type, "item_index": index, "path": path, "outcome": outcome}


def _seed_parecer_run(factory, ws_id: str, *, e5_payload: dict, entries: list[dict]) -> str:
    run_id = str(uuid.uuid4())
    with factory() as db:
        db.add(PipelineRun(id=run_id, workspace_id=ws_id, status=PipelineRunStatus.completed))
        db.add(_e5_artifact_of(ws_id, run_id, e5_payload))
        db.add(_parecer_artifact(ws_id, run_id, entries))
        db.commit()
    return run_id


def test_from_artifact_builds_verified_only_scalar_path(edge_db):
    """Slice 2: só entries verified viram edge; path escalar → src = o próprio path."""
    factory, ws_id = edge_db
    entries = [
        _entry("risco", 2, "$.patrimonio.liquido"),
        _entry("risco", 0, "$.x", "missing_path"),
    ]
    run_id = _seed_parecer_run(factory, ws_id, e5_payload=_E5_PAYLOAD, entries=entries)
    with factory() as db:
        assert (
            materialize_parecer_citation_from_artifact(db, workspace_id=ws_id, run_id=run_id) == 1
        )
    rows = _edge_rows(factory, ws_id)
    assert len(rows) == 1
    assert (rows[0].edge_type, rows[0].dst_field, rows[0].src_field) == (
        "parecer_citation",
        "risco[2]",
        "$.patrimonio.liquido",
    )


def test_from_artifact_resolves_natural_key_and_reverse_query(edge_db):
    """Slices 1+2+4: citação de LISTA vira src por chave natural; reverse responde de-onde-veio."""
    factory, ws_id = edge_db
    entries = [_entry("sugestoes_taticas", 1, "$.investimentos.top_ativos[0].valor")]
    run_id = _seed_parecer_run(factory, ws_id, e5_payload=_E5_TOP_ATIVOS, entries=entries)
    with factory() as db:
        materialize_parecer_citation_from_artifact(db, workspace_id=ws_id, run_id=run_id)
        srcs = sources_of_parecer_citation(db, workspace_id=ws_id)
    assert srcs == [
        {
            "parecer_item": "sugestoes_taticas[1]",
            "e5_source": "membro=Ana|instituicao=XP|nome=PETR4|posicao=0",
            "run_id": run_id,
        }
    ]


def test_from_artifact_without_parecer_returns_zero(edge_db):
    """E5 existe mas sem artefato de parecer → nada a materializar."""
    factory, ws_id = edge_db
    run_id = _seed_run(factory, ws_id)
    with factory() as db:
        assert (
            materialize_parecer_citation_from_artifact(db, workspace_id=ws_id, run_id=run_id) == 0
        )


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
