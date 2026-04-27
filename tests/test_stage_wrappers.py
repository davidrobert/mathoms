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

    def test_import_reconcile_transactions(self):
        from pipeline.stages import reconcile_transactions

        assert callable(reconcile_transactions.run)

    def test_import_categorize_transactions(self):
        from pipeline.stages import categorize_transactions

        assert callable(categorize_transactions.run)

    def test_import_analyze_finances(self):
        from pipeline.stages import analyze_finances

        assert callable(analyze_finances.run)

    def test_import_generate_narratives(self):
        from pipeline.stages import generate_narratives

        assert callable(generate_narratives.run)

    def test_import_unlock_documents(self):
        from pipeline.stages import unlock_documents

        assert callable(unlock_documents.run)

    def test_import_route_documents(self):
        from pipeline.stages import route_documents

        assert callable(route_documents.run)

    def test_import_audit_documents(self):
        from pipeline.stages import audit_documents

        assert callable(audit_documents.run)

    def test_import_extract_members(self):
        from pipeline.stages import extract_members

        assert callable(extract_members.run)

    def test_import_extract_baseline(self):
        from pipeline.stages import extract_baseline

        assert callable(extract_baseline.run)

    def test_import_consolidate_baseline(self):
        from pipeline.stages import consolidate_baseline

        assert callable(consolidate_baseline.run)

    def test_import_extract_statements(self):
        from pipeline.stages import extract_statements

        assert callable(extract_statements.run)

    def test_import_extract_invoices(self):
        from pipeline.stages import extract_invoices

        assert callable(extract_invoices.run)

    def test_import_extract_with_llm(self):
        from pipeline.stages import extract_with_llm

        assert callable(extract_with_llm.run)

    def test_import_e7(self):
        from pipeline.stages import e7

        assert callable(e7.run_crossval)
        assert callable(e7.run_apply)

    def test_import_review_finances(self):
        from pipeline.stages import review_finances

        assert callable(review_finances.run)


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

        # _init_config(_REPO_ROOT) removido em A7.5 — config/ legado não
        # tem mais categorization.json/family_members.json para o teardown.

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

        # A7.5: ``e4_categorize._init_config`` delega leitura ao cache de
        # ``pipeline_common`` (CONFIG_DIR global). Precisa resetar o ``_pc``
        # para ``tmp_path`` antes — pré-A7.5 o ``_REPO_ROOT/config`` legado
        # tinha os JSONs e a chamada implícita "funcionava".
        import scripts.pipeline_common as _pc

        _pc._init_config(tmp_path)

        from scripts.e4_categorize import _init_config

        _init_config(tmp_path)
        from scripts import e4_categorize

        assert e4_categorize._BASE_DIR == tmp_path

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

        # _init_config(_REPO_ROOT) removido em A7.5 (ver fixture cli_stub_root).

    def test_e7_init_config_custom_root(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "scoring.json").write_text("{}")
        (config_dir / "pipeline.json").write_text("{}")

        from scripts.e7_review import _init_config

        _init_config(tmp_path)
        from scripts import e7_review

        assert e7_review.PROJECT_DIR == tmp_path

        # _init_config(_REPO_ROOT) removido em A7.5 (ver fixture cli_stub_root).

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

        # _init_config(_REPO_ROOT) removido em A7.5 (ver fixture cli_stub_root).

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

        # _init_config(_REPO_ROOT) removido em A7.5 (ver fixture cli_stub_root).

    def test_e0_audit_init_config_custom_root(self, tmp_path):
        from scripts.e0_audit import _init_config

        _init_config(tmp_path)
        from scripts import e0_audit

        assert e0_audit.PROJECT_DIR == tmp_path
        assert e0_audit.DATA_DIR == tmp_path / "data"

        # _init_config(_REPO_ROOT) removido em A7.5 (ver fixture cli_stub_root).

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

        # _init_config(_REPO_ROOT) removido em A7.5 (ver fixture cli_stub_root).

    def test_e0_unlock_init_config_custom_root(self, tmp_path):
        from scripts.e0_unlock import _init_config

        _init_config(tmp_path)
        from scripts import e0_unlock

        assert e0_unlock.BASE == tmp_path
        assert e0_unlock.INBOX == tmp_path / "inbox"

        # _init_config(_REPO_ROOT) removido em A7.5 (ver fixture cli_stub_root).

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

        # _init_config(_REPO_ROOT) removido em A7.5 (ver fixture cli_stub_root).

    def test_pipeline_common_init_config_custom_root(self, tmp_path):
        from scripts.pipeline_common import _init_config

        _init_config(tmp_path)
        from scripts import pipeline_common as pc

        assert pc.PROJECT_DIR == tmp_path
        assert pc.CONFIG_DIR == tmp_path / "config"
        assert pc.E5_DIR == tmp_path / "processed" / "E5_analysis"

        # _init_config(_REPO_ROOT) removido em A7.5 (ver fixture cli_stub_root).


class TestContextIntegration:
    """Verifica que WorkspaceContext.default() aponta para o projeto real."""

    def test_default_has_config_files(self):
        """A7.5 (ADR-134): configs cliente migraram para DB; ``config/`` global
        retém apenas assets de produto (pipeline, scoring, schemas, prompts,
        templates, report_layout, etc.). ``family_members``/``categorization``
        passam a vir via ``ConfigStore`` no boundary do worker."""
        ctx = WorkspaceContext.default()
        assert (ctx.config_dir / "pipeline.json").exists()
        assert (ctx.config_dir / "scoring.json").exists()
        assert (ctx.config_dir / "report_layout.yaml").exists()

    def test_default_has_processed_dirs(self):
        ctx = WorkspaceContext.default()
        # `processed/` não é tracked em git — num checkout fresco (CI) o
        # diretório só existe após `ensure_dirs()`. O invariante real do
        # teste é que o factory aponta ao layout correto e `ensure_dirs`
        # materializa-o; existência pré-execução não é garantida.
        assert ctx.e2_dir == ctx.processed_dir / "E2_extracts"
        ctx.ensure_dirs()
        assert ctx.e2_dir.exists()
