"""Pina o acoplamento `artefato E3 → HashInputs`: o `titular` de **nível-conta** decide
o hash de **toda** transação do artefato.

Instrumento aberto pela avaliação da fusão [[A42]] → [[A40]] (2026-08-05). A A42.l5
reagrupa os grupos do razão *period-free*, o que faz duas pernas da mesma conta caírem
no mesmo grupo; o merge posicional elege **um** `titular` por artefato E3, e é esse
campo que o classificador lê e alimenta no hash de identidade. Consequência: mudança de
agrupamento re-escreve `transaction_hash` **sem tocar a função de hash**, orfanando
override manual do dono (a constraint única deixa de casar).

Nenhuma asserção aqui fixa hash literal — são propriedades relacionais, logo válidas em
v1 e v2 (ADR-278). O que o teste protege é o **mapeamento**, que é o que a A42.l5 muda.

Restrição adjacente, medida em 2026-08-05 e **não** um defeito: o #1200 (ADR-226 PR2)
passou a escrever `titulares` no artefato E3 (`e3_serialization.py:102`, hoje lista de
um, com *"conta conjunta vira 2+ em V2"* declarado), mas a via do hash segue lendo o
`titular` **singular** (`transaction_classifier.py:300`). Quando a conta conjunta render
2+, o hash continuará consumindo um eleito — é este acoplamento, não a lista, que decide
a identidade.

Prova por mutação (2026-08-05) — as duas são necessárias, porque uma asserção de
*ausência* de leitura é insensível à mutação que remove o acoplamento:

- `titular = ""` em `_classify_account_audit` ⇒ morrem 3 dos 4 (todos menos
  `test_titular_por_transacao_e_ignorado`, que segue verde porque a tx continua ignorada);
- `tx.get("titular") or titular` no call-site de `build_hash_inputs` ⇒ morre exatamente
  esse 4º.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.transaction_classifier import (  # noqa: E402
    ClassifierConfig,
    TransactionClassifier,
)

_TXS = [
    {"data": "2026-03-30", "descricao": "Pix recebido", "valor": 100.0},
    {"data": "2026-03-31", "descricao": "Boleto pago", "valor": -250.0},
]


def _classifier() -> TransactionClassifier:
    return TransactionClassifier(ClassifierConfig.from_configs(categorization={}, family={}))


def _account(titular: str | None, transacoes: list[dict] | None = None) -> dict:
    return {
        "banco": "C6Bank",
        "titular": titular,
        "tipo_conta": "extratoconta",
        "moeda": "BRL",
        "transacoes": transacoes if transacoes is not None else _TXS,
    }


def _hashes(titular: str | None, transacoes: list[dict] | None = None) -> list[str]:
    txs = _classifier().classify_account(_account(titular, transacoes))
    return [tx.transaction_hash for tx in txs]


def test_titular_do_artefato_muda_o_hash_de_toda_transacao_da_conta() -> None:
    """Raio de dano é a **conta inteira**, não uma tx — é o mecanismo de orfanamento."""
    alpha, beta = _hashes("titular alpha"), _hashes("titular beta")

    assert len(alpha) == len(beta) == len(_TXS)
    assert set(alpha).isdisjoint(beta), (
        "conjuntos de hash deveriam ser disjuntos: se um dia coincidirem, o titular "
        "saiu dos inputs do hash e esta guarda perdeu o referente"
    )


def test_titular_por_transacao_e_ignorado() -> None:
    """A autoridade é o campo do artefato. Corrigir na tx **não** salva o hash —
    restrição direta sobre o espaço de desenho da A42.l5."""
    com_titular_na_tx = [{**tx, "titular": "titular beta"} for tx in _TXS]

    assert _hashes("titular alpha", com_titular_na_tx) == _hashes("titular alpha")


def test_titular_ausente_e_carrier_e_caixa_nao_e() -> None:
    """Separa o carrier real (string divergente / vazia) do falso (caixa, acento) —
    `normalize_titular` roda dentro do hash. O painel da A40 mediu que confundir os
    dois produz fix no-op que fecha verde."""
    preenchido = _hashes("titular alpha")

    assert set(_hashes("")).isdisjoint(preenchido)
    assert set(_hashes(None)).isdisjoint(preenchido)
    assert _hashes("TITULAR ALPHA") == preenchido
    assert _hashes("  titular alpha  ") == preenchido


def test_merge_de_duas_pernas_com_titular_divergente_reescreve_a_perna_perdedora() -> None:
    """Encena o efeito do merge posicional: eleger o titular da 1ª perna reescreve o
    hash da 2ª. É o que a A42.l5 provoca ao reagrupar period-free."""
    perna_a, perna_b = _hashes("titular alpha"), _hashes("titular beta")
    apos_merge_elegendo_a = _hashes("titular alpha")

    assert apos_merge_elegendo_a == perna_a
    assert set(apos_merge_elegendo_a).isdisjoint(perna_b), (
        "a perna perdedora perde a identidade de todas as suas transações — "
        "override ancorado nelas fica órfão"
    )
