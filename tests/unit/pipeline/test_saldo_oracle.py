"""Oráculo de saldo do colapso ([[A40.l2]] · 4º P0).

A prova que o enforce planejava usar era verde por construção em DUAS camadas: o
adapter passa `statements` pré-colapso aos validators, e o validator compara só
metadado de saldo. Este oráculo mede outra coisa — o resíduo — e julga pela DIREÇÃO.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dev.ledger_saldo_oracle import saldo_oracle  # noqa: E402
from pipeline.domain.models.document import BankStatement  # noqa: E402
from pipeline.domain.models.transaction import Money, Transaction  # noqa: E402


def _stmt(valores: list[str], arquivo: str, *, abertura="0.00", fechamento=None) -> BankStatement:
    """Statement cujo `closing` é declarado — o resíduo mede a diferença contra as tx."""
    txs = [
        Transaction(date=date(2026, 3, 30), description="mov", amount=Money.of(v, "BRL"))
        for v in valores
    ]
    return BankStatement(
        institution="banco exemplo",
        member_key="titular exemplo",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        currency="BRL",
        transactions=txs,
        opening_balance=Money.of(abertura, "BRL"),
        closing_balance=Money.of(fechamento, "BRL") if fechamento else None,
        account_type="extratoconta",
        source_document=arquivo,
    )


def test_remover_duplicata_espuria_APROXIMA_o_residuo_de_zero() -> None:
    """O caso que autoriza: o banco declarou -100, mas o extrato trouxe a row 2×."""
    antes = _stmt(["-100.00", "-100.00"], "a.pdf", fechamento="-100.00")  # resíduo +100
    depois = _stmt(["-100.00"], "a.pdf", fechamento="-100.00")  # resíduo 0

    r = saldo_oracle([antes], [depois])

    assert (r.mensuraveis, r.melhoraram, r.pioraram) == (1, 1, 0)
    assert r.aprovado


def test_remover_row_REAL_afasta_o_residuo_e_reprova() -> None:
    """O caso que reprova, e é o que as 140 nativas exibiram no corpus (3/3)."""
    antes = _stmt(["-100.00", "-50.00"], "a.pdf", fechamento="-150.00")  # resíduo 0
    depois = _stmt(["-100.00"], "a.pdf", fechamento="-150.00")  # resíduo -50

    r = saldo_oracle([antes], [depois])

    assert (r.melhoraram, r.pioraram, r.cents_piora) == (0, 1, 5000)
    assert not r.aprovado
    assert r.fontes_que_pioraram == ("a.pdf",)


def test_statement_sem_saldo_declarado_nao_e_mensuravel() -> None:
    """Perna LLM tipicamente não traz saldo — não inventa veredito sobre ela."""
    antes = _stmt(["-100.00", "-100.00"], "llm.pdf")  # sem closing
    depois = _stmt(["-100.00"], "llm.pdf")

    r = saldo_oracle([antes], [depois])

    assert r.mensuraveis == 0
    assert r.vacuo  # nada a reprovar — mas também nada observado
    assert not r.aprovado  # e vácuo NÃO é aprovação


def test_statement_intocado_conta_como_inalterado() -> None:
    a = _stmt(["-100.00"], "a.pdf", fechamento="-100.00")

    r = saldo_oracle([a], [a])

    assert (r.mensuraveis, r.inalterados, r.pioraram) == (1, 1, 0)


def test_um_grupo_que_piora_reprova_o_conjunto_inteiro() -> None:
    """Fail-closed: melhorar em 2 não compensa piorar em 1 — a direção não é média."""
    bom_a = _stmt(["-100.00", "-100.00"], "bom.pdf", fechamento="-100.00")
    bom_d = _stmt(["-100.00"], "bom.pdf", fechamento="-100.00")
    ruim_a = _stmt(["-100.00", "-50.00"], "ruim.pdf", fechamento="-150.00")
    ruim_d = _stmt(["-100.00"], "ruim.pdf", fechamento="-150.00")

    r = saldo_oracle([bom_a, bom_a, ruim_a], [bom_d, bom_d, ruim_d])

    assert (r.melhoraram, r.pioraram) == (1, 1)  # 'bom.pdf' aparece 2x, dedup por source
    assert not r.aprovado


def test_aprovacao_por_VACUIDADE_nao_e_aprovacao() -> None:
    """`pioraram == 0` sozinho aprova quando o oráculo não observou NADA — que é o caso
    comum, porque a perna LLM tipicamente não traz saldo. Medido no corpus: 73/73
    inalterados com `aprovado=true` na primeira versão."""
    intocado = _stmt(["-100.00"], "a.pdf", fechamento="-100.00")

    r = saldo_oracle([intocado], [intocado])

    assert (r.mensuraveis, r.pioraram) == (1, 0)
    assert r.observados == 0
    assert r.vacuo
    assert not r.aprovado  # não aprova sem ter visto nada


def test_aprova_quando_observa_e_a_direcao_e_boa() -> None:
    antes = _stmt(["-100.00", "-100.00"], "a.pdf", fechamento="-100.00")
    depois = _stmt(["-100.00"], "a.pdf", fechamento="-100.00")

    r = saldo_oracle([antes], [depois])

    assert (r.observados, r.pioraram) == (1, 0)
    assert not r.vacuo
    assert r.aprovado
