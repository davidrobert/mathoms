#!/usr/bin/env python3
"""Tests for pipeline stage wrappers — verifica que são importáveis e
que a interface run(ctx) está correta."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.context import WorkspaceContext


class TestStageImports:
    """Verifica que todos os stage wrappers são importáveis."""

    def test_import_e2(self):
        from pipeline.stages import e2
        assert callable(e2.run)

    def test_import_e3(self):
        from pipeline.stages import e3
        assert callable(e3.run)

    def test_import_e4(self):
        from pipeline.stages import e4
        assert callable(e4.run)

    def test_import_e7(self):
        from pipeline.stages import e7
        assert callable(e7.run_crossval)
        assert callable(e7.run_apply)


class TestInitConfig:
    """Verifica que _init_config dos scripts funciona com root_dir custom."""

    def test_e3_init_config_custom_root(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "pipeline.json").write_text('{"reconciliation": {}}')
        (config_dir / "family_members.json").write_text('{}')
        (config_dir / "institutions.json").write_text('{}')

        from scripts.e3_reconcile import _init_config, _BASE_DIR, _DEFAULT_BASE_DIR
        _init_config(tmp_path)
        from scripts import e3_reconcile
        assert e3_reconcile._BASE_DIR == tmp_path

        # Restaurar default para não afetar outros testes
        _init_config(_DEFAULT_BASE_DIR)

    def test_e4_init_config_custom_root(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "categorization.json").write_text(
            '{"expense_keywords":{},"income_keywords":{},'
            '"internal_transfer_patterns":[],"pj_source_mapping":{},'
            '"clt_source_mapping":{}}'
        )
        (config_dir / "family_members.json").write_text('{}')
        (config_dir / "pipeline.json").write_text('{}')

        from scripts.e4_categorize import _init_config, _BASE_DIR, _DEFAULT_BASE_DIR
        _init_config(tmp_path)
        from scripts import e4_categorize
        assert e4_categorize._BASE_DIR == tmp_path

        _init_config(_DEFAULT_BASE_DIR)

    def test_e2_common_init_config_custom_root(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "family_members.json").write_text('{"membros":{}}')
        (config_dir / "localization.json").write_text('{}')
        (config_dir / "institutions.json").write_text('{}')
        (config_dir / "pipeline.json").write_text('{}')

        from scripts.e2.common import _init_config, BASE_DIR, _DEFAULT_BASE_DIR
        _init_config(tmp_path)
        from scripts.e2 import common as e2c
        assert e2c.BASE_DIR == tmp_path
        assert e2c.DATA_DIR == tmp_path / "data" / "financial_statements"

        _init_config(_DEFAULT_BASE_DIR)

    def test_e7_init_config_custom_root(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "scoring.json").write_text('{}')
        (config_dir / "pipeline.json").write_text('{}')

        from scripts.e7_review import _init_config, _DEFAULT_BASE_DIR
        _init_config(tmp_path)
        from scripts import e7_review
        assert e7_review.PROJECT_DIR == tmp_path

        _init_config(_DEFAULT_BASE_DIR)


class TestContextIntegration:
    """Verifica que WorkspaceContext.default() aponta para o projeto real."""

    def test_default_has_config_files(self):
        ctx = WorkspaceContext.default()
        assert (ctx.config_dir / "pipeline.json").exists()
        assert (ctx.config_dir / "family_members.json").exists()
        assert (ctx.config_dir / "categorization.json").exists()

    def test_default_has_processed_dirs(self):
        ctx = WorkspaceContext.default()
        assert ctx.e2_dir.exists()
