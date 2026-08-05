"""Guardas gêmeas da cardinalidade por ARQUIVO ([[ADR-354]] §Emenda 2 · [[A40.l2]] D4).

A unidade de contagem de eventos é (proveniência, source_document): um arquivo
reportando 2× = 2 eventos; dois arquivos reportando 1× cada = 1 evento. Cada teste
mata uma mutação específica — trocar o `max` por arquivo por `max` por perna
(regressão ao multiset antigo) ou por 1 (colapso ingênuo).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models.document import BankStatement  # noqa: E402
from pipeline.domain.models.transaction import Money, Transaction  # noqa: E402
from pipeline.domain.services.cross_document_collapser import (  # noqa: E402
    CrossDocumentCollapser,
    _row_hash,
)


def _tx() -> Transaction:
    return Transaction(
        date=date(2026, 3, 30), description="compra mercado", amount=Money.of("-100.00", "BRL")
    )


def _doc(n_tx: int, arquivo: str, metodo: str = "native") -> BankStatement:
    """``n_tx`` cópias da MESMA transação, vindas de UM arquivo."""
    llm = metodo == "llm"
    return BankStatement(
        institution="banco exemplo",
        member_key=None if llm else "titular exemplo",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        currency="BRL",
        transactions=[_tx() for _ in range(n_tx)],
        account_type="extrato" if llm else "extratoconta",
        extraction_method=metodo,
        source_document=arquivo,
    )


def _measure(statements):
    return CrossDocumentCollapser().measure(statements)


def test_repeticao_no_mesmo_arquivo_e_dois_eventos() -> None:
    """Guarda 1: um ARQUIVO reportando 2× = 2 eventos — repetição legítima protegida."""
    (c,) = _measure([_doc(2, "extrato_marco.pdf"), _doc(2, "anual.pdf", "llm")])

    assert c.survivor_cardinality == 2
    assert c.removable_rows == 2  # sobram as 2 nativas do mesmo arquivo


def test_arquivos_sobrepostos_na_mesma_perna_sao_um_evento() -> None:
    """Guarda 2: dois ARQUIVOS da mesma perna, 1× cada = 1 evento. Era o furo do
    multiset por perna (262/262 legs com ≥2 rows tinham source distinto; 0/262 eram
    2 eventos)."""
    statements = [_doc(1, "marco.pdf"), _doc(1, "anual.pdf"), _doc(1, "reex.pdf", "llm")]

    (c,) = _measure(statements)

    assert (c.survivor_cardinality, c.n_rows) == (1, 3)
    assert c.removable_rows == 2  # 1 nativa sobrevive; a outra nativa + a LLM saem


def test_sobrevivente_native_first_alvo_nunca_e_nativo_quando_nativa_cobre() -> None:
    """card=2 (arquivo LLM viu 2×) e 2 nativas disponíveis ⇒ sobrevivem as 2 nativas
    e AMBOS os alvos são da perna LLM."""
    a, b, llm = _doc(1, "a.pdf"), _doc(1, "b.pdf"), _doc(2, "c.pdf", "llm")

    (c,) = _measure([a, b, llm])

    assert (c.survivor_cardinality, c.removable_rows) == (2, 2)
    assert {t.hash for t in c.removal_targets} == {_row_hash(llm.transactions[0], llm)}


def test_bucket_nativo_excedente_tambem_gera_alvo() -> None:
    """3 nativas de arquivos sobrepostos + 1 LLM, card=1 ⇒ saem 2 nativas + 1 LLM."""
    statements = [_doc(1, "a.pdf"), _doc(1, "b.pdf"), _doc(1, "c.pdf"), _doc(1, "x.pdf", "llm")]

    (c,) = _measure(statements)

    assert (c.survivor_cardinality, c.removable_rows) == (1, 3)
    por_bucket = {t.no_bucket: t.remover for t in c.removal_targets}
    assert por_bucket == {3: 2, 1: 1}  # bucket nativo perde 2; bucket LLM some inteiro
