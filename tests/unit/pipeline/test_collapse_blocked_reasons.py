"""Eixo (6) do §Critério de saída da [[A40.l2]] — os 6 ramos de `blocked_reason`.

Os testes de `test_cross_document_collapser.py` fixam cada cláusula, mas nenhum prova que o
bloqueio veio da cláusula NOMEADA: fixture que já falha em `par_nao_e_nativo_mais_llm` passaria
verde num teste de `banco_conflitante` sem nunca chegar lá. A medição no corpus real deu **0
bloqueados** — 6 de 6 ramos inexercitados em produção —, então o único lugar onde o predicado é
provado é aqui, e ele precisa provar de fato.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models.document import BankStatement  # noqa: E402
from tests.unit.pipeline.test_cross_document_collapser import (  # noqa: E402
    _measure,
    _par_nativo_llm,
    _stmt,
    _tx,
)


# Os testes acima fixam cada cláusula, mas nenhum prova que o bloqueio veio da cláusula
# NOMEADA: uma fixture que já falha em `par_nao_e_nativo_mais_llm` passaria verde num teste
# de `banco_conflitante` sem nunca chegar lá. A medição no corpus real deu **0 bloqueados** —
# 6 de 6 ramos inexercitados em produção —, então o único lugar onde o predicado é provado é
# aqui, e ele precisa provar de fato.
#
# Cada caso parte da MESMA fixture colapsável e muda UMA coisa. O controle negativo é a
# própria base: se ela deixar de colapsar, todos os casos viram vacuidade e o teste diz isso.
def _base_colapsavel() -> list[BankStatement]:
    return _par_nativo_llm()


def _sem_descricao(stmts: list[BankStatement]) -> list[BankStatement]:
    for stmt in stmts:
        stmt.transactions[0] = _tx(descricao="")
    return stmts


def _tres_proveniencias(stmts: list[BankStatement]) -> list[BankStatement]:
    return [*stmts, _stmt(_tx(), tipo_conta="extratoconta", banco="banco exemplo 2")]


def _bancos_conflitantes(stmts: list[BankStatement]) -> list[BankStatement]:
    return [
        _stmt(_tx(), tipo_conta="extratoconta"),
        _stmt(
            _tx(),
            tipo_conta="extrato",
            banco="outro banco",
            titular=None,
            extraction_method="llm",
            saldo_final=None,
        ),
    ]


def _titulares_conflitantes(stmts: list[BankStatement]) -> list[BankStatement]:
    return [
        _stmt(_tx(), tipo_conta="extratoconta"),
        _stmt(
            _tx(),
            tipo_conta="extrato",
            titular="outro titular",
            extraction_method="llm",
            saldo_final=None,
        ),
    ]


# `extratopoupanca`, não `faturaunique`: `_direction` depende do `account_type`, e fatura
# inverteria o sinal — a chave mudaria e o grupo se desfaria antes de chegar ao predicado.
def _tipo_conta_fora(stmts: list[BankStatement]) -> list[BankStatement]:
    return [
        _stmt(_tx(), tipo_conta="extratoconta"),
        _stmt(
            _tx(),
            tipo_conta="extratopoupanca",
            titular=None,
            extraction_method="llm",
            saldo_final=None,
        ),
    ]


def _duas_nativas(stmts: list[BankStatement]) -> list[BankStatement]:
    return [
        _stmt(_tx(), tipo_conta="extratoconta"),
        _stmt(_tx(), tipo_conta="extrato", titular=None, saldo_final=None),
    ]


_BLOQUEIOS = {
    "descricao_vazia": _sem_descricao,
    "proveniencias_diferente_de_duas": _tres_proveniencias,
    "banco_conflitante": _bancos_conflitantes,
    "titular_conflitante": _titulares_conflitantes,
    "tipo_conta_fora_da_allow_list": _tipo_conta_fora,
    "par_nao_e_nativo_mais_llm": _duas_nativas,
}


def test_controle_negativo__a_base_das_mutacoes_colapsa() -> None:
    """Sem isto, os 6 casos abaixo passariam verdes sobre uma fixture já bloqueada."""
    (candidato,) = _measure(_base_colapsavel())

    assert candidato.blocked_reason is None and candidato.collapsible


@pytest.mark.parametrize("reason", sorted(_BLOQUEIOS), ids=sorted(_BLOQUEIOS))
def test_cada_ramo_de_bloqueio_e_alcancado_por_uma_mutacao_isolada(reason: str) -> None:
    """Uma mudança sobre a base colapsável ⇒ exatamente aquele `blocked_reason`."""
    candidatos = _measure(_BLOQUEIOS[reason](_base_colapsavel()))

    assert candidatos, "mutação matou o agrupamento — nada a bloquear é diferente de bloquear"
    assert [c.blocked_reason for c in candidatos] == [reason]


def _campos_iterados(fn: ast.FunctionDef) -> list[str]:
    """Literais do `for name in (...)` que prefixam o f-string de `{name}_conflitante`."""
    for node in ast.walk(fn):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple):
            return [e.value for e in node.iter.elts if isinstance(e, ast.Constant)]
    return []


def _reason_do_return(node: ast.Return, fn: ast.FunctionDef) -> set[str]:
    """Literal do `return`; f-string expande sobre os campos do `for` que a envolve."""
    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
        return {node.value.value}
    if not isinstance(node.value, ast.JoinedStr):
        return set()
    sufixo = "".join(v.value for v in node.value.values if isinstance(v, ast.Constant))
    return {f"{campo}{sufixo}" for campo in _campos_iterados(fn)}


def _reasons_de(fn: ast.FunctionDef) -> set[str]:
    returns = (n for n in ast.walk(fn) if isinstance(n, ast.Return))
    return set().union(*(_reason_do_return(n, fn) for n in returns), set())


# Sem a exaustividade o eixo (6) mede "6 dos 6 que eu lembrei", não "6 dos 6 que existem".
def test_os_ramos_testados_sao_TODOS_os_que_o_predicado_emite() -> None:
    """AST, não grep: ramo novo em `_blocked_reason` sem caso aqui deixa isto vermelho."""
    fonte = (
        Path(__file__).resolve().parents[3] / "pipeline/domain/services/cross_document_collapser.py"
    )
    arvore = ast.parse(fonte.read_text(encoding="utf-8"))
    fns = {n.name: n for n in ast.walk(arvore) if isinstance(n, ast.FunctionDef)}
    emitidos = _reasons_de(fns["_blocked_reason"]) | _reasons_de(fns["_extraction_reason"])

    assert emitidos == set(_BLOQUEIOS), "ramo de bloqueio sem mutação que o alcance"
