"""Classe D±1 ([[A40.l102]]) — contabilidade da proximidade, e a ausência de alvo.

O par publicado no dogfood não era "mesma data, dois pares" como o LEDGER dizia:
é UM par, `2025-10-26` em `extratoconta` e `2025-10-27` em `extrato`, mesmo banco,
mesmo valor, documentos-fonte distintos, e AMBAS as pernas nativas. Cada teste aqui
fixa uma cláusula do recorte — e o contrafactual de cada uma foi medido: mudar a
janela de 1 para 3 dias, remover a guarda de ≥2 proveniências, remover a de ≥2
datas ou não rodar a passada no `collapse()` derruba exatamente um teste cada.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models.document import BankStatement  # noqa: E402
from pipeline.domain.services.cross_document_collapser import (  # noqa: E402
    CrossDocumentCollapser,
    OverrideRetentionGuard,
)

from .test_cross_document_collapser import _stmt, _tx  # noqa: E402

_D26 = date(2025, 10, 26)
_D27 = date(2025, 10, 27)


def _par_d1(descricao: str = "pagamento pix", dia_b: date = _D27) -> list[BankStatement]:
    """Duas pernas NATIVAS, mesmo banco, `extrato` vs `extratoconta`, D e D+1."""
    return [
        _stmt(_tx(dia=_D26, descricao=descricao), tipo_conta="extratoconta"),
        _stmt(_tx(dia=dia_b, descricao=descricao), tipo_conta="extrato"),
    ]


def _mede(stmts):
    collapser = CrossDocumentCollapser(retention_guard=OverrideRetentionGuard.sem_overrides())
    return collapser.measure(stmts)


def test_par_d1_vira_candidato_contavel_com_blocked_reason():
    medicao = _mede(_par_d1())
    assert len(medicao.proximidade_d1) == 1
    candidato = medicao.proximidade_d1[0]
    assert candidato.blocked_reason == "proximidade_d1"
    assert candidato.datas == ("2025-10-26", "2025-10-27")
    assert candidato.delta_dias == 1
    assert candidato.n_rows == 2
    assert candidato.n_provenances == 2


def test_o_par_d1_continua_fora_da_passada_principal():
    """A chave day-exact não o alcança — é o motivo de a classe precisar de passada própria."""
    medicao = _mede(_par_d1())
    assert medicao.candidates == ()


def test_medir_d1_nao_remove_row_nenhuma():
    """Measure-first: a classe é contável e o corpo do razão não se move."""
    stmts = _par_d1()
    antes = [[t.to_dict() for t in s.transactions] for s in stmts]
    collapser = CrossDocumentCollapser(retention_guard=OverrideRetentionGuard.sem_overrides())
    depois_stmts, medicao, removals = collapser.collapse(stmts)
    assert medicao.proximidade_d1  # a classe foi medida...
    assert removals == ()  # ...e nada foi publicado no canal de remoção
    assert [[t.to_dict() for t in s.transactions] for s in depois_stmts] == antes


def test_a_janela_discrimina_o_que_esta_fora_dela():
    """Anti-vacuidade: sem esta asserção o candidato acima poderia sair de qualquer par."""
    assert _mede(_par_d1(dia_b=date(2025, 10, 29))).proximidade_d1 == ()


def test_descricao_diferente_nao_e_a_mesma_classe():
    """O eixo da classe é SÓ a data — divergir na descrição a tira do grupo."""
    stmts = [
        _stmt(_tx(dia=_D26, descricao="pagamento pix"), tipo_conta="extratoconta"),
        _stmt(_tx(dia=_D27, descricao="tarifa mensal"), tipo_conta="extrato"),
    ]
    assert _mede(stmts).proximidade_d1 == ()


def test_repeticao_dentro_da_mesma_proveniencia_nao_conta():
    """Classe da [[A42.l5]], não desta: `_group_by_key` também exige ≥2 proveniências."""
    stmts = [
        _stmt(
            _tx(dia=_D26, descricao="pagamento pix"),
            _tx(dia=_D27, descricao="pagamento pix"),
            tipo_conta="extratoconta",
        )
    ]
    assert _mede(stmts).proximidade_d1 == ()


def test_data_unica_fica_com_a_passada_principal():
    """Mesmo dia em duas proveniências é candidato de COLAPSO, não de proximidade."""
    medicao = _mede(_par_d1(dia_b=_D26))
    assert medicao.proximidade_d1 == ()
    assert len(medicao.candidates) == 1
