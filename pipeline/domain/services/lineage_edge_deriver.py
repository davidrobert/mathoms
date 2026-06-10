"""Derivação pura ``_lineage`` E5 → edges do índice reverso (ADR-279 · A25.l3): lê o bloco inline do payload e devolve lista determinística (sorted, dedup) de ``LineageEdge`` para ``artifact_lineage_edge``. Teto honesto do F5 — o ``_lineage`` inline para em E5 (inputs intra-E5; E4/E3 não emitem), então a FOLHA documental é coarse via ``consumed_sources`` (paridade com ``report_lineage``): todo agregado com lineage recebe edge ``source_document`` de toda fonte consumida pelo run (nível run→doc, não atribuição fina doc→campo). Zero SQLAlchemy — persistência é do writer ``backend/app/services/lineage_edge_writer.py``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from pipeline.domain.services.lineage_fields import E5_ANALISE_KEY, E5_STAGE

SOURCE_DOCUMENT_EDGE_TYPE = "source_document"

# Payloads JSON wire-shaped (mesmo padrão de lineage_fields.LineageBlock) — shape
# canônico em config/schemas/e5_analysis.schema.json (`_lineage`).
E5Payload = dict[str, Any]
LineageEntry = dict[str, Any]


@dataclass(frozen=True)
class LineageEdge:
    """Edge ``src → dst``; ``winner=True`` em toda edge derivada (semântica fina K4 member-level é F7)."""

    src_stage: str
    src_key: str
    src_field: str
    dst_stage: str
    dst_key: str
    dst_field: str
    edge_type: str
    rule_ref: str
    source_document_id: str | None
    data_source_id: str | None
    winner: bool


@dataclass(frozen=True)
class ConsumedSource:
    """Fonte coarse consumida pelo run (row E2 em ``pipeline_artifacts``), resolvida pelo writer."""

    stage: str
    artifact_key: str
    document_id: str | None = None
    data_source_id: str | None = None


def derive_lineage_edges(
    payload: E5Payload,
    *,
    consumed_sources: Iterable[ConsumedSource] = (),
    dst_stage: str = E5_STAGE,
    dst_key: str = E5_ANALISE_KEY,
) -> list[LineageEdge]:
    """Edges determinísticas (sorted, dedup) do ``_lineage`` + folha documental coarse."""
    fields = (payload.get("_lineage") or {}).get("fields") or {}
    sources = tuple(consumed_sources)
    edges: set[LineageEdge] = set()
    for field_name, entry in fields.items():
        edges.update(_field_edges(field_name, entry, dst_stage, dst_key))
        edges.update(_source_edges(field_name, sources, dst_stage, dst_key))
    return sorted(edges, key=_edge_sort_key)


def _field_edges(
    field_name: str, entry: LineageEntry, dst_stage: str, dst_key: str
) -> Iterable[LineageEdge]:
    rule_ref = _rule_ref_text(entry.get("rule_ref"))
    edge_type = entry.get("edge_type") or ""
    for ref in entry.get("inputs") or []:
        yield LineageEdge(
            src_stage=ref["stage"],
            src_key=ref["artifact_key"],
            src_field=ref["field"],
            dst_stage=dst_stage,
            dst_key=dst_key,
            dst_field=field_name,
            edge_type=edge_type,
            rule_ref=rule_ref,
            source_document_id=None,
            data_source_id=None,
            winner=True,
        )


def _source_edges(
    field_name: str, sources: tuple[ConsumedSource, ...], dst_stage: str, dst_key: str
) -> Iterable[LineageEdge]:
    """Folha coarse: ``src_field=""`` + ``edge_type="source_document"`` (teto run→doc)."""
    for source in sources:
        yield LineageEdge(
            src_stage=source.stage,
            src_key=source.artifact_key,
            src_field="",
            dst_stage=dst_stage,
            dst_key=dst_key,
            dst_field=field_name,
            edge_type=SOURCE_DOCUMENT_EDGE_TYPE,
            rule_ref="",
            source_document_id=source.document_id,
            data_source_id=source.data_source_id,
            winner=True,
        )


def _rule_ref_text(rule_ref: Any) -> str:
    """Serialização TEXT do ``rule_ref`` dict (``{adr, ref}`` → ``"ADR-NNN module:qualname"``)."""
    if not isinstance(rule_ref, dict):
        return ""
    adr = rule_ref.get("adr") or ""
    ref = rule_ref.get("ref") or ""
    return f"{adr} {ref}".strip()


def _edge_sort_key(edge: LineageEdge) -> tuple[str, ...]:
    return (
        edge.dst_stage,
        edge.dst_key,
        edge.dst_field,
        edge.edge_type,
        edge.src_stage,
        edge.src_key,
        edge.src_field,
        edge.source_document_id or "",
        edge.data_source_id or "",
    )
