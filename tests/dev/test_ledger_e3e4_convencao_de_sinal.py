"""Uma convenção de sinal por termo no eixo-valor E3→E4 ([[ADR-434]] · [[A42.l25]]).

A [[ADR-426]] ligou a perna de valor, mas somava `total_geral` dos dois baldes — soma
ASSINADA — ao lado de dois termos em Σ|valor|. Quatro termos, duas convenções: o destino
saía `2 × Σ|receitas negativas|` menor **sempre**. Offset constante, não resíduo — logo
uma perda real do mesmo tamanho publicaria `Δ = 0` e o veredito diria `conservado`.

A cadeia aqui é a real (classificador → `CashFlowBuilder` → `conferencia_signals` →
`e3_to_e4`), e a fixture tem uma receita **negativa** — sem ela o eixo é uma identidade
trivial e nenhum destes testes discrimina coisa alguma.
"""

from __future__ import annotations

import copy

from dev.golden_diff import to_cents
from dev.ledger_conservation import COBERTO_SEM_VALOR, CONSERVADO, e3_to_e4
from dev.ledger_verdicts import delta_cents
from pipeline.domain.services.cash_flow_builder import CashFlowBuilder
from pipeline.domain.services.e4_serialization import conferencia_signals
from pipeline.domain.services.transaction_classifier import (
    ClassifiedTransaction,
    ClassifierConfig,
    TransactionClassifier,
)

# `PAGAMENTO EFETUADO` é crédito e vira receita NEGATIVA — o mecanismo real medido em
# `ws-1b9f2cf5` (48 tx, Σ|v| = R$ 9.993,86), e o defeito de domínio da [[ADR-429]].
_ESTORNO = {
    "data": "2026-01-12",
    "descricao": "PAGAMENTO EFETUADO",
    "valor": -500.00,
    "tipo": "credito",
}
_BASE = [
    {"data": "2026-01-05", "descricao": "MERCADO XPTO", "valor": -250.00, "tipo": "debito"},
    {"data": "2026-01-10", "descricao": "SALARIO", "valor": 9000.00, "tipo": "credito"},
    _ESTORNO,
]


class _Result:
    def __init__(self, classified, cash_flow) -> None:
        self.classified, self.cash_flow = classified, cash_flow


def _conta(txs: list[dict]) -> dict:
    return {
        "banco": "itau",
        "tipo_conta": "corrente",
        "titular": "T",
        "moeda": "BRL",
        "transacoes": txs,
        "transacoes_total": len(txs),
    }


def _rodar(txs: list[dict], *, mutar=None, suprimir: str | None = None):
    """Cadeia real → ``(ConservationResult, cash_flow, signals)``."""
    conta = _conta(txs)
    classified = TransactionClassifier(ClassifierConfig()).classify_all([conta])
    cash_flow = CashFlowBuilder(now=None).build(classified)
    signals = conferencia_signals(_Result(classified, cash_flow))
    if suprimir is not None:
        signals.pop(suprimir)
    if mutar is not None:
        signals.update(mutar)
    despesas = cash_flow.despesas.to_legacy_dict()
    despesas["_lineage"] = {"signals": signals}
    receitas = cash_flow.receitas.to_legacy_dict()
    r = e3_to_e4([conta], despesas, receitas, cash_flow.transferencias_count)
    return r, cash_flow, signals


# ─────────────── a fixture discrimina (anti-inércia) ───────────────


def test_o_produtor_emite_receita_negativa_e_o_eixo_fecha() -> None:
    """Sem receita negativa no corpus, tudo abaixo passaria por identidade trivial."""
    r, cf, _ = _rodar(copy.deepcopy(_BASE))
    assert cf.receitas_negativas_cents == 50_000  # a fixture TEM o fenômeno
    assert cf.receitas.total_geral == 8500.0  # e o balde publica o líquido
    assert r.verdict == CONSERVADO
    assert delta_cents(r.value_in_cents, r.value_out_cents) == 0


def test_a_formula_antiga_publicava_delta_espurio_na_mesma_fixture() -> None:
    """O contrafactual que prova a não-inércia: a fórmula da [[ADR-426]] §D2, aplicada
    a ESTA fixture, acusa `-2 × Σ|negativas|` onde não há perda nenhuma."""
    r, cf, sig = _rodar(copy.deepcopy(_BASE))
    antiga = (
        to_cents(cf.despesas.total_geral)
        + to_cents(cf.receitas.total_geral)
        + int(sig["transferencias_cents"])
        + int(sig["dedup_collapsed_cents"])
    )
    assert delta_cents(r.value_in_cents, antiga) == -2 * cf.receitas_negativas_cents == -100_000
    assert delta_cents(r.value_in_cents, r.value_out_cents) == 0  # a nova fecha


# ─────────────── controle positivo (critério 4 da lane) ───────────────


def test_um_centavo_em_um_termo_move_o_delta_um_centavo_com_o_sinal_do_rotulo() -> None:
    """`DELTA_LABEL` é destino−origem: inflar o DESTINO em 1 sobe o Δ em 1."""
    base, _, sig = _rodar(copy.deepcopy(_BASE))
    for termo in ("despesas_abs_cents", "receitas_abs_cents", "transferencias_cents"):
        mais_um, _, _ = _rodar(copy.deepcopy(_BASE), mutar={termo: str(int(sig[termo]) + 1)})
        movimento = delta_cents(mais_um.value_in_cents, mais_um.value_out_cents) - delta_cents(
            base.value_in_cents, base.value_out_cents
        )
        assert movimento == 1, f"{termo} não move o Δ em 1 centavo"


def test_um_centavo_na_receita_negativa_do_e3_nao_move_o_delta() -> None:
    """O dual, e é o que a fórmula antiga errava: mexer 1 centavo numa receita NEGATIVA
    move origem e destino juntos ⇒ Δ segue 0. Na fórmula antiga movia 2 centavos, porque
    origem somava `+1` e destino somava `-1`."""
    txs = copy.deepcopy(_BASE)
    txs[2]["valor"] = -500.01
    r, cf, sig = _rodar(txs)
    assert delta_cents(r.value_in_cents, r.value_out_cents) == 0
    antiga = (
        to_cents(cf.despesas.total_geral)
        + to_cents(cf.receitas.total_geral)
        + int(sig["transferencias_cents"])
        + int(sig["dedup_collapsed_cents"])
    )
    assert delta_cents(r.value_in_cents, antiga) == -100_002  # 2 centavos a mais que o base


# ─────────────── imunidade à [[ADR-429]] ───────────────


_DESPESA = {
    "kind": "despesa",
    "data": "2026-01-05",
    "descricao": "ESTORNO DE COMPRA",
    "banco": "itau",
    "moeda": "BRL",
    "tipo_conta": "corrente",
    "titular": "T",
    "tipo": "debito",
    "categoria": "casa",
}


def test_despesa_assinada_negativa_mantem_o_eixo_fechado() -> None:
    """A [[ADR-429]] fará `despesas.dados[*].valor` deixar de ser ≥ 0. Quando isso
    entrar, `despesas.total_geral` deixa de ser Σ|valor| pelo MESMO mecanismo que hoje
    quebra receitas — e o eixo tem de continuar fechando, sem mudar de forma."""
    despesas = [ClassifiedTransaction(valor=v, **_DESPESA) for v in (300.0, -100.0)]
    cf = CashFlowBuilder(now=None).build(despesas)
    assert cf.despesas.total_geral == 200.0  # publicado: líquido do estorno
    assert cf.despesas_abs_cents == 40_000  # eixo: Σ|valor|
    assert cf.despesas_negativas_cents == 10_000
    # A ponte que o harness assevera reconstrói o número publicado a partir do declarado.
    assert cf.despesas_abs_cents == to_cents(cf.despesas.total_geral) + 2 * (
        cf.despesas_negativas_cents
    )


# ─────────────── fail-closed ───────────────


def test_ausencia_de_abs_cents_e_nao_medido_nunca_conservado() -> None:
    for chave in ("despesas_abs_cents", "receitas_abs_cents"):
        r, _, _ = _rodar(copy.deepcopy(_BASE), suprimir=chave)
        assert r.verdict == COBERTO_SEM_VALOR
        assert r.value_out_cents is None, f"{chave} suprimida deveria zerar o destino"
        assert r.value_terms is None


def test_ponte_rompida_rebaixa_o_veredito() -> None:
    """Termo declarado que não reconstrói `total_geral` = o eixo parou de cruzar o
    número publicado. Rebaixa, nunca sobe a perda ([[ADR-426]] §D3 preservado)."""
    _, _, sig = _rodar(copy.deepcopy(_BASE))
    r, _, _ = _rodar(
        copy.deepcopy(_BASE),
        mutar={"receitas_abs_cents": str(int(sig["receitas_abs_cents"]) + 1)},
    )
    assert r.verdict == COBERTO_SEM_VALOR
    assert "ponte abs↔assinado rompida em receitas" in r.detail


def test_chaves_novas_ficam_fora_do_whitelist_do_parecer() -> None:
    """[[ADR-173]] hard-stop: chave nova no E5 mudaria o `sha256` do payload e forçaria
    regeração integral da base do parecer num PR que corrige zero."""
    from pipeline.domain.services.e5_lineage import _CONFERENCIA_SIGNAL_KEYS

    novas = {
        "despesas_abs_cents",
        "receitas_abs_cents",
        "despesas_negativas_cents",
        "receitas_negativas_cents",
    }
    assert novas.isdisjoint(_CONFERENCIA_SIGNAL_KEYS)


# ─────────────── um conversor por campo (critério 3 da lane) ───────────────

# `1234.565` é meio-centavo exato: `cents_int` (legado do produtor,
# `int(round(float(v)*100))`) devolve 123456 e `Decimal(str(v))` + ROUND_HALF_UP
# (harness) devolve 123457. Enquanto os dois lados usavam conversores diferentes, o eixo
# tinha um segundo canal de divergência que o corpus só não exercia por sorte.
_MEIO_CENTAVO = {
    "data": "2026-01-15",
    "descricao": "CONSULTORIA",
    "valor": 1234.565,
    "tipo": "credito",
}


def test_valor_no_meio_centavo_converte_igual_nos_dois_lados() -> None:
    r, cf, _ = _rodar(copy.deepcopy(_BASE) + [copy.deepcopy(_MEIO_CENTAVO)])
    assert delta_cents(r.value_in_cents, r.value_out_cents) == 0
    assert r.verdict == CONSERVADO
    # O termo declarado arredonda para CIMA, como o harness — não para baixo (123456).
    assert cf.receitas_abs_cents == 1_073_457
