"""Tests — integração ``WorkspaceContext`` ↔ ``ArtifactStore`` (Fase 1.3)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import (  # noqa: E402
    ArtifactStore,
    DiskArtifactStore,
    InMemoryArtifactStore,
)
from pipeline.context import WorkspaceContext  # noqa: E402


class TestGetArtifactStore:
    def test_default_is_disk_artifact_store(self, tmp_path: Path):
        ctx = WorkspaceContext(root=tmp_path)
        store = ctx.get_artifact_store()
        assert isinstance(store, DiskArtifactStore)

    def test_default_is_memoized(self, tmp_path: Path):
        ctx = WorkspaceContext(root=tmp_path)
        a = ctx.get_artifact_store()
        b = ctx.get_artifact_store()
        assert a is b

    def test_injected_store_is_respected(self, tmp_path: Path):
        injected = InMemoryArtifactStore()
        ctx = WorkspaceContext(root=tmp_path, artifact_store=injected)
        assert ctx.get_artifact_store() is injected

    def test_for_tenant_accepts_artifact_store(self, tmp_path: Path):
        injected = InMemoryArtifactStore()
        ctx = WorkspaceContext.for_tenant(tmp_path, artifact_store=injected)
        assert ctx.get_artifact_store() is injected

    def test_for_tenant_default_creates_disk_store(self, tmp_path: Path):
        ctx = WorkspaceContext.for_tenant(tmp_path)
        store = ctx.get_artifact_store()
        assert isinstance(store, DiskArtifactStore)

    def test_returned_store_satisfies_protocol(self, tmp_path: Path):
        ctx = WorkspaceContext(root=tmp_path)
        store = ctx.get_artifact_store()
        assert isinstance(store, ArtifactStore)
