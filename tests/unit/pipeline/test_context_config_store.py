"""Tests — ``WorkspaceContext.config_store`` + ``workspace_id`` (A7.1 · ADR-134)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.adapters.in_memory_config_store import InMemoryConfigStore  # noqa: E402
from pipeline.context import WorkspaceContext  # noqa: E402
from pipeline.ports import ConfigStore  # noqa: E402


class TestConfigStoreInjection:
    def test_default_is_none(self, tmp_path: Path):
        ctx = WorkspaceContext(root=tmp_path)
        assert ctx.config_store is None
        assert ctx.workspace_id is None

    def test_for_tenant_accepts_config_store(self, tmp_path: Path):
        store = InMemoryConfigStore()
        ctx = WorkspaceContext.for_tenant(
            tmp_path, workspace_id="ws-001", config_store=store
        )
        assert ctx.config_store is store
        assert ctx.workspace_id == "ws-001"

    def test_for_tenant_defaults_keep_none(self, tmp_path: Path):
        ctx = WorkspaceContext.for_tenant(tmp_path)
        assert ctx.config_store is None
        assert ctx.workspace_id is None

    def test_injected_store_satisfies_protocol(self, tmp_path: Path):
        store = InMemoryConfigStore()
        ctx = WorkspaceContext.for_tenant(tmp_path, config_store=store)
        assert isinstance(ctx.config_store, ConfigStore)
