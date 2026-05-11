"""Tests — ``compute_custo_essencial_mensal`` (Track T06 · [[ADR-191]] §D4)."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.essential_expense_calculator import (  # noqa: E402
    compute_custo_essencial_mensal,
)

CATEGORIAS_IN = (
    "moradia",
    "alimentacao",
    "transporte",
    "saude",
    "seguros",
    "servicos_domesticos",
    "educacao",
    "suporte_familiar",
    "financiamentos",
)


class TestComputeCustoEssencialMensal:
    def test_lista_completa_soma_todas_categorias_essenciais(self):
        despesas = {
            "moradia": Decimal("3000"),
            "alimentacao": Decimal("1500"),
            "transporte": Decimal("800"),
            "saude": Decimal("400"),
            "seguros": Decimal("200"),
            "servicos_domesticos": Decimal("500"),
            "educacao": Decimal("600"),
            "suporte_familiar": Decimal("300"),
            "financiamentos": Decimal("2200"),
        }
        total = compute_custo_essencial_mensal(despesas, CATEGORIAS_IN)
        assert total == Decimal("9500")

    def test_lista_parcial_soma_apenas_presentes(self):
        # Categorias declaradas mas ausentes em despesas → 0.
        despesas = {"moradia": Decimal("2500"), "alimentacao": Decimal("1200")}
        total = compute_custo_essencial_mensal(despesas, CATEGORIAS_IN)
        assert total == Decimal("3700")

    def test_lista_vazia_retorna_zero(self):
        total = compute_custo_essencial_mensal({}, CATEGORIAS_IN)
        assert total == Decimal("0")

    def test_categorias_in_vazia_ignora_tudo(self):
        despesas = {"moradia": Decimal("3000"), "alimentacao": Decimal("1500")}
        total = compute_custo_essencial_mensal(despesas, ())
        assert total == Decimal("0")

    def test_categorias_nao_declaradas_sao_ignoradas(self):
        # ``lazer_viagens`` está em ``categorias_out`` no scoring.json — ignorar.
        despesas = {
            "moradia": Decimal("3000"),
            "lazer_viagens": Decimal("1500"),
            "assinaturas": Decimal("100"),
        }
        total = compute_custo_essencial_mensal(despesas, CATEGORIAS_IN)
        assert total == Decimal("3000")

    def test_coerce_int_e_string_decimal(self):
        despesas = {
            "moradia": 3000,  # int
            "alimentacao": "1500.50",  # string
            "saude": Decimal("200.25"),
        }
        total = compute_custo_essencial_mensal(despesas, CATEGORIAS_IN)
        assert total == Decimal("4700.75")

    def test_coerce_float_via_str(self):
        # ADR-090: float é coerido via str(v) — sem rounding silencioso.
        despesas = {"moradia": 1234.56}
        total = compute_custo_essencial_mensal(despesas, ("moradia",))
        assert total == Decimal("1234.56")

    def test_none_e_bool_viram_zero(self):
        despesas = {"moradia": None, "alimentacao": True, "saude": Decimal("100")}
        total = compute_custo_essencial_mensal(despesas, CATEGORIAS_IN)
        assert total == Decimal("100")

    def test_string_invalida_vira_zero(self):
        despesas = {"moradia": "n/a", "alimentacao": Decimal("500")}
        total = compute_custo_essencial_mensal(despesas, CATEGORIAS_IN)
        assert total == Decimal("500")

    @pytest.mark.parametrize(
        "categorias",
        [
            ["moradia", "alimentacao"],
            ("moradia", "alimentacao"),
            frozenset({"moradia", "alimentacao"}),
        ],
    )
    def test_aceita_qualquer_iteravel_de_strings(self, categorias):
        despesas = {
            "moradia": Decimal("3000"),
            "alimentacao": Decimal("1500"),
            "saude": Decimal("400"),
        }
        total = compute_custo_essencial_mensal(despesas, categorias)
        assert total == Decimal("4500")
