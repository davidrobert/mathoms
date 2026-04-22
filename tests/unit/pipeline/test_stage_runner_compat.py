"""Tests — ``pipeline.stage_runner_compat`` (Fase 3)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import DiskArtifactStore, InMemoryArtifactStore  # noqa: E402
from pipeline.context import WorkspaceContext  # noqa: E402
from pipeline.stage_runner_compat import run_legacy_with_bridge_if_db  # noqa: E402


class TestDiskPathSkipsBridge:
    def test_runs_against_ctx_root(self, tmp_path: Path):
        ctx = WorkspaceContext(root=tmp_path)
        # DiskArtifactStore é o default — nenhum bridge deve ser invocado.
        captured: list[Path] = []

        def runner(root: Path) -> None:
            captured.append(root)
            # Simula um script que escreve um arquivo no layout de disco.
            out_dir = root / "processed" / "E3_reconciled"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "k-3_reconciled.json").write_text('{"ok": 1}')

        result = run_legacy_with_bridge_if_db(ctx, stage="E3", legacy_runner=runner)
        assert result["success"] is True
        assert captured == [ctx.root]


class TestDBBackedUsesBridge:
    def test_hydrates_reads_and_persists_writes(self, tmp_path: Path):
        store = InMemoryArtifactStore()
        store.seed("E2-extratos", "itau_202601", {"tx": [{"v": 1}]})
        ctx = WorkspaceContext(
            root=tmp_path,
            artifact_store=store,
            pipeline_run_id="run-xyz",
        )
        captured: list[Path] = []

        def runner(root: Path) -> None:
            captured.append(root)
            # Verifica que o input foi hidratado
            hidrated = root / "processed" / "E2_extracts" / "itau_202601-2_extract.json"
            assert hidrated.exists()
            assert json.loads(hidrated.read_text()) == {"tx": [{"v": 1}]}
            # Simula saída E3
            out_dir = root / "processed" / "E3_reconciled"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "itau_BRL-3_reconciled.json").write_text('{"net": 42}')

        result = run_legacy_with_bridge_if_db(ctx, stage="E3", legacy_runner=runner)
        assert result["success"] is True
        assert result["bridge_persisted"] == 1
        assert len(captured) == 1
        # tmp dir não é ctx.root
        assert captured[0] != ctx.root
        # Store recebeu o output
        assert store.read("E3", "itau_BRL") == {"net": 42}

    def test_raises_if_no_pipeline_run_id(self, tmp_path: Path):
        store = InMemoryArtifactStore()
        ctx = WorkspaceContext(root=tmp_path, artifact_store=store)
        with pytest.raises(RuntimeError, match="pipeline_run_id"):
            run_legacy_with_bridge_if_db(ctx, stage="E3", legacy_runner=lambda _r: None)


class TestCollectCallback:
    def test_collect_invoked_on_disk_path(self, tmp_path: Path):
        ctx = WorkspaceContext(root=tmp_path)
        seen: list[Path] = []

        def runner(root: Path) -> None:
            pass

        def collect(root: Path) -> dict:
            seen.append(root)
            return {"files_created": ["a", "b"]}

        result = run_legacy_with_bridge_if_db(
            ctx, stage="E3", legacy_runner=runner, collect=collect
        )
        assert seen == [ctx.root]
        assert result["files_created"] == ["a", "b"]
