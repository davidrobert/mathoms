"""Tests — ``CashFlowBuilder`` (Sessão A4a)."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.cash_flow_builder import (  # noqa: E402
    CashFlowBuilder,
    DespesasUnified,
    FluxoMensal,
    ReceitasUnified,
)
from pipeline.domain.services.transaction_classifier import ClassifiedTransaction  # noqa: E402

# =============================================================================
# Helpers
# =============================================================================


def _receita(data: str, categoria: str, origem: str, valor: float) -> ClassifiedTransaction:
    return ClassifiedTransaction(
        kind="receita",
        data=data,
        descricao="X",
        valor=valor,
        banco="Itaú",
        moeda="BRL",
        tipo_conta="extratoconta",
        titular="david",
        tipo="credito",
        categoria=categoria,
        origem=origem,
    )


def _despesa(data: str, categoria: str, valor: float) -> ClassifiedTransaction:
    return ClassifiedTransaction(
        kind="despesa",
        data=data,
        descricao="X",
        valor=valor,
        banco="Itaú",
        moeda="BRL",
        tipo_conta="extratoconta",
        titular="david",
        tipo="debito",
        categoria=categoria,
    )


_FIXED_NOW = datetime(2026, 4, 19, 10, 0, 0, tzinfo=timezone(timedelta(hours=-3)))


def _builder() -> CashFlowBuilder:
    return CashFlowBuilder(now=_FIXED_NOW)


# =============================================================================
# Receitas
# =============================================================================


class TestReceitas:
    def test_groups_by_category_and_sums(self):
        b = _builder()
        txs = [
            _receita("2026-01-05", "receita_clt", "Empregador", 5000),
            _receita("2026-02-05", "receita_clt", "Empregador", 5500),
            _receita("2026-01-10", "receita_aluguel", "Aluguéis", 2000),
        ]

        out = b.build_receitas_unified(txs)

        assert isinstance(out, ReceitasUnified)
        assert out.total_transacoes == 3
        assert out.total_categorias == 2
        assert set(out.categorias) == {"receita_clt", "receita_aluguel"}
        assert out.totais_por_categoria["receita_clt"] == 10500.0
        assert out.totais_por_categoria["receita_aluguel"] == 2000.0
        assert out.total_geral == 12500.0

    def test_periodo_computed_from_months(self):
        b = _builder()
        txs = [
            _receita("2026-01-05", "receita_clt", "X", 1000),
            _receita("2026-04-20", "receita_clt", "X", 1000),
        ]

        out = b.build_receitas_unified(txs)

        assert out.periodo == "2026-01 a 2026-04"

    def test_empty_receitas_produces_zeroed_output(self):
        b = _builder()

        out = b.build_receitas_unified([])

        assert out.total_geral == 0.0
        assert out.total_transacoes == 0
        assert out.categorias == ()
        assert out.periodo == "N/D"

    def test_to_legacy_dict_includes_consolidation_date(self):
        b = _builder()
        out = b.build_receitas_unified([_receita("2026-01-05", "x", "X", 100)])

        d = out.to_legacy_dict()

        assert d["consolidation_date"] == _FIXED_NOW.isoformat()
        assert d["total_geral"] == 100.0


# =============================================================================
# Despesas
# =============================================================================


class TestDespesas:
    def test_groups_by_category(self):
        b = _builder()
        txs = [
            _despesa("2026-01-05", "mercado", 100),
            _despesa("2026-02-05", "mercado", 150),
            _despesa("2026-01-10", "uber", 30),
        ]

        out = b.build_despesas_unified(txs)

        assert isinstance(out, DespesasUnified)
        assert out.totais_por_categoria["mercado"] == 250.0
        assert out.totais_por_categoria["uber"] == 30.0
        assert out.total_geral == 280.0

    def test_data_sorted_per_category(self):
        b = _builder()
        txs = [
            _despesa("2026-02-05", "mercado", 100),
            _despesa("2026-01-05", "mercado", 150),
        ]

        out = b.build_despesas_unified(txs)

        datas = [tx["data"] for tx in out.dados["mercado"]]
        assert datas == sorted(datas)


# =============================================================================
# Fluxo mensal
# =============================================================================


class TestFluxoMensal:
    def test_groups_by_month_with_origens_and_categorias(self):
        b = _builder()
        receitas = [
            _receita("2026-01-05", "receita_clt", "Empregador A", 5000),
            _receita("2026-02-05", "receita_clt", "Empregador A", 5500),
        ]
        despesas = [
            _despesa("2026-01-05", "mercado", 100),
            _despesa("2026-02-10", "mercado", 200),
            _despesa("2026-02-15", "uber", 50),
        ]

        out = b.build_fluxo_mensal(receitas, despesas)

        assert isinstance(out, FluxoMensal)
        assert out.meses_ordenados == ("2026-01", "2026-02")
        assert "Empregador A" in out.receitas["origens"]
        assert out.receitas["por_mes"]["2026-01"]["Empregador A"] == 5000.0
        assert out.receitas["por_mes"]["2026-02"]["Empregador A"] == 5500.0
        assert out.receitas["por_mes"]["2026-01"]["_total"] == 5000.0

    def test_fills_zero_for_missing_origins_and_categorias(self):
        b = _builder()
        receitas = [
            _receita("2026-01-05", "x", "A", 100),
            _receita("2026-02-05", "x", "B", 200),
        ]

        out = b.build_fluxo_mensal(receitas, [])

        # Origem B não aparece em janeiro; deve ser 0.0.
        assert out.receitas["por_mes"]["2026-01"]["B"] == 0.0
        assert out.receitas["por_mes"]["2026-01"]["A"] == 100.0

    def test_totals_sum_correctly(self):
        b = _builder()
        despesas = [
            _despesa("2026-01-05", "mercado", 100),
            _despesa("2026-01-10", "uber", 30),
        ]

        out = b.build_fluxo_mensal([], despesas)

        assert out.despesas["por_mes"]["2026-01"]["_total"] == 130.0


# =============================================================================
# build() — compõe tudo
# =============================================================================


class TestBuildComposed:
    def test_build_returns_cash_flow_with_all_components(self):
        b = _builder()
        txs = [
            _receita("2026-01-05", "receita_clt", "Emp", 5000),
            _despesa("2026-01-10", "mercado", 100),
            ClassifiedTransaction(
                kind="transferencia",
                data="2026-01-15",
                descricao="PIX",
                valor=500,
                banco="Itaú",
                moeda="BRL",
                tipo_conta="extratoconta",
                titular="david",
                tipo="debito",
            ),
        ]

        cf = b.build(txs)

        assert cf.receitas.total_transacoes == 1
        assert cf.despesas.total_transacoes == 1
        assert cf.transferencias_count == 1
        assert cf.fluxo_mensal.meses_ordenados == ("2026-01",)
