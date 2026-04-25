#!/usr/bin/env python3
"""Tests for pipeline stage wrappers — verifica que são importáveis e
que a interface run(ctx) está correta."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.context import WorkspaceContext
from scripts.pipeline_common import _REPO_ROOT


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

    def test_import_e5(self):
        from pipeline.stages import e5

        assert callable(e5.run)

    def test_import_e5n(self):
        from pipeline.stages import e5n

        assert callable(e5n.run)

    def test_import_e0_unlock(self):
        from pipeline.stages import e0_unlock

        assert callable(e0_unlock.run)

    def test_import_e0_route(self):
        from pipeline.stages import e0_route

        assert callable(e0_route.run)

    def test_import_e0_audit(self):
        from pipeline.stages import e0_audit

        assert callable(e0_audit.run)

    def test_import_e1(self):
        from pipeline.stages import e1

        assert callable(e1.run)

    def test_import_e15(self):
        from pipeline.stages import e15

        assert callable(e15.run)

    def test_import_e15c(self):
        from pipeline.stages import e15c

        assert callable(e15c.run)

    def test_import_e2_llm(self):
        from pipeline.stages import e2_llm

        assert callable(e2_llm.run)

    def test_import_e7(self):
        from pipeline.stages import e7

        assert callable(e7.run_crossval)
        assert callable(e7.run_apply)

    def test_import_e7_review_llm(self):
        from pipeline.stages import e7_review_llm

        assert callable(e7_review_llm.run)


class TestInitConfig:
    """Verifica que _init_config dos scripts funciona com root_dir custom."""

    def test_e3_init_config_custom_root(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "pipeline.json").write_text('{"reconciliation": {}}')
        (config_dir / "family_members.json").write_text("{}")
        (config_dir / "institutions.json").write_text("{}")

        from scripts.e3_reconcile import _BASE_DIR, _init_config

        _init_config(tmp_path)
        from scripts import e3_reconcile

        assert e3_reconcile._BASE_DIR == tmp_path

        # Restaurar default para não afetar outros testes
        _init_config(_REPO_ROOT)

    def test_e4_init_config_custom_root(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "categorization.json").write_text(
            '{"expense_keywords":{},"income_keywords":{},'
            '"internal_transfer_patterns":[],"pj_source_mapping":{},'
            '"clt_source_mapping":{}}'
        )
        (config_dir / "family_members.json").write_text("{}")
        (config_dir / "pipeline.json").write_text("{}")

        from scripts.e4_categorize import _BASE_DIR, _init_config

        _init_config(tmp_path)
        from scripts import e4_categorize

        assert e4_categorize._BASE_DIR == tmp_path

        _init_config(_REPO_ROOT)

    def test_e2_common_init_config_custom_root(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "family_members.json").write_text('{"membros":{}}')
        (config_dir / "localization.json").write_text("{}")
        (config_dir / "institutions.json").write_text("{}")
        (config_dir / "pipeline.json").write_text("{}")

        from scripts.e2.common import BASE_DIR, _init_config

        _init_config(tmp_path)
        from scripts.e2 import common as e2c

        assert e2c.BASE_DIR == tmp_path
        assert e2c.DATA_DIR == tmp_path / "data" / "financial_statements"

        _init_config(_REPO_ROOT)

    def test_e7_init_config_custom_root(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "scoring.json").write_text("{}")
        (config_dir / "pipeline.json").write_text("{}")

        from scripts.e7_review import _init_config

        _init_config(tmp_path)
        from scripts import e7_review

        assert e7_review.PROJECT_DIR == tmp_path

        _init_config(_REPO_ROOT)

    def test_e5_init_config_custom_root(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "family_members.json").write_text('{"titular":"test","membros":{}}')
        (config_dir / "goals.json").write_text("{}")
        (config_dir / "scoring.json").write_text("{}")
        (config_dir / "parametros_fiscais.json").write_text("{}")
        (config_dir / "categorization.json").write_text("{}")

        from scripts.e5_analyze import _init_config

        _init_config(tmp_path)
        from scripts import e5_analyze

        assert e5_analyze.PROJECT_DIR == tmp_path
        assert e5_analyze.E5_ANALYSIS_DIR == tmp_path / "processed" / "E5_analysis"

        _init_config(_REPO_ROOT)

    def test_e5n_init_config_custom_root(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "family_members.json").write_text('{"titular":"test","membros":{}}')
        (config_dir / "categorization.json").write_text("{}")

        from scripts.e5n_narrativas import _init_config

        _init_config(tmp_path)
        from scripts import e5n_narrativas

        assert e5n_narrativas.PROJECT_DIR == tmp_path
        assert (
            e5n_narrativas.E5_JSON_PATH
            == tmp_path / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
        )

        _init_config(_REPO_ROOT)

    def test_e0_audit_init_config_custom_root(self, tmp_path):
        from scripts.e0_audit import _init_config

        _init_config(tmp_path)
        from scripts import e0_audit

        assert e0_audit.PROJECT_DIR == tmp_path
        assert e0_audit.DATA_DIR == tmp_path / "data"

        _init_config(_REPO_ROOT)

    def test_e0_route_init_config_custom_root(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "institutions.json").write_text("{}")
        (config_dir / "pipeline.json").write_text("{}")
        (config_dir / "family_members.json").write_text("{}")

        from scripts.e0_route import _init_config

        _init_config(tmp_path)
        from scripts import e0_route

        assert e0_route.BASE == tmp_path
        assert e0_route.INBOX == tmp_path / "inbox"

        _init_config(_REPO_ROOT)

    def test_e0_unlock_init_config_custom_root(self, tmp_path):
        from scripts.e0_unlock import _init_config

        _init_config(tmp_path)
        from scripts import e0_unlock

        assert e0_unlock.BASE == tmp_path
        assert e0_unlock.INBOX == tmp_path / "inbox"

        _init_config(_REPO_ROOT)

    def test_e15c_init_config_custom_root(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "pipeline.json").write_text("{}")
        (config_dir / "family_members.json").write_text("{}")

        from scripts.e15_consolidate import _init_config

        _init_config(tmp_path)
        from scripts import e15_consolidate

        assert e15_consolidate.PROJECT_DIR == tmp_path
        assert e15_consolidate.E2_DIR == tmp_path / "processed" / "E2_extracts"

        _init_config(_REPO_ROOT)

    def test_pipeline_common_init_config_custom_root(self, tmp_path):
        from scripts.pipeline_common import _init_config

        _init_config(tmp_path)
        from scripts import pipeline_common as pc

        assert pc.PROJECT_DIR == tmp_path
        assert pc.CONFIG_DIR == tmp_path / "config"
        assert pc.E5_DIR == tmp_path / "processed" / "E5_analysis"

        _init_config(_REPO_ROOT)


class TestContextIntegration:
    """Verifica que WorkspaceContext.default() aponta para o projeto real."""

    def test_default_has_config_files(self):
        ctx = WorkspaceContext.default()
        assert (ctx.config_dir / "pipeline.json").exists()
        assert (ctx.config_dir / "family_members.json").exists()
        assert (ctx.config_dir / "categorization.json").exists()

    def test_default_has_processed_dirs(self):
        ctx = WorkspaceContext.default()
        # `processed/` não é tracked em git — num checkout fresco (CI) o
        # diretório só existe após `ensure_dirs()`. O invariante real do
        # teste é que o factory aponta ao layout correto e `ensure_dirs`
        # materializa-o; existência pré-execução não é garantida.
        assert ctx.e2_dir == ctx.processed_dir / "E2_extracts"
        ctx.ensure_dirs()
        assert ctx.e2_dir.exists()
