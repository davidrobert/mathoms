"""O card imprime uma contagem ao lado do KPI ([[ADR-420]] §Critério de aceite 5)."""

# Antes do flip o numerador somava cat_2 COMPLETO (5 imóveis no workspace medido) e o
# card imprimia `data.imoveis.length` (4, os de `INVESTMENT_CLASSIFICATIONS`) na MESMA
# frase — um dos dois estava dentro do percentual ao lado sem aparecer na contagem.
#
# O flip fecha isso quase inteiro, e este arquivo mede o "quase": o conjunto do
# numerador é `INVESTMENT_CLASSIFICATIONS ∪ {desconhecido, sem-override}`, então as duas
# cardinalidades coincidem EXATAMENTE quando não há imóvel não-classificado em cat_2 —
# que é o corpus do workspace medido. A divergência remanescente é o §Follow-up de
# regime default da [[A40.l95]], e é ela que este teste NOMEIA em vez de deixar implícita.

from __future__ import annotations

from pipeline.domain.services.patrimonio_imovel_classifier import (
    _CLASSIFICATIONS_FORA_DA_ALOCACAO,
    CLASSIFICATION_COMERCIAL,
    CLASSIFICATION_DESCONHECIDO,
    CLASSIFICATION_ESPECULACAO,
    CLASSIFICATION_LOCADO,
    CLASSIFICATION_NU_PROPRIETARIO,
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    CLASSIFICATION_USO_PESSOAL,
)
from pipeline.domain.services.real_estate_metrics import INVESTMENT_CLASSIFICATIONS

_CAT_2 = frozenset(
    {
        CLASSIFICATION_LOCADO,
        CLASSIFICATION_COMERCIAL,
        CLASSIFICATION_ESPECULACAO,
        CLASSIFICATION_USO_PESSOAL,
        CLASSIFICATION_NU_PROPRIETARIO,
        CLASSIFICATION_DESCONHECIDO,
    }
)


def _conjunto_do_numerador() -> frozenset[str]:
    """O que o numerador soma, derivado do produtor — nunca reescrito à mão aqui."""
    return _CAT_2 - _CLASSIFICATIONS_FORA_DA_ALOCACAO


def test_residencia_nao_esta_em_cat_2():
    """cat_1 fica fora dos dois lados; se entrasse, a paridade abaixo seria falsa."""
    assert CLASSIFICATION_RESIDENCIA_PRINCIPAL not in _CAT_2


def test_o_card_conta_um_SUBCONJUNTO_do_numerador():
    """Contagem maior que o numerador seria pior: imprimiria imóvel fora da razão."""
    assert frozenset(INVESTMENT_CLASSIFICATIONS) <= _conjunto_do_numerador()


def test_a_divergencia_e_EXATAMENTE_o_nao_classificado():
    """Nomeia o resíduo em vez de deixá-lo implícito — é o §Follow-up de regime default."""
    assert _conjunto_do_numerador() - frozenset(INVESTMENT_CLASSIFICATIONS) == {
        CLASSIFICATION_DESCONHECIDO
    }


def test_o_nu_proprietario_saiu_dos_DOIS():
    """O caso que motivou o critério 5: ele somava no numerador e não era contado."""
    assert CLASSIFICATION_NU_PROPRIETARIO not in _conjunto_do_numerador()
    assert CLASSIFICATION_NU_PROPRIETARIO not in INVESTMENT_CLASSIFICATIONS
