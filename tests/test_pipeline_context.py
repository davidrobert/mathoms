#!/usr/bin/env python3
"""Tests for pipeline.context.WorkspaceContext and pipeline.config_loader."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.context import WorkspaceContext
from pipeline import config_loader


class TestWorkspaceContextDefault:
    def test_default_root_is_project(self):
        ctx = WorkspaceContext.default()
        assert ctx.root.exists()
        assert (ctx.root / "CLAUDE.md").exists()

    def test_paths_derived_from_root(self):
        ctx = WorkspaceContext.default()
        assert ctx.config_dir == ctx.root / "config"
        assert ctx.data_dir == ctx.root / "data"
        assert ctx.processed_dir == ctx.root / "processed"
        assert ctx.e2_dir == ctx.root / "processed" / "E2_extracts"
        assert ctx.e3_dir == ctx.root / "processed" / "E3_reconciled"
        assert ctx.e4_dir == ctx.root / "processed" / "E4_unified"
        assert ctx.e5_dir == ctx.root / "processed" / "E5_analysis"
        assert ctx.e7_dir == ctx.root / "processed" / "E7_review"
        assert ctx.output_dir == ctx.root / "output"
        assert ctx.logs_dir == ctx.root / "logs"

    def test_config_dir_exists(self):
        ctx = WorkspaceContext.default()
        assert ctx.config_dir.exists()

    def test_load_config_from_disk(self):
        ctx = WorkspaceContext.default()
        pipeline_cfg = ctx.load_config("pipeline.json")
        assert isinstance(pipeline_cfg, dict)
        assert "llm" in pipeline_cfg

    def test_load_config_nonexistent_returns_empty(self):
        ctx = WorkspaceContext.default()
        result = ctx.load_config("nonexistent_file_xyz.json")
        assert result == {}

    def test_load_config_required_raises(self):
        ctx = WorkspaceContext.default()
        try:
            ctx.load_config("nonexistent_file_xyz.json", required=True)
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass


class TestWorkspaceContextCustomRoot:
    def test_custom_root(self, tmp_path):
        ctx = WorkspaceContext(root=tmp_path)
        assert ctx.root == tmp_path.resolve()
        assert ctx.config_dir == tmp_path.resolve() / "config"
        assert ctx.e2_dir == tmp_path.resolve() / "processed" / "E2_extracts"

    def test_ensure_dirs_creates_structure(self, tmp_path):
        ctx = WorkspaceContext(root=tmp_path)
        ctx.ensure_dirs()
        assert ctx.processed_dir.exists()
        assert ctx.e2_dir.exists()
        assert ctx.e3_dir.exists()
        assert ctx.e4_dir.exists()
        assert ctx.e5_dir.exists()
        assert ctx.output_dir.exists()
        assert ctx.logs_dir.exists()

    def test_config_overrides(self, tmp_path):
        overrides = {
            "pipeline.json": {"llm": {"model": "test-model"}},
            "family_members.json": {"titular": "test_user"},
        }
        ctx = WorkspaceContext(root=tmp_path, config_overrides=overrides)

        pipeline_cfg = ctx.load_config("pipeline.json")
        assert pipeline_cfg["llm"]["model"] == "test-model"

        family_cfg = ctx.load_config("family_members.json")
        assert family_cfg["titular"] == "test_user"

    def test_config_overrides_fallback_to_disk(self, tmp_path):
        """Override parcial: configs não overridden tentam disco."""
        overrides = {"pipeline.json": {"test": True}}
        ctx = WorkspaceContext(root=tmp_path, config_overrides=overrides)

        assert ctx.load_config("pipeline.json") == {"test": True}
        assert ctx.load_config("other.json") == {}

    def test_for_tenant_factory(self, tmp_path):
        config = {"pipeline.json": {"tenant": True}}
        ctx = WorkspaceContext.for_tenant(tmp_path, config)
        assert ctx.root == tmp_path.resolve()
        assert ctx.load_config("pipeline.json") == {"tenant": True}


class TestConfigLoader:
    def test_load_from_ctx(self, tmp_path):
        overrides = {"test.json": {"key": "value"}}
        ctx = WorkspaceContext(root=tmp_path, config_overrides=overrides)
        result = config_loader.load_config("test.json", ctx=ctx)
        assert result == {"key": "value"}

    def test_load_from_config_dir(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "test.json").write_text('{"from_disk": true}')

        result = config_loader.load_config("test.json", config_dir=config_dir)
        assert result == {"from_disk": True}

    def test_load_fallback_to_project(self):
        config_loader.clear_cache()
        result = config_loader.load_config("pipeline.json")
        assert isinstance(result, dict)
        assert "llm" in result

    def test_required_raises(self, tmp_path):
        try:
            config_loader.load_config(
                "nope.json", config_dir=tmp_path, required=True
            )
            assert False, "Should have raised"
        except FileNotFoundError:
            pass

    def test_cache_and_clear(self, tmp_path):
        config_loader.clear_cache()
        config_dir = tmp_path / "cfg"
        config_dir.mkdir()
        cfg_file = config_dir / "cached.json"
        cfg_file.write_text('{"v": 1}')

        r1 = config_loader.load_config("cached.json", config_dir=config_dir)
        assert r1 == {"v": 1}

        cfg_file.write_text('{"v": 2}')
        r2 = config_loader.load_config("cached.json", config_dir=config_dir)
        assert r2 == {"v": 1}, "Should return cached value"

        config_loader.clear_cache()
        r3 = config_loader.load_config("cached.json", config_dir=config_dir)
        assert r3 == {"v": 2}, "After clear, should read fresh"

    def test_read_json(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"a": 1}')
        assert config_loader.read_json(f) == {"a": 1}

    def test_read_json_missing_returns_none(self, tmp_path):
        assert config_loader.read_json(tmp_path / "missing.json") is None

    def test_write_json(self, tmp_path):
        f = tmp_path / "sub" / "out.json"
        assert config_loader.write_json(f, {"b": 2})
        assert f.exists()
        with open(f) as fh:
            assert json.load(fh) == {"b": 2}
