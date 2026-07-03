"""Cobertura direta do stage runner E1.5c (`pipeline/stages/consolidate_baseline.py`).

Complementa `test_e15c_golden_execution.py` (que exercita `main_with_store`
direto): aqui o alvo é o **runner do stage** — contrato de saída via `run(ctx)`,
idempotência de re-run e degradação graciosa com input degenerado.
PLATFORM_REVIEW citava cobertura só indireta destes caminhos.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from pipeline.adapters.in_memory_property_identity_resolver import (
    InMemoryPropertyIdentityResolver,
)
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext
from pipeline.stages import consolidate_baseline
from tests.test_e15c_golden_execution import _E5_CONSUMED_KEYS, _canonical_baseline


def _make_ctx(tmp_path: Path, store: InMemoryArtifactStore) -> WorkspaceContext:
    """Contexto mínimo espelhando o golden E1.5c (config vazio, resolver in-memory)."""
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "pipeline.json").write_text("{}")
    (tmp_path / "config" / "family_members.json").write_text("{}")
    return WorkspaceContext(
        root=tmp_path,
        artifact_store=store,
        workspace_id="test-ws-stage",
        property_identity_resolver=InMemoryPropertyIdentityResolver(),
    )


def test_stage_run_produces_e5_contract(tmp_path: Path) -> None:
    """`run(ctx)` sobre baseline E1.5 sintético produz as chaves que o E5 consome."""
    store = InMemoryArtifactStore()
    store.write("E1.5", "baseline_patrimonial", _canonical_baseline())
    result = consolidate_baseline.run(_make_ctx(tmp_path, store))
    assert result["success"] is True
    out = store.read("E1.5c", "baseline_patrimonial")
    for key in _E5_CONSUMED_KEYS:
        assert key in out, f"contrato E5 quebrado no stage runner: falta {key!r}"


def test_stage_run_is_idempotent(tmp_path: Path) -> None:
    """Rodar o stage 2× sobre o mesmo workspace produz artifact idêntico."""
    store = InMemoryArtifactStore()
    store.write("E1.5", "baseline_patrimonial", _canonical_baseline())
    ctx = _make_ctx(tmp_path, store)
    r1 = consolidate_baseline.run(ctx)
    out1 = copy.deepcopy(store.read("E1.5c", "baseline_patrimonial"))
    r2 = consolidate_baseline.run(ctx)
    out2 = store.read("E1.5c", "baseline_patrimonial")
    assert r1 == r2
    assert json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)


def test_stage_run_degenerate_baseline_is_graceful(tmp_path: Path) -> None:
    """Baseline com `itens` vazio (sem membros) não crasha — contadores zerados."""
    store = InMemoryArtifactStore()
    store.write("E1.5", "baseline_patrimonial", {"itens": [], "resumo": {}})
    ctx = WorkspaceContext(root=tmp_path, artifact_store=store)
    (tmp_path / "config").mkdir(exist_ok=True)
    result = consolidate_baseline.run(ctx)
    assert result["success"] is True
    assert (result["imoveis"], result["investimentos"], result["dividas"]) == (0, 0, 0)
    out = store.read("E1.5c", "baseline_patrimonial")
    assert out["imoveis_consolidados"] == []
    assert out["dividas"] == []


def test_stage_run_skips_when_baseline_absent(tmp_path: Path) -> None:
    """Sem artifact E1.5 (free tier) → skip gracioso, nada escrito no store."""
    store = InMemoryArtifactStore()
    ctx = WorkspaceContext(root=tmp_path, artifact_store=store)
    (tmp_path / "config").mkdir(exist_ok=True)
    result = consolidate_baseline.run(ctx)
    assert result["success"] is True
    assert result["skipped"] is True
    assert store.read("E1.5c", "baseline_patrimonial") is None
