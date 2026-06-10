"""Deriver puro de edges do índice reverso (ADR-279 · A25.l3) sobre o golden dogfood: edges determinísticas (sorted, dedup, 2 derivações idênticas), topologia espelha os ``inputs[]`` do ``_lineage`` inline, folha documental coarse via ``ConsumedSource`` (teto run→doc — todo agregado depende de toda fonte consumida; atribuição fina doc→campo não existe enquanto E4/E3 não emitem ``_lineage``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.domain.services.lineage_edge_deriver import (
    SOURCE_DOCUMENT_EDGE_TYPE,
    ConsumedSource,
    derive_lineage_edges,
)
from tests.pipeline_golden_substrate import load_fixture, run_dogfood_pipeline, write_e5_config

_REPO = Path(__file__).resolve().parents[1]
_DOGFOOD = _REPO / "tests" / "fixtures" / "pipeline_golden" / "dogfood"

_SOURCES = (
    ConsumedSource("E2-extratos", "fict_a", document_id="doc-a", data_source_id="ds-1"),
    ConsumedSource("E2-extratos", "fict_b", document_id="doc-b", data_source_id="ds-1"),
)


def _run_dogfood(root: Path) -> dict:
    write_e5_config(root)
    return run_dogfood_pipeline(
        root,
        raw_baseline=load_fixture(_DOGFOOD / "baseline-1.5.json"),
        e2_extracts={
            "fict_a": load_fixture(_DOGFOOD / "extrato-a-2_extract.json"),
            "fict_b": load_fixture(_DOGFOOD / "extrato-b-2_extract.json"),
        },
    )


@pytest.fixture(scope="module")
def e5_payload(tmp_path_factory) -> dict:
    return _run_dogfood(tmp_path_factory.mktemp("edge_deriver_dogfood"))


def test_derivation_is_deterministic_and_sorted(e5_payload: dict):
    first = derive_lineage_edges(e5_payload, consumed_sources=_SOURCES)
    second = derive_lineage_edges(e5_payload, consumed_sources=_SOURCES)
    assert first == second
    assert first, "golden dogfood sem edges derivadas"
    keys = [(e.dst_field, e.edge_type, e.src_stage, e.src_key, e.src_field) for e in first]
    assert keys == sorted(keys)
    assert len(first) == len(set(first)), "dedup furou"


def test_field_edges_mirror_lineage_inputs(e5_payload: dict):
    """Topologia: 1 edge por input de cada field do bloco inline, src intra-E5."""
    edges = derive_lineage_edges(e5_payload)
    fields = e5_payload["_lineage"]["fields"]
    assert {e.dst_field for e in edges} == set(fields)
    for name, entry in fields.items():
        derived = {e.src_field for e in edges if e.dst_field == name}
        assert derived == {i["field"] for i in entry["inputs"]}
    assert all(e.src_stage == "E5" and e.source_document_id is None for e in edges)
    assert all(e.winner for e in edges)


def test_rule_ref_serialized_as_text(e5_payload: dict):
    edges = derive_lineage_edges(e5_payload)
    liquido = [e for e in edges if e.dst_field == "patrimonio.liquido"]
    assert liquido and all(e.rule_ref.startswith("ADR-") and " " in e.rule_ref for e in liquido)


def test_source_document_leaf_edges_cover_every_aggregate(e5_payload: dict):
    """Teto run→doc: toda fonte consumida vira folha de TODO agregado com lineage."""
    edges = derive_lineage_edges(e5_payload, consumed_sources=_SOURCES)
    leafs = [e for e in edges if e.edge_type == SOURCE_DOCUMENT_EDGE_TYPE]
    fields = set(e5_payload["_lineage"]["fields"])
    assert len(leafs) == len(_SOURCES) * len(fields)
    for source in _SOURCES:
        covered = {e.dst_field for e in leafs if e.source_document_id == source.document_id}
        assert covered == fields
    assert all(e.src_field == "" and e.rule_ref == "" for e in leafs)


def test_payload_without_lineage_block_yields_no_edges():
    assert derive_lineage_edges({"patrimonio": {"bruto": 1.0}}, consumed_sources=_SOURCES) == []
