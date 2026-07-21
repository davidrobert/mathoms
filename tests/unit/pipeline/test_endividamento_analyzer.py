"""Tests — ``EndividamentoAnalyzer`` (Sessão A5b)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.endividamento_analyzer import (  # noqa: E402
    DividaItem,
    EndividamentoAnalysis,
    EndividamentoAnalyzer,
)


def _member(nome: str, total_dividas: float | None = None, dividas: float | None = None) -> dict:
    data: dict = {}
    if total_dividas is not None:
        data["total_dividas"] = total_dividas
    if dividas is not None:
        data["dividas"] = dividas
    return {"nome": nome, "data": data}


class TestAnalyze:
    def test_computes_percentual_sobre_bruto(self):
        r = EndividamentoAnalyzer().analyze(
            {"bruto": 1_000_000, "dividas": 200_000},
            [_member("David", total_dividas=200_000)],
        )
        assert r.percentual_patrimonio == pytest.approx(20.0)

    def test_creates_divida_item_per_member_with_positive_divida(self):
        r = EndividamentoAnalyzer().analyze(
            {"bruto": 1_000_000, "dividas": 300_000},
            [
                _member("David", total_dividas=200_000),
                _member("Mariana", total_dividas=100_000),
            ],
        )
        assert len(r.dividas) == 2
        descs = [d.descricao for d in r.dividas]
        assert "Financiamento imobiliário (David)" in descs
        assert "Financiamento imobiliário (Mariana)" in descs

    def test_skips_member_without_dividas(self):
        r = EndividamentoAnalyzer().analyze(
            {"bruto": 1_000_000, "dividas": 200_000},
            [
                _member("David", total_dividas=200_000),
                _member("Ana", total_dividas=0),
            ],
        )
        assert len(r.dividas) == 1

    def test_fallback_to_dividas_field_when_total_dividas_absent(self):
        r = EndividamentoAnalyzer().analyze(
            {"bruto": 500_000, "dividas": 100_000},
            [_member("David", dividas=100_000)],
        )
        assert len(r.dividas) == 1

    def test_no_members_or_zero_dividas_produces_default_detalhe(self):
        r = EndividamentoAnalyzer().analyze({"bruto": 500_000, "dividas": 0}, [])
        assert r.detalhe == "Sem dívidas identificadas"
        assert r.dividas == ()

    def test_detalhe_joins_descricoes_with_semicolons(self):
        r = EndividamentoAnalyzer().analyze(
            {"bruto": 1_000_000, "dividas": 300_000},
            [_member("David", total_dividas=200_000), _member("Mariana", total_dividas=100_000)],
        )
        assert "; " in r.detalhe
        assert r.detalhe.count("Financiamento imobiliário") == 2

    def test_pct_zero_when_bruto_zero(self):
        r = EndividamentoAnalyzer().analyze(
            {"bruto": 0, "dividas": 100_000},
            [_member("David", total_dividas=100_000)],
        )
        assert r.percentual_patrimonio == 0.0

    def test_skips_non_dict_entries(self):
        r = EndividamentoAnalyzer().analyze(
            {"bruto": 1_000_000, "dividas": 100_000},
            [None, "string", _member("David", total_dividas=100_000)],
        )
        assert len(r.dividas) == 1


class TestResult:
    def test_result_is_frozen_dataclass(self):
        r = EndividamentoAnalyzer().analyze({"bruto": 0, "dividas": 0}, [])
        assert isinstance(r, EndividamentoAnalysis)

    def test_divida_item_to_dict_absent_fields_are_null(self):
        """A37.l4 · DE-07: ausência é null, nunca sentinela "N/D"/0.0."""
        item = DividaItem(descricao="Fin imóvel", saldo_devedor=200_000.123)
        d = item.to_dict()
        assert d["saldo_devedor"] == 200_000.12
        assert d["parcela_mensal"] is None
        assert d["taxa_juros"] is None

    def test_divida_item_to_dict_rounds_known_parcela(self):
        item = DividaItem(
            descricao="Fin imóvel",
            saldo_devedor=200_000.0,
            parcela_mensal=1_234.567,
            taxa_juros=9.5,
        )
        d = item.to_dict()
        assert d["parcela_mensal"] == 1_234.57
        assert d["taxa_juros"] == 9.5

    def test_to_legacy_dict_has_all_fields(self):
        r = EndividamentoAnalyzer().analyze(
            {"bruto": 1_000_000, "dividas": 100_000},
            [_member("David", total_dividas=100_000)],
        )
        d = r.to_legacy_dict()

        assert {"total_dividas", "percentual_patrimonio", "dividas", "detalhe"}.issubset(d.keys())
        assert isinstance(d["dividas"], list)
        assert len(d["dividas"]) == 1
