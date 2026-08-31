"""A perna de VALOR E3→E4 é capaz de falhar (anti-inércia · [[A42.l18]] · [[ADR-426]]).

Os testes de `test_ledger_conservation.py` provam a COMPARAÇÃO com sinais montados à
mão. Não provam que algum produtor real consegue emitir números divergentes — e o
defeito de origem era exatamente esse: o lado-saída era uma re-soma da MESMA
população de origem, então `Δvalor = 0` era identidade, não medição.

Aqui a cadeia é a real — classificador → `CashFlowBuilder` → `conferencia_signals` →
`e3_to_e4` — para que o eixo-valor seja exercido pelo produtor, não pela fixture.
"""

from __future__ import annotations

import copy

from dev.ledger_conservation import (
    COBERTO_SEM_VALOR,
    CONSERVADO,
    e3_to_e4,
)
from pipeline.domain.services.cash_flow_builder import CashFlowBuilder
from pipeline.domain.services.e4_serialization import conferencia_signals
from pipeline.domain.services.transaction_classifier import (
    ClassifierConfig,
    TransactionClassifier,
)

_ALUGUEL = {"data": "2026-01-06", "descricao": "ALUGUEL", "valor": -1800.00, "tipo": "debito"}
_BASE = [
    {"data": "2026-01-05", "descricao": "MERCADO XPTO", "valor": -250.00, "tipo": "debito"},
    _ALUGUEL,
    {"data": "2026-01-10", "descricao": "SALARIO", "valor": 9000.00, "tipo": "credito"},
]


class _Result:
    """Superfície mínima que ``conferencia_signals`` consome."""

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


def _rodar(txs: list[dict], *, suprimir: str | None = None):
    """Roda a cadeia real e devolve o ``ConservationResult`` da perna E3→E4."""
    conta = _conta(txs)
    classified = TransactionClassifier(ClassifierConfig()).classify_all([conta])
    cash_flow = CashFlowBuilder(now=None).build(classified)
    signals = conferencia_signals(_Result(classified, cash_flow))
    if suprimir is not None:
        signals.pop(suprimir)
    despesas = cash_flow.despesas.to_legacy_dict()
    despesas["_lineage"] = {"signals": signals}
    receitas = cash_flow.receitas.to_legacy_dict()
    return e3_to_e4([conta], despesas, receitas, cash_flow.transferencias_count), cash_flow


def test_cadeia_real_sem_defeito_conserva() -> None:
    r, _ = _rodar(copy.deepcopy(_BASE))
    assert r.verdict == CONSERVADO
    assert r.value_in_cents == r.value_out_cents == 1_105_000


def test_dedup_do_e4_e_load_bearing_no_eixo_valor() -> None:
    # É o controle que a perna inerte não passava: antes, a duplicata inflava OS DOIS
    # lados igualmente e `Δ` continuava 0 (medido em [[A42.l18]]).
    """O produtor colapsa 1 row de R$1.800; sem o valor declarado o destino não fecha."""
    txs = copy.deepcopy(_BASE) + [copy.deepcopy(_ALUGUEL)]
    r, cash_flow = _rodar(txs)
    assert cash_flow.dedup_report.collapsed_count == 1
    assert cash_flow.dedup_report.collapsed_cents == 180_000  # exato, não só contado
    assert r.verdict == CONSERVADO and r.dups == 1

    suprimido, _ = _rodar(txs, suprimir="dedup_collapsed_cents")
    assert suprimido.verdict == COBERTO_SEM_VALOR
    assert suprimido.value_out_cents is None


def test_valor_removido_pelo_dedup_bate_com_o_buraco_nos_baldes() -> None:
    """`collapsed_cents` mede o buraco real que o dedup abre no destino."""
    limpo, cf_limpo = _rodar(copy.deepcopy(_BASE))
    com_dup, cf_dup = _rodar(copy.deepcopy(_BASE) + [copy.deepcopy(_ALUGUEL)])
    baldes_limpo = cf_limpo.despesas.total_geral + cf_limpo.receitas.total_geral
    baldes_dup = cf_dup.despesas.total_geral + cf_dup.receitas.total_geral
    assert baldes_limpo == baldes_dup  # o dedup devolveu os baldes ao estado limpo
    assert com_dup.value_in_cents - limpo.value_in_cents == 180_000
    assert cf_dup.dedup_report.collapsed_cents == 180_000


def test_perna_nao_discrimina_sinal_e_a_limitacao_esta_declarada() -> None:
    """Fronteira declarada ([[ADR-426]] §Consequências), não defeito silencioso."""
    # Inverter o sinal de N débitos deixa `Δ=0`: o classificador aplica `abs(valor)`
    # e, na forma dominante do dado (tx sem `tipo`), a direção É derivada do sinal —
    # não existe segunda declaração independente para discordar dele. Erro de sinal é
    # fidelidade do E3 (perna E2→E3 / `parse-certify`), não conservação desta transição.
    # Se a perna passar a discriminar, este teste falha e a ADR deve ser emendada.
    invertido = copy.deepcopy(_BASE)
    for tx in invertido:
        if tx["tipo"] == "debito":
            tx["valor"] = -tx["valor"]  # só o SINAL; `tipo` segue "debito"
    r, _ = _rodar(invertido)
    assert r.value_in_cents - r.value_out_cents == 0
