"""Smoke tests para os data migrations da A7.3.

Não roda alembic (chain pré-existente tem dup IDs); importa o módulo direto e
verifica que ``_build_seed_rows`` produz o conteúdo esperado, e que o backfill
``_compute_diff`` retorna ``None`` para iguais e dict para divergências.
"""

from __future__ import annotations

import importlib

seed_module = importlib.import_module(
    "backend.alembic.versions.a5b6c7d8e9f0_seed_category_template_v1"
)
backfill_module = importlib.import_module(
    "backend.alembic.versions.d8e9f0a1b2c3_backfill_workspace_category_overrides"
)


class TestSeedTemplateContent:
    def test_seed_includes_all_expense_categories(self):
        rows = list(seed_module._build_seed_rows(set()))
        keys = [r["key"] for r in rows]
        for expected in (
            "moradia",
            "alimentacao",
            "transporte",
            "saude",
            "lazer_viagens",
        ):
            assert expected in keys

    def test_seed_includes_all_income_categories(self):
        rows = list(seed_module._build_seed_rows(set()))
        keys = [r["key"] for r in rows]
        for expected in (
            "receita_pj",
            "receita_clt",
            "receita_aluguel",
            "receita_investimento",
            "receita_fgts",
        ):
            assert expected in keys

    def test_seed_includes_metadata_row(self):
        rows = list(seed_module._build_seed_rows(set()))
        keys = [r["key"] for r in rows]
        assert seed_module._METADATA_KEY in keys

    def test_metadata_row_carries_aux_blocks(self):
        rows = list(seed_module._build_seed_rows(set()))
        meta = next(r for r in rows if r["key"] == seed_module._METADATA_KEY)
        meta_json = meta["metadata_json"]
        assert "pj_source_mapping" in meta_json
        assert "internal_transfer_patterns" in meta_json
        assert "one_time_income_categories" in meta_json
        assert "qa_investigation_patterns" in meta_json

    def test_seed_skips_existing_keys(self):
        existing = {"moradia", seed_module._METADATA_KEY}
        rows = list(seed_module._build_seed_rows(existing))
        keys = [r["key"] for r in rows]
        assert "moradia" not in keys
        assert seed_module._METADATA_KEY not in keys
        assert "alimentacao" in keys

    def test_all_rows_have_template_version_1(self):
        rows = list(seed_module._build_seed_rows(set()))
        assert all(r["template_version"] == 1 for r in rows)

    def test_expense_rows_have_correct_type(self):
        rows = list(seed_module._build_seed_rows(set()))
        moradia = next(r for r in rows if r["key"] == "moradia")
        assert moradia["category_type"] == "expense"

    def test_income_rows_have_correct_type(self):
        rows = list(seed_module._build_seed_rows(set()))
        receita = next(r for r in rows if r["key"] == "receita_pj")
        assert receita["category_type"] == "income"

    def test_keywords_propagated_correctly(self):
        rows = list(seed_module._build_seed_rows(set()))
        moradia = next(r for r in rows if r["key"] == "moradia")
        assert "ELETROPAULO" in moradia["default_keywords"]


class TestBackfillDiffLogic:
    def test_diff_returns_none_when_identical(self):
        cat = {
            "name": "Moradia",
            "keywords": ["A", "B"],
            "monthly_cap_brl_cents": None,
        }
        tmpl = {
            "label": "Moradia",
            "keywords": ["A", "B"],
            "monthly_cap_brl_cents": None,
        }
        assert backfill_module._compute_diff(cat, tmpl) is None

    def test_diff_detects_label_change(self):
        cat = {
            "name": "Casa",
            "keywords": ["A"],
            "monthly_cap_brl_cents": None,
        }
        tmpl = {
            "label": "Moradia",
            "keywords": ["A"],
            "monthly_cap_brl_cents": None,
        }
        diff = backfill_module._compute_diff(cat, tmpl)
        assert diff["label_override"] == "Casa"
        assert diff["keywords_override"] is None
        assert diff["monthly_cap_brl_cents_override"] is None

    def test_diff_detects_keyword_change(self):
        cat = {
            "name": "Moradia",
            "keywords": ["A", "B", "C"],
            "monthly_cap_brl_cents": None,
        }
        tmpl = {
            "label": "Moradia",
            "keywords": ["A", "B"],
            "monthly_cap_brl_cents": None,
        }
        diff = backfill_module._compute_diff(cat, tmpl)
        assert diff["keywords_override"] == ["A", "B", "C"]
        assert diff["label_override"] is None

    def test_diff_detects_cap_change(self):
        cat = {
            "name": "Moradia",
            "keywords": [],
            "monthly_cap_brl_cents": 300000,
        }
        tmpl = {
            "label": "Moradia",
            "keywords": [],
            "monthly_cap_brl_cents": None,
        }
        diff = backfill_module._compute_diff(cat, tmpl)
        assert diff["monthly_cap_brl_cents_override"] == 300000

    def test_float_to_cents_conversion(self):
        assert backfill_module._float_to_cents(None) is None
        assert backfill_module._float_to_cents(3000.50) == 300050
        assert backfill_module._float_to_cents(1234.56) == 123456


class TestSeedInstitutions:
    def test_module_lists_expected_codes(self):
        seed_inst = importlib.import_module(
            "backend.alembic.versions.b6c7d8e9f0a1_seed_institution_catalog"
        )
        codes = {item["code"] for item in seed_inst._INSTITUTIONS}
        for expected in ("itau", "c6bank", "santander", "binance", "wise"):
            assert expected in codes

    def test_categories_are_assigned(self):
        seed_inst = importlib.import_module(
            "backend.alembic.versions.b6c7d8e9f0a1_seed_institution_catalog"
        )
        binance = next(i for i in seed_inst._INSTITUTIONS if i["code"] == "binance")
        assert binance["category"] == "exchange"
        itau = next(i for i in seed_inst._INSTITUTIONS if i["code"] == "itau")
        assert itau["category"] == "bank"
