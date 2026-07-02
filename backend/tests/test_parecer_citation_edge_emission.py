"""A27.l1 slices 2+4 (ADR-293) — emissão do edge ``parecer_citation`` + reverse-lineage.

Slice 2: âncoras VERIFICADAS do parecer publicado viram edges E6→E5 com
``src_field`` por chave natural (listas) ou path (escalar). Slice 4: queries
"de onde veio este R$ do parecer?" e documento → itens do parecer (2 hops).
DB real em SQLite file-backed (nunca mock), mesmo padrão de
``test_lineage_edge_writer.py``.
"""

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
    materialize_lineage_edges,
    parecer_citation_sources,
    parecer_items_depending_on_source_document,
)
from backend.app.services.parecer_citation_lineage import build_parecer_citation_edges

_DOC_ID = "22222222-2222-2222-2222-222222222222"

_E5_PAYLOAD = {
    "patrimonio": {"bruto": 100.0, "dividas": 20.0, "liquido": 80.0},
    "investimentos": {
        "top_ativos": [
            {"posicao": 0, "nome": "PETR4", "membro": "Ana", "instituicao": "XP", "valor": 100},
            {"posicao": 1, "nome": "ITSA4", "membro": "Bruno", "instituicao": "Itau", "valor": 90},
        ]
    },
    # Espelha a fixture de test_lineage_edge_writer — 1 field com inputs para o
    # deriver emitir a folha documental (source_document_id) além das intra.
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


def _entries(*specs: tuple[str, int, str | None, str]) -> list[dict]:
    return [
        {"item_type": t, "item_index": i, "path": p, "outcome": o} for (t, i, p, o) in specs
    ]


# ---------------------------------------------------------------------------
# build_parecer_citation_edges (slice 2 — puro)
# ---------------------------------------------------------------------------


def test_scalar_path_becomes_edge_with_path_src_field() -> None:
    edges = build_parecer_citation_edges(
        _E5_PAYLOAD, _entries(("risco", 2, "$.patrimonio.liquido", "verified"))
    )
    assert len(edges) == 1
    edge = edges[0]
    assert edge.src_field == "$.patrimonio.liquido"
    assert edge.dst_field == "risco[2]"
    assert edge.edge_type == "parecer_citation"
    assert edge.dst_stage == PARECER_CITATION_DST_STAGE
    assert edge.src_stage == "E5" and edge.src_key == "analise_financeira"


def test_list_leaf_uses_natural_key_stable_across_reorder() -> None:
    """KR3: reordenado o top_ativos, o MESMO ativo produz o MESMO src_field (fora posicao);
    o endereçamento por índice apontaria para outro ativo."""
    entry = _entries(("sugestoes_taticas", 0, "$.investimentos.top_ativos[0].valor", "verified"))
    edges_run_r = build_parecer_citation_edges(_E5_PAYLOAD, entry)

    reordered = {
        **_E5_PAYLOAD,
        "investimentos": {
            "top_ativos": [
                {"posicao": 0, "nome": "ITSA4", "membro": "Bruno", "instituicao": "Itau", "valor": 95},
                {"posicao": 1, "nome": "PETR4", "membro": "Ana", "instituicao": "XP", "valor": 90},
            ]
        },
    }
    entry_r1 = _entries(
        ("sugestoes_taticas", 0, "$.investimentos.top_ativos[1].valor", "verified")
    )
    edges_run_r1 = build_parecer_citation_edges(reordered, entry_r1)

    key_r = edges_run_r[0].src_field.rsplit("|posicao=", 1)[0]
    key_r1 = edges_run_r1[0].src_field.rsplit("|posicao=", 1)[0]
    assert key_r == key_r1 == "membro=Ana|instituicao=XP|nome=PETR4"


def test_failed_and_pathless_anchors_never_become_edges() -> None:
    edges = build_parecer_citation_edges(
        _E5_PAYLOAD,
        _entries(
            ("risco", 0, "$.patrimonio.liquido", "value_mismatch"),
            ("risco", 1, None, "missing_path"),
            ("risco", 2, "$.patrimonio.liquido", "pairing_mismatch"),
        ),
    )
    assert edges == []


def test_duplicate_anchor_same_item_dedupes() -> None:
    edges = build_parecer_citation_edges(
        _E5_PAYLOAD,
        _entries(
            ("risco", 0, "$.patrimonio.liquido", "verified"),
            ("risco", 0, "$.patrimonio.liquido", "verified"),
        ),
    )
    assert len(edges) == 1


# ---------------------------------------------------------------------------
# Hook pós-run + reverse-lineage (slices 2+4 — DB real)
# ---------------------------------------------------------------------------


def _seed_workspace(factory) -> str:
    with factory() as db:
        user = User(
            id=str(uuid.uuid4()), email="cite@test.com", hashed_password="x", full_name="C"
        )
        db.add(user)
        db.flush()
        ws = Workspace(id=str(uuid.uuid4()), owner_id=user.id, name="Cite WS")
        db.add(ws)
        db.commit()
        return ws.id


@pytest.fixture
def edge_db(tmp_path):
    import backend.app.models  # noqa: F401 — registra todos os models no Base
    from backend.app.core.database import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'citation_edge.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory, _seed_workspace(factory)
    engine.dispose()


def _parecer_artifact(ws_id: str, run_id: str, *, status: str, entries: list[dict]):
    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="E6-parecer",
        artifact_key="parecer_planejador",
        content_json={
            "riscos": [],
            "_meta": {"status": status, "evidencia_verification": entries},
        },
    )


def _seed_run_with_parecer(
    factory, ws_id: str, *, status: str = "Gerado", entries: list[dict] | None = None
) -> str:
    run_id = str(uuid.uuid4())
    default_entries = _entries(
        ("risco", 2, "$.patrimonio.liquido", "verified"),
        ("sugestoes_taticas", 0, "$.investimentos.top_ativos[0].valor", "verified"),
        ("risco", 0, "$.patrimonio.liquido", "value_mismatch"),
    )
    with factory() as db:
        db.add(PipelineRun(id=run_id, workspace_id=ws_id, status=PipelineRunStatus.completed))
        db.add(
            PipelineArtifact(
                workspace_id=ws_id,
                pipeline_run_id=run_id,
                stage="E5",
                artifact_key="analise_financeira",
                content_json=_E5_PAYLOAD,
            )
        )
        db.add(
            PipelineArtifact(
                workspace_id=ws_id,
                pipeline_run_id=run_id,
                stage="E2-extratos",
                artifact_key="itau_extratoconta_202601",
                document_id=_DOC_ID,
                content_json={"transacoes": []},
            )
        )
        db.add(
            _parecer_artifact(
                ws_id, run_id, status=status, entries=entries or default_entries
            )
        )
        db.commit()
    return run_id


def _run_hook(factory, ws_id: str, run_id: str, monkeypatch) -> None:
    import backend.app.tasks.pipeline_task as task_module

    monkeypatch.setattr(task_module, "SyncSessionLocal", factory)
    task_module._materialize_parecer_citation_edges(ws_id, run_id)


def _citation_rows(factory, ws_id: str) -> list[ArtifactLineageEdge]:
    with factory() as db:
        return list(
            db.execute(
                select(ArtifactLineageEdge).where(
                    ArtifactLineageEdge.workspace_id == ws_id,
                    ArtifactLineageEdge.dst_stage == PARECER_CITATION_DST_STAGE,
                )
            ).scalars()
        )


def test_hook_materializes_verified_citations_only(edge_db, monkeypatch) -> None:
    factory, ws_id = edge_db
    run_id = _seed_run_with_parecer(factory, ws_id)

    _run_hook(factory, ws_id, run_id, monkeypatch)

    rows = _citation_rows(factory, ws_id)
    assert {(r.dst_field, r.src_field) for r in rows} == {
        ("risco[2]", "$.patrimonio.liquido"),
        ("sugestoes_taticas[0]", "membro=Ana|instituicao=XP|nome=PETR4|posicao=0"),
    }


def test_hook_skips_needs_review_parecer(edge_db, monkeypatch) -> None:
    factory, ws_id = edge_db
    run_id = _seed_run_with_parecer(factory, ws_id, status="needs_review")

    _run_hook(factory, ws_id, run_id, monkeypatch)

    assert _citation_rows(factory, ws_id) == []


def test_reverse_lineage_answers_document_to_parecer(edge_db, monkeypatch) -> None:
    """Slice 4 (KR3): 'quais itens do parecer dependem do documento X?' via 2 hops."""
    factory, ws_id = edge_db
    run_id = _seed_run_with_parecer(factory, ws_id)
    with factory() as db:
        materialize_lineage_edges(db, workspace_id=ws_id, run_id=run_id)
    _run_hook(factory, ws_id, run_id, monkeypatch)

    with factory() as db:
        items = parecer_items_depending_on_source_document(
            db, workspace_id=ws_id, document_id=_DOC_ID
        )
        sources = parecer_citation_sources(db, workspace_id=ws_id)

    assert {i["item"] for i in items} == {"risco[2]", "sugestoes_taticas[0]"}
    assert {(s["item"], s["e5_source"]) for s in sources} == {
        ("risco[2]", "$.patrimonio.liquido"),
        ("sugestoes_taticas[0]", "membro=Ana|instituicao=XP|nome=PETR4|posicao=0"),
    }


def test_reverse_lineage_unrelated_document_is_empty(edge_db, monkeypatch) -> None:
    factory, ws_id = edge_db
    run_id = _seed_run_with_parecer(factory, ws_id)
    _run_hook(factory, ws_id, run_id, monkeypatch)

    with factory() as db:
        items = parecer_items_depending_on_source_document(
            db, workspace_id=ws_id, document_id=str(uuid.uuid4())
        )
    assert items == []
