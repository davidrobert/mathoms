"""Testes unitários do mapper DTO do agregado Category.

Cobrem:

- ``category_to_response`` mapeia ORM → DTO e preserva ordem de keywords
  (definida por ``order_by=CategoryKeyword.id`` na relationship).
- ``convert_global_defaults_to_responses`` converte
  ``config/categorization.json`` em lista de DTOs com ``name`` derivado de
  ``code.replace("_", " ").title()`` e ``order`` sequencial (expense primeiro,
  depois income) — paridade com o helper legado
  ``_convert_categorization_json_to_schemas``.
- ``count_defaults`` soma ``expense_keywords`` + ``income_keywords``.
- Mapper funciona sem ``AsyncSession`` (pré-condição: keywords eager-loaded
  pelo caller).
"""

from __future__ import annotations

from types import SimpleNamespace

from backend.app.schemas.dto.category.mapper import (
    category_to_response,
    convert_global_defaults_to_responses,
    count_defaults,
)


def _fake_keyword(keyword: str) -> SimpleNamespace:
    return SimpleNamespace(keyword=keyword)


def _fake_category(**overrides) -> SimpleNamespace:
    defaults = dict(
        id="cat-1",
        code="moradia",
        name="Moradia",
        category_type="expense",
        monthly_cap=None,
        order=0,
        keywords=[],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestCategoryToResponse:
    def test_minimal_category_without_keywords(self):
        cat = _fake_category()

        resp = category_to_response(cat)

        assert resp.id == "cat-1"
        assert resp.code == "moradia"
        assert resp.name == "Moradia"
        assert resp.category_type == "expense"
        assert resp.monthly_cap is None
        assert resp.order == 0
        assert resp.keywords == []

    def test_keywords_are_preserved_in_given_order(self):
        # A relationship ordena por CategoryKeyword.id — mapper confia na
        # ordem já dada pelo ORM e NÃO reordena.
        cat = _fake_category(
            keywords=[
                _fake_keyword("aluguel"),
                _fake_keyword("iptu"),
                _fake_keyword("condominio"),
            ]
        )

        resp = category_to_response(cat)

        assert resp.keywords == ["aluguel", "iptu", "condominio"]

    def test_monthly_cap_and_order_mapped(self):
        cat = _fake_category(monthly_cap=3500.0, order=7)

        resp = category_to_response(cat)

        assert resp.monthly_cap == 3500.0
        assert resp.order == 7

    def test_income_category(self):
        cat = _fake_category(code="receita_pj", category_type="income")

        resp = category_to_response(cat)

        assert resp.category_type == "income"
        assert resp.code == "receita_pj"

    def test_none_keywords_attribute_treated_as_empty(self):
        """SQLAlchemy pode entregar None antes de hidratar a relationship;
        mapper não deve quebrar."""
        cat = _fake_category(keywords=None)

        resp = category_to_response(cat)

        assert resp.keywords == []


class TestConvertGlobalDefaultsToResponses:
    """Paridade com o helper legado ``_convert_categorization_json_to_schemas``
    (removido em A6e.3)."""

    def test_empty_config_returns_empty_list(self):
        assert convert_global_defaults_to_responses({}) == []
        assert (
            convert_global_defaults_to_responses({"expense_keywords": {}, "income_keywords": {}})
            == []
        )

    def test_only_expense_keywords(self):
        cfg = {
            "expense_keywords": {
                "moradia": ["aluguel", "iptu"],
                "transporte": ["uber"],
            }
        }

        responses = convert_global_defaults_to_responses(cfg)

        assert [r.code for r in responses] == ["moradia", "transporte"]
        assert all(r.category_type == "expense" for r in responses)
        assert [r.order for r in responses] == [0, 1]

    def test_expense_precedes_income_in_order_sequence(self):
        cfg = {
            "expense_keywords": {"moradia": [], "transporte": []},
            "income_keywords": {"receita_pj": [], "aluguel_recebido": []},
        }

        responses = convert_global_defaults_to_responses(cfg)

        assert [r.code for r in responses] == [
            "moradia",
            "transporte",
            "receita_pj",
            "aluguel_recebido",
        ]
        assert [r.category_type for r in responses] == [
            "expense",
            "expense",
            "income",
            "income",
        ]
        assert [r.order for r in responses] == [0, 1, 2, 3]

    def test_name_derivation_from_code(self):
        cfg = {
            "expense_keywords": {
                "moradia": [],
                "lazer_e_cultura": [],
            },
            "income_keywords": {
                "receita_pj": [],
            },
        }

        responses = convert_global_defaults_to_responses(cfg)

        names = {r.code: r.name for r in responses}
        assert names == {
            "moradia": "Moradia",
            "lazer_e_cultura": "Lazer E Cultura",
            "receita_pj": "Receita Pj",
        }

    def test_keywords_preserved_as_list(self):
        cfg = {
            "expense_keywords": {
                "moradia": ["aluguel", "iptu", "condominio"],
            }
        }

        responses = convert_global_defaults_to_responses(cfg)

        assert responses[0].keywords == ["aluguel", "iptu", "condominio"]

    def test_null_keyword_list_treated_as_empty(self):
        """YAML/JSON loaders podem devolver ``None`` para blocos vazios."""
        cfg = {
            "expense_keywords": {"moradia": None},
            "income_keywords": None,
        }

        responses = convert_global_defaults_to_responses(cfg)

        assert len(responses) == 1
        assert responses[0].keywords == []

    def test_categories_default_have_no_id_or_monthly_cap(self):
        cfg = {"expense_keywords": {"moradia": ["aluguel"]}}

        responses = convert_global_defaults_to_responses(cfg)

        assert responses[0].id is None
        assert responses[0].monthly_cap is None


class TestCountDefaults:
    def test_empty(self):
        assert count_defaults({}) == 0
        assert count_defaults({"expense_keywords": {}, "income_keywords": {}}) == 0

    def test_sum_of_sections(self):
        cfg = {
            "expense_keywords": {"a": [], "b": [], "c": []},
            "income_keywords": {"d": [], "e": []},
        }

        assert count_defaults(cfg) == 5

    def test_missing_sections_treated_as_zero(self):
        assert count_defaults({"expense_keywords": {"a": []}}) == 1
        assert count_defaults({"income_keywords": {"a": []}}) == 1

    def test_null_section_treated_as_zero(self):
        cfg = {"expense_keywords": None, "income_keywords": {"a": []}}

        assert count_defaults(cfg) == 1
