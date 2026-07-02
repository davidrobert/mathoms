"""Writer SQLAlchemy do índice reverso ``artifact_lineage_edge`` (ADR-279 · A25.l3): materializa as edges derivadas do ``_lineage`` E5 com retenção N=1 por workspace (B6) — DELETE workspace-wide + INSERT na MESMA transação (atômico: nunca estado com 0 edges; cobre cross-run E rerun idempotente do mesmo run_id). Run sem E5/sem ``_lineage`` preserva as edges do último run bem-sucedido (return 0 sem deletar). Sessão injetada (espelha ``DBArtifactStore``); a edge table é derivada/rebuildável — auditoria histórica usa o ``_lineage`` inline em ``pipeline_artifacts``."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.models.artifact_lineage_edge import ArtifactLineageEdge
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.services.crypto import read_artifact_content
from backend.app.services.report_lineage import EXTRACTION_STAGES
from pipeline.domain.services.e5_serialization import E5_ARTIFACT_KEY, E5_OUTPUT_STAGE
from pipeline.domain.services.lineage_edge_deriver import (
    ConsumedSource,
    LineageEdge,
    derive_lineage_edges,
)

# ``dst_stage`` do edge parecer_citation (E6→E5) — == ``parecer_planejador.STAGE_NAME``.
# DELETE-por-produtor discrimina por dst_stage (1:1 por produtor, robusto a edge_type novo),
# não por edge_type — que é data-driven/aberto no _lineage (ADR-293 §Emenda).
PARECER_CITATION_DST_STAGE = "review_finances_holistic"

_logger = get_logger("lineage.edge_writer")


def _delete_producer_edges(session: Session, workspace_id: str, dst_stage: str) -> None:
    """Apaga só as edges cujo ``dst`` é o stage deste produtor (ADR-293 §Emenda)."""
    session.execute(
        delete(ArtifactLineageEdge).where(
            ArtifactLineageEdge.workspace_id == workspace_id,
            ArtifactLineageEdge.dst_stage == dst_stage,
        )
    )


def materialize_lineage_edges(session: Session, *, workspace_id: str, run_id: str) -> int:
    """Deriva e persiste as edges E5→doc do run; retorna o nº de edges inseridas."""
    payload = e5_payload_for_run(session, workspace_id, run_id)
    if payload is None:
        return 0
    edges = derive_lineage_edges(payload, consumed_sources=_consumed_sources(session, run_id))
    if not edges:
        return 0
    _delete_producer_edges(session, workspace_id, E5_OUTPUT_STAGE)
    session.add_all(_row(workspace_id, run_id, edge) for edge in edges)
    session.commit()
    _logger.info("lineage edges materializadas", extra={"producer": "e5_doc", "count": len(edges)})
    return len(edges)


def materialize_parecer_citation_edges(
    session: Session, *, workspace_id: str, run_id: str, edges: Sequence[LineageEdge]
) -> int:
    """Persiste as edges de citação do parecer (E6→E5, ADR-293 slice 3). Órfão-guard: só grava
    se houver E5 no run corrente (senão a citação apontaria para E5 de outro run); sem edges
    preserva o último run bom (espelha E5). DELETE-por-produtor não toca edges E5→doc."""
    if e5_payload_for_run(session, workspace_id, run_id) is None:
        return 0
    if not edges:
        return 0
    _delete_producer_edges(session, workspace_id, PARECER_CITATION_DST_STAGE)
    session.add_all(_row(workspace_id, run_id, edge) for edge in edges)
    session.commit()
    _logger.info(
        "lineage edges materializadas", extra={"producer": "parecer_citation", "count": len(edges)}
    )
    return len(edges)


def aggregates_depending_on_source_document(
    session: Session, *, workspace_id: str, document_id: str
) -> list[dict]:
    """Query reversa F5 — "números que dependem da fonte X". Teto honesto run→doc: o ``_lineage`` inline para em E5, então a folha documental é coarse — a resposta é "agregados do run R que dependem dos documentos consumidos por R", não atribuição fina doc→campo."""
    rows = session.execute(_reverse_query_stmt(workspace_id, document_id))
    return [{"dst_stage": r[0], "dst_key": r[1], "dst_field": r[2], "run_id": r[3]} for r in rows]


def parecer_citation_sources(session: Session, *, workspace_id: str) -> list[dict]:
    """Drill N2 do parecer (ADR-293 slice 4) — "de onde veio este R$ do parecer?".

    Mapa item do parecer (``dst_field``, ex. ``risco[2]``) → folha E5 citada
    (``src_field`` = chave natural ou path escalar) + run que a verificou.
    """
    rows = session.execute(
        select(
            ArtifactLineageEdge.dst_field,
            ArtifactLineageEdge.src_field,
            ArtifactLineageEdge.run_id,
        )
        .where(
            ArtifactLineageEdge.workspace_id == workspace_id,
            ArtifactLineageEdge.dst_stage == PARECER_CITATION_DST_STAGE,
        )
        .distinct()
        .order_by(ArtifactLineageEdge.dst_field, ArtifactLineageEdge.src_field)
    )
    return [{"item": r[0], "e5_source": r[1], "run_id": r[2]} for r in rows]


def parecer_items_depending_on_source_document(
    session: Session, *, workspace_id: str, document_id: str
) -> list[dict]:
    """Reverse-lineage cobre o parecer (ADR-293 slice 4): documento → itens do parecer.

    2 hops coarse: as edges E5→doc dão os runs que consumiram o documento; as
    citações ``parecer_citation`` desses runs são os itens do parecer que
    dependem (transitivamente) da fonte. Mesmo teto honesto da query E5 —
    granularidade run→doc, não atribuição fina campo→doc.
    """
    runs_consuming_doc = (
        select(ArtifactLineageEdge.run_id)
        .where(
            ArtifactLineageEdge.workspace_id == workspace_id,
            ArtifactLineageEdge.source_document_id == document_id,
        )
        .distinct()
    )
    rows = session.execute(
        select(
            ArtifactLineageEdge.dst_field,
            ArtifactLineageEdge.src_field,
            ArtifactLineageEdge.run_id,
        )
        .where(
            ArtifactLineageEdge.workspace_id == workspace_id,
            ArtifactLineageEdge.dst_stage == PARECER_CITATION_DST_STAGE,
            ArtifactLineageEdge.run_id.in_(runs_consuming_doc),
        )
        .distinct()
        .order_by(ArtifactLineageEdge.dst_field, ArtifactLineageEdge.src_field)
    )
    return [{"item": r[0], "e5_source": r[1], "run_id": r[2]} for r in rows]


def _reverse_query_stmt(workspace_id: str, document_id: str):
    return (
        select(
            ArtifactLineageEdge.dst_stage,
            ArtifactLineageEdge.dst_key,
            ArtifactLineageEdge.dst_field,
            ArtifactLineageEdge.run_id,
        )
        .where(
            ArtifactLineageEdge.workspace_id == workspace_id,
            ArtifactLineageEdge.source_document_id == document_id,
        )
        .distinct()
        .order_by(
            ArtifactLineageEdge.dst_stage,
            ArtifactLineageEdge.dst_key,
            ArtifactLineageEdge.dst_field,
        )
    )


def e5_payload_for_run(session: Session, workspace_id: str, run_id: str) -> dict | None:
    """Payload E5 do run (decriptado) — consumido pelos hooks de materialização."""
    row = session.execute(
        select(PipelineArtifact.content_json).where(
            PipelineArtifact.workspace_id == workspace_id,
            PipelineArtifact.pipeline_run_id == run_id,
            PipelineArtifact.stage == E5_OUTPUT_STAGE,
            PipelineArtifact.artifact_key == E5_ARTIFACT_KEY,
        )
    ).first()
    if row is None or row[0] is None:
        return None
    return read_artifact_content(row[0])


def _consumed_sources(session: Session, run_id: str) -> tuple[ConsumedSource, ...]:
    """Rows E2 do run (paridade com ``report_lineage.consumed_documents_for_run``)."""
    rows = session.execute(
        select(
            PipelineArtifact.stage,
            PipelineArtifact.artifact_key,
            PipelineArtifact.document_id,
            PipelineArtifact.data_source_id,
        )
        .where(
            PipelineArtifact.pipeline_run_id == run_id,
            PipelineArtifact.stage.in_(EXTRACTION_STAGES),
        )
        .order_by(PipelineArtifact.stage, PipelineArtifact.artifact_key)
    ).all()
    return tuple(
        ConsumedSource(stage=r[0], artifact_key=r[1], document_id=r[2], data_source_id=r[3])
        for r in rows
    )


def _row(workspace_id: str, run_id: str, edge: LineageEdge) -> ArtifactLineageEdge:
    return ArtifactLineageEdge(
        workspace_id=workspace_id,
        run_id=run_id,
        src_stage=edge.src_stage,
        src_key=edge.src_key,
        src_field=edge.src_field,
        dst_stage=edge.dst_stage,
        dst_key=edge.dst_key,
        dst_field=edge.dst_field,
        edge_type=edge.edge_type,
        rule_ref=edge.rule_ref,
        source_document_id=edge.source_document_id,
        data_source_id=edge.data_source_id,
        winner=edge.winner,
    )
