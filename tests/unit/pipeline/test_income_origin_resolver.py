"""Tests — ``IncomeOriginResolver`` (Sessão A3a · Fase 7 foundation).

Cobre paridade com ``get_pj_origin`` / ``get_clt_origin`` (e4_categorize.py:196/207)
e o ``if/elif`` de classificação de origem em ``process_transactions``
(e4_categorize.py:660-679).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.income_origin_resolver import (  # noqa: E402
    IncomeOriginConfig,
    IncomeOriginResolver,
)

# =============================================================================
# Config
# =============================================================================


class TestConfig:
    def test_from_categorization_handles_nested_pj_format(self):
        cat = {"pj_source_mapping": {"receita_pj": {"acme inc": "Acme Inc"}}}
        cfg = IncomeOriginConfig.from_categorization(cat)
        assert cfg.pj_source_mapping == {"acme inc": "Acme Inc"}

    def test_from_categorization_handles_flat_pj_format(self):
        cat = {"pj_source_mapping": {"acme": "Acme"}}
        cfg = IncomeOriginConfig.from_categorization(cat)
        assert cfg.pj_source_mapping == {"acme": "Acme"}

    def test_from_categorization_clt_mapping(self):
        cat = {"clt_source_mapping": {"banco x": "Empregador X"}}
        cfg = IncomeOriginConfig.from_categorization(cat)
        assert cfg.clt_source_mapping == {"banco x": "Empregador X"}

    def test_static_origins_default_includes_known_categories(self):
        cfg = IncomeOriginConfig()
        for cat in (
            "receita_aluguel",
            "receita_investimento",
            "receita_resgate",
            "receita_venda_ativo",
            "receita_restituicao",
            "receita_fgts",
            "outras_receitas",
        ):
            assert cat in cfg.static_origins


# =============================================================================
# resolve_pj / resolve_clt
# =============================================================================


class TestResolvePJ:
    def test_matches_keyword_in_description(self):
        cfg = IncomeOriginConfig(pj_source_mapping={"acme": "Acme Corp"})
        resolver = IncomeOriginResolver(cfg)

        assert resolver.resolve_pj("Pagamento ACME LTDA") == "Acme Corp"

    def test_falls_back_to_default(self):
        resolver = IncomeOriginResolver(IncomeOriginConfig(pj_source_mapping={"acme": "Acme"}))

        assert resolver.resolve_pj("Cliente Desconhecido") == "Outras Receitas PJ"

    def test_normalization_strips_accent_and_case(self):
        cfg = IncomeOriginConfig(pj_source_mapping={"servicos": "Empresa Y"})
        resolver = IncomeOriginResolver(cfg)

        assert resolver.resolve_pj("PRESTAÇÃO DE SERVIÇOS Y") == "Empresa Y"


class TestResolveCLT:
    def test_matches_keyword(self):
        cfg = IncomeOriginConfig(clt_source_mapping={"acme": "Acme CLT"})
        resolver = IncomeOriginResolver(cfg)

        assert resolver.resolve_clt("SALARIO ACME") == "Acme CLT"

    def test_falls_back_to_first_mapping_value_when_no_match(self):
        cfg = IncomeOriginConfig(clt_source_mapping={"a": "Primeira", "b": "Segunda"})
        resolver = IncomeOriginResolver(cfg)

        assert resolver.resolve_clt("Outra coisa") == "Primeira"

    def test_explicit_default_overrides_mapping_fallback(self):
        cfg = IncomeOriginConfig(
            clt_source_mapping={"a": "Primeira"},
            default_clt_origin="Default Explícito",
        )
        resolver = IncomeOriginResolver(cfg)

        assert resolver.resolve_clt("X") == "Default Explícito"

    def test_empty_mapping_returns_generic_label(self):
        resolver = IncomeOriginResolver(IncomeOriginConfig())

        assert resolver.resolve_clt("X") == "Receita CLT"


# =============================================================================
# resolve_for_category — roteador
# =============================================================================


class TestResolveForCategory:
    def test_routes_pj_to_resolve_pj(self):
        cfg = IncomeOriginConfig(pj_source_mapping={"acme": "Acme"})
        resolver = IncomeOriginResolver(cfg)

        assert resolver.resolve_for_category("receita_pj", "ACME LTDA") == "Acme"

    def test_routes_clt_to_resolve_clt(self):
        cfg = IncomeOriginConfig(clt_source_mapping={"x": "Empregador X"})
        resolver = IncomeOriginResolver(cfg)

        assert resolver.resolve_for_category("receita_clt", "SALARIO X") == "Empregador X"

    def test_uses_static_origin_for_aluguel(self):
        resolver = IncomeOriginResolver(IncomeOriginConfig())

        assert resolver.resolve_for_category("receita_aluguel", "any") == "Aluguéis"

    def test_uses_static_origin_for_fgts(self):
        resolver = IncomeOriginResolver(IncomeOriginConfig())

        assert resolver.resolve_for_category("receita_fgts", "any") == "FGTS"

    def test_uses_static_origin_for_outras_receitas(self):
        resolver = IncomeOriginResolver(IncomeOriginConfig())

        assert resolver.resolve_for_category("outras_receitas", "any") == "Outras Receitas"

    def test_unknown_category_falls_back_to_outras_receitas(self):
        resolver = IncomeOriginResolver(IncomeOriginConfig())

        assert resolver.resolve_for_category("categoria_inexistente", "any") == "Outras Receitas"

    def test_known_categories_includes_pj_clt_and_static(self):
        kc = IncomeOriginResolver.known_categories()

        assert "receita_pj" in kc
        assert "receita_clt" in kc
        assert "receita_aluguel" in kc
