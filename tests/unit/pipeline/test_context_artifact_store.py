"""Tests — integração ``WorkspaceContext`` ↔ ``ArtifactStore`` (Fase 1.3).

ADR-212 PR3b: lazy-default ``DiskArtifactStore`` removido. ``get_artifact_store()``
agora raise ``RuntimeError`` se store não foi injetada.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import (  # noqa: E402
    ArtifactStore,
    InMemoryArtifactStore,
)
from pipeline.context import WorkspaceContext  # noqa: E402


class TestGetArtifactStore:
    def test_missing_store_raises_runtime_error(self, tmp_path: Path):
        """ADR-212 PR3b: sem store injetada, get_artifact_store() raise."""
        ctx = WorkspaceContext(root=tmp_path)
        with pytest.raises(RuntimeError, match="artifact_store não foi injetado"):
            ctx.get_artifact_store()

    def test_injected_store_is_respected(self, tmp_path: Path):
        injected = InMemoryArtifactStore()
        ctx = WorkspaceContext(root=tmp_path, artifact_store=injected)
        assert ctx.get_artifact_store() is injected

    def test_for_tenant_accepts_artifact_store(self, tmp_path: Path):
        injected = InMemoryArtifactStore()
        ctx = WorkspaceContext.for_tenant(tmp_path, artifact_store=injected)
        assert ctx.get_artifact_store() is injected

    def test_for_tenant_without_store_raises_on_access(self, tmp_path: Path):
        """ADR-212 PR3b: for_tenant sem artifact_store retorna ctx, mas
        get_artifact_store() raise quando chamado."""
        ctx = WorkspaceContext.for_tenant(tmp_path)
        with pytest.raises(RuntimeError, match="artifact_store não foi injetado"):
            ctx.get_artifact_store()

    def test_returned_store_satisfies_protocol(self, tmp_path: Path):
        injected = InMemoryArtifactStore()
        ctx = WorkspaceContext(root=tmp_path, artifact_store=injected)
        store = ctx.get_artifact_store()
        assert isinstance(store, ArtifactStore)
