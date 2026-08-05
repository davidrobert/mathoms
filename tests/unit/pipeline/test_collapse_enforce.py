"""`collapse()` — mutação e declaração no MESMO passo ([[A40.l2]] D2 · [[ADR-354]]).

Identidade de row é identidade de **objeto** dentro da chamada: o measure e o
agrupamento rodam sobre a mesma lista, no mesmo processo, então selecionar objetos
dispensa endereço serializado (e portanto dispensa `_hash_v3`). Os dois eixos que
importam aqui são **externos**: mutação × declaração, e determinismo sob permutação.
"""

from __future__ import annotations

import random
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models.document import BankStatement  # noqa: E402
from pipeline.domain.models.transaction import Money, Transaction  # noqa: E402
from pipeline.domain.services.cross_document_collapser import CrossDocumentCollapser  # noqa: E402


def _tx(valor: str = "-100.00", desc: str = "compra mercado") -> Transaction:
    return Transaction(date=date(2026, 3, 30), description=desc, amount=Money.of(valor, "BRL"))


def _doc(n: int, arquivo: str, metodo: str = "native", valor: str = "-100.00") -> BankStatement:
    llm = metodo == "llm"
    return BankStatement(
        institution="banco exemplo",
        member_key=None if llm else "titular exemplo",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        currency="BRL",
        transactions=[_tx(valor) for _ in range(n)],
        account_type="extrato" if llm else "extratoconta",
        extraction_method=metodo,
        source_document=arquivo,
    )


def _par() -> list[BankStatement]:
    return [_doc(1, "marco.pdf"), _doc(1, "anual.pdf", "llm")]


def _total_tx(stmts) -> int:
    return sum(len(s.transactions) for s in stmts)


# ── eixo externo 1: mutação × declaração ──


def test_rows_removidas_de_fato_igualam_o_declarado() -> None:
    """O eixo que substitui `alvo_enderecavel`: o que saiu == o que o measure declarou."""
    entrada = _par()

    saida, candidatos, removals = CrossDocumentCollapser().collapse(entrada)

    declarado = sum(c.removable_rows for c in candidatos if c.collapsible)
    assert _total_tx(entrada) - _total_tx(saida) == declarado == 1
    assert sum(r.count for r in removals) == declarado


def test_removal_declara_cents_ASSINADO_nao_magnitude() -> None:
    """`candidate.valor_cents` é magnitude (`abs`); o ledger grava assinado. Reusar a
    magnitude faria `_declared_dedup_cents` nunca fechar contra `val_in − val_out`."""
    _saida, candidatos, removals = CrossDocumentCollapser().collapse(_par())

    assert candidatos[0].valor_cents == 10000  # magnitude, no candidato
    assert sum(r.count for r in removals) == 1
    assert sum(r.valor_cents for r in removals) == -10000  # assinado, no ledger


def test_removal_e_agregado_por_source_document() -> None:
    """O ledger é per-group ⇒ atribuição global não fecha."""
    statements = [_doc(1, "a.pdf"), _doc(1, "b.pdf"), _doc(1, "llm.pdf", "llm")]

    _s, _c, removals = CrossDocumentCollapser().collapse(statements)

    assert {r.source for r in removals} == {"b.pdf", "llm.pdf"}  # 'a.pdf' sobrevive
    assert all(r.canal == "cross_document_collapse" for r in removals)


# ── eixo externo 2: determinismo ──


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_permutacao_de_statements_nao_muda_o_resultado(seed) -> None:
    """Ordem total de CONTEÚDO: shuffle da entrada não move a escolha."""
    base = [_doc(1, "a.pdf"), _doc(1, "b.pdf"), _doc(1, "c.pdf"), _doc(1, "llm.pdf", "llm")]
    embaralhado = list(base)
    random.Random(seed).shuffle(embaralhado)

    ref, _c1, r1 = CrossDocumentCollapser().collapse(base)
    alt, _c2, r2 = CrossDocumentCollapser().collapse(embaralhado)

    sobrevive = lambda s: sorted((x.source_document, len(x.transactions)) for x in s)  # noqa: E731
    assert sobrevive(ref) == sobrevive(alt)
    assert sorted((r.source, r.count) for r in r1) == sorted((r.source, r.count) for r in r2)


def test_collapse_e_idempotente() -> None:
    """Re-rodar sobre a saída não remove mais nada (não há mais chave cross-prov)."""
    saida1, _c, _r = CrossDocumentCollapser().collapse(_par())

    saida2, cand2, removals2 = CrossDocumentCollapser().collapse(saida1)

    assert _total_tx(saida2) == _total_tx(saida1)
    assert removals2 == ()
    assert [c for c in cand2 if c.collapsible] == []


def test_nao_muta_os_statements_de_entrada() -> None:
    """Cópias via `replace`; o original preserva as rows."""
    entrada = _par()

    CrossDocumentCollapser().collapse(entrada)

    assert _total_tx(entrada) == 2


def test_replace_preserva_campo_que_construtor_campo_a_campo_perderia() -> None:
    """Regressão de ADR-226 PR2: `account_number_norm` sobrevive ao colapso."""
    nativa, llm = _par()
    nativa.account_number_raw, nativa.account_number_norm = "12345-6", "123456"

    saida, _c, _r = CrossDocumentCollapser().collapse([nativa, llm])

    sobrevivente = next(s for s in saida if s.extraction_method == "native")
    assert sobrevivente.account_number_norm == "123456"


def test_grupo_bloqueado_nao_remove_row() -> None:
    """Predicado reprovou ⇒ nenhuma row sai, e nenhum removal é declarado."""
    statements = [_doc(1, "a.pdf"), _doc(1, "b.pdf", valor="-100.00")]
    statements[1].institution = "outro banco"

    saida, candidatos, removals = CrossDocumentCollapser().collapse(statements)

    assert candidatos[0].blocked_reason == "banco_conflitante"
    assert (_total_tx(saida), removals) == (2, ())
