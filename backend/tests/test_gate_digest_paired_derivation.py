"""Paridade do ``gate_digest`` entre os DOIS produtores reais ([[A40.l2]] PR3b).

O gate de pré-condição do colapso cruza um digest produzido no **pipeline** (colapsador,
sobre `BankStatement`/`Transaction`) com um produzido no **backend** (colunas de snapshot da
[[ADR-282]], gravadas por `override_identity`). Se as duas pontas divergirem, o join morre em
silêncio e `hits == 0` vira aprovação por vácuo.

`backend/tests/test_collapse_precondition.py` **não** cobre isso: ele constrói o `gate_digest`
da fixture **chamando `gate_key_digest`** — o produtor da fixture é o consumidor sob teste, e
uma divergência entre os caminhos reais passaria verde. Este arquivo alimenta cada lado pelo
seu produtor de produção e só então compara.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from backend.app.models.transaction_override import TransactionOverride
from backend.app.services.internal_ops.collapse_precondition import _override_gate_digest
from backend.app.services.override_identity import inputs_from_classified_tx
from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Money, Transaction
from pipeline.domain.services._tx_identity import HashInputs
from pipeline.domain.services.cross_document_collapser import CrossDocumentCollapser
from pipeline.domain.services.transaction_classifier import ClassifiedTransaction

_DATA = date(2026, 3, 30)
_DESCRICAO = "compra mercado central"
_VALOR = "-100.00"
_MOEDA = "BRL"


def _tx() -> Transaction:
    return Transaction(date=_DATA, description=_DESCRICAO, amount=Money.of(_VALOR, _MOEDA))


def _stmt(arquivo: str, *, llm: bool) -> BankStatement:
    return BankStatement(
        institution="banco exemplo",
        member_key=None if llm else "titular exemplo",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        currency=_MOEDA,
        transactions=[_tx()],
        account_type="extrato" if llm else "extratoconta",
        extraction_method="llm" if llm else "native",
        source_document=arquivo,
    )


def _digest_do_pipeline() -> str:
    """Produtor 1 — o colapsador, sobre os objetos de domínio do E3."""
    candidatos = (
        CrossDocumentCollapser()
        .measure([_stmt("nativo.json", llm=False), _stmt("llm.json", llm=True)])
        .candidates
    )
    assert len(candidatos) == 1, "fixture deixou de produzir candidato — teste vira vácuo"
    return candidatos[0].gate_digest


def _inputs_do_backend() -> HashInputs:
    """Produtor 2 — o adapter que grava as colunas de snapshot da ADR-282."""
    return inputs_from_classified_tx(
        ClassifiedTransaction(
            kind="despesa",
            data=_DATA.isoformat(),
            banco="banco exemplo",
            titular="titular exemplo",
            tipo_conta="extratoconta",
            valor=Decimal(_VALOR),
            moeda=_MOEDA,
            descricao=_DESCRICAO,
            tipo="debito",
        )
    )


def _override_de(inputs: HashInputs) -> TransactionOverride:
    return TransactionOverride(
        tx_data=inputs.data,
        tx_valor_cents=inputs.valor_cents,
        tx_moeda=inputs.moeda,
        tx_descricao=inputs.descricao,
        tx_direction=inputs.direction,
        hash_version=2,
    )


def test_os_dois_produtores_reais_concordam_no_gate_digest():
    """A mesma transação, pelos dois caminhos de produção, tem de dar o mesmo digest."""
    do_backend = _override_gate_digest(_override_de(_inputs_do_backend()))

    assert do_backend is not None
    assert _digest_do_pipeline() == do_backend


def test_moeda_com_espaco_nao_separa_os_lados():
    """Regressão: o produtor fazia `.strip().upper()` e a função canônica só `.upper()`."""
    # Inerte em produção porque os dois chamadores passam dado já stripado — e por isso
    # invisível, que é como a divergência do `keep_split` sobreviveu à suíte inteira.
    inputs = _inputs_do_backend()
    com_espaco = _override_de(inputs)
    com_espaco.tx_moeda = f" {inputs.moeda} "

    assert _override_gate_digest(com_espaco) == _digest_do_pipeline()


@pytest.mark.parametrize("campo", ["tx_data", "tx_valor_cents", "tx_descricao"])
def test_digest_discrimina_cada_componente(campo):
    """Sem isto, um digest constante passaria os testes acima."""
    base = _override_de(_inputs_do_backend())
    mexido = _override_de(_inputs_do_backend())
    setattr(
        mexido,
        campo,
        {"tx_data": "2020-01-01", "tx_valor_cents": 1, "tx_descricao": "outra"}[campo],
    )

    assert _override_gate_digest(base) != _override_gate_digest(mexido)


def test_produtor_DELEGA_a_funcao_canonica(monkeypatch):
    """Prova a delegação, não a igualdade — a prova de mutação mostrou que só a igualdade
    deixa a duplicação voltar sem quebrar nada."""
    # Com input já stripado, tupla inline e função canônica dão o MESMO digest: os testes de
    # paridade acima passam com a duplicação reintroduzida. Só interceptar a chamada distingue.
    import pipeline.domain.services.cross_document_collapser as mod

    monkeypatch.setattr(mod, "gate_key_digest", lambda **_: "SENTINELA")

    assert _digest_do_pipeline() == "SENTINELA"
