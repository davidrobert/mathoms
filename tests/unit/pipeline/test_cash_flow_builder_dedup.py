"""Tests — dedup cross-document em ``CashFlowBuilder.build`` (ADR-255 Camada A)."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.cash_flow_builder import CashFlowBuilder  # noqa: E402
from pipeline.domain.services.transaction_classifier import ClassifiedTransaction  # noqa: E402

_FIXED_NOW = datetime(2026, 5, 22, 10, 0, 0, tzinfo=timezone(timedelta(hours=-3)))


def _builder() -> CashFlowBuilder:
    return CashFlowBuilder(now=_FIXED_NOW)


_DEFAULT_RECEITA: dict = dict(
    data="2026-03-30",
    descricao="Pix recebido de ARVO SAUDE LTDA",
    valor=47208.77,
    banco="C6Bank",
    titular="david",
    tipo_conta="extratoconta",
    categoria="receita_pj",
    origem="Arvo (David - PJ)",
)

_DEFAULT_DESPESA: dict = dict(
    data="2026-03-15",
    descricao="compra",
    valor=100.0,
    banco="Itau",
    titular="david",
    tipo_conta="extratoconta",
    categoria="mercado",
)


def _receita(**overrides) -> ClassifiedTransaction:
    return ClassifiedTransaction(
        kind="receita",
        moeda="BRL",
        tipo="credito",
        **{**_DEFAULT_RECEITA, **overrides},
    )


def _despesa(**overrides) -> ClassifiedTransaction:
    return ClassifiedTransaction(
        kind="despesa",
        moeda="BRL",
        tipo="debito",
        **{**_DEFAULT_DESPESA, **overrides},
    )


class TestCrossDocumentDedup:
    def test_arvo_3x_collapses_to_1(self):
        # Cenário Arvo do report 9b31d739-...: mesmo PIX C6 presente em 3 E3s
        # (1 CSV C6 explícito + 2 PDFs C6 "unknown" — snapshots cumulativos do
        # app C6 PJ não reconhecidos pelo classificador E0). Drift de casing no
        # banco simula documento sem identificação canônica.
        txs = [
            _receita(banco="C6Bank"),
            _receita(banco="C6 Bank"),  # mesmo banco, casing drift
            _receita(banco="c6bank"),  # mesmo banco, lowercase
        ]
        cf = _builder().build(txs)

        assert cf.receitas.total_transacoes == 1
        assert cf.receitas.total_geral == 47208.77
        assert cf.fluxo_mensal.receitas["por_mes"]["2026-03"]["Arvo (David - PJ)"] == 47208.77
        assert cf.dedup_report.collapsed_count == 2
        # Valor ≥ R$ 10k → review entry esperada
        assert cf.dedup_report.review_count == 1
        assert cf.dedup_report.review_entries[0].reason == "material_value"
        assert cf.dedup_report.review_entries[0].collision_count == 2

    def test_couple_same_bank_different_titular_preserved(self):
        # Casal recebendo PIX idêntico do mesmo pagador no mesmo dia: 2 linhas.
        txs = [
            _receita(titular="david", origem="Cliente X"),
            _receita(titular="mariana", origem="Cliente X"),
        ]
        cf = _builder().build(txs)

        assert cf.receitas.total_transacoes == 2
        assert cf.receitas.total_geral == 47208.77 * 2
        assert cf.dedup_report.collapsed_count == 0

    def test_internal_transfer_different_tipo_conta_preserved(self):
        # Mesmo titular/banco, CC→poupança: tipo_conta separa.
        txs = [
            _receita(tipo_conta="extratoconta", valor=1000.0, descricao="TRANSF INTERNA"),
            _receita(tipo_conta="extratopoupanca", valor=1000.0, descricao="TRANSF INTERNA"),
        ]
        cf = _builder().build(txs)

        assert cf.receitas.total_transacoes == 2
        assert cf.dedup_report.collapsed_count == 0

    def test_distinct_installments_preserved(self):
        # PARC 3/12 e PARC 4/12 no mesmo dia/valor — lançamentos legítimos.
        txs = [
            _despesa(descricao="LOJA X PARC 3/12", valor=199.90, categoria="lazer"),
            _despesa(descricao="LOJA X PARC 4/12", valor=199.90, categoria="lazer"),
        ]
        cf = _builder().build(txs)

        assert cf.despesas.total_transacoes == 2
        assert cf.dedup_report.collapsed_count == 0

    def test_receita_and_despesa_same_signature_not_collapsed(self):
        # ClassifiedTransaction guarda valor positivo em ambas kinds; dedup
        # é por kind, então receita e despesa não colapsam entre si.
        txs = [
            _receita(valor=500.0, descricao="X", categoria="rec", origem="O"),
            _despesa(valor=500.0, descricao="X", categoria="desp"),
        ]
        cf = _builder().build(txs)

        assert cf.receitas.total_transacoes == 1
        assert cf.despesas.total_transacoes == 1

    def test_below_threshold_silent_dedup(self):
        # Dedup silente (não vira review) quando valor < R$ 10k e tipo_conta
        # presente nos dois lados.
        txs = [
            _despesa(valor=200.0, descricao="UBER VIAGEM 123"),
            _despesa(valor=200.0, descricao="UBER VIAGEM 123"),
        ]
        cf = _builder().build(txs)

        assert cf.despesas.total_transacoes == 1
        assert cf.dedup_report.collapsed_count == 1
        assert cf.dedup_report.review_count == 0

    def test_missing_tipo_conta_triggers_review(self):
        # Chave incompleta — não decide sozinho: review.
        txs = [
            _despesa(valor=200.0, tipo_conta=""),
            _despesa(valor=200.0, tipo_conta=""),
        ]
        cf = _builder().build(txs)

        assert cf.despesas.total_transacoes == 1
        assert cf.dedup_report.collapsed_count == 1
        assert cf.dedup_report.review_count == 1
        assert cf.dedup_report.review_entries[0].reason == "missing_tipo_conta"

    def test_dedup_stable_keeps_first_occurrence(self):
        # Ordem do output deve refletir primeira ocorrência (estável).
        a = _receita(descricao="A", valor=100.0)
        b = _receita(descricao="A", valor=100.0)  # mesmo hash de a
        cf = _builder().build([a, b])

        # `a` é o sobrevivente — único item em `dados[<cat>]`.
        items = cf.receitas.dados[a.categoria]
        assert len(items) == 1

    def test_dedup_report_empty_when_no_collisions(self):
        txs = [_receita(data=f"2026-03-{d:02d}") for d in (1, 2, 3, 4)]
        cf = _builder().build(txs)

        assert cf.receitas.total_transacoes == 4
        assert cf.dedup_report.collapsed_count == 0
        assert cf.dedup_report.review_count == 0

    def test_fluxo_mensal_total_correct_after_dedup(self):
        # Sintoma original do bug: tooltip do mês com valor 3× — após dedup
        # o `_total` do mês deve voltar ao valor real.
        txs = [
            _receita(banco="C6Bank"),  # 47208.77
            _receita(banco="C6 Bank"),
            _receita(banco="c6bank"),
            _receita(
                data="2026-03-15",
                valor=8247.0,
                descricao="Rendimentos CDB",
                categoria="rendimento",
                origem="Rendimentos Financeiros",
                banco="Itau",
            ),
        ]
        cf = _builder().build(txs)

        total_mar = cf.fluxo_mensal.receitas["por_mes"]["2026-03"]["_total"]
        assert total_mar == 47208.77 + 8247.0
