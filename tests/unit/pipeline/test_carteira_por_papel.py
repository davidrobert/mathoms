"""A40.l80 PR2 C1 ([[ADR-412]] §D3): o produtor único do eixo de posições.

Cada teste nomeia a mutação que ele mata. Asserção de **partição por item**, nunca
de soma: a soma fecha em 0,00% *sobre* o defeito que esta lane corrige — foi por
isso que a §Corretude da lane passou verde durante meses.
"""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.bases_financeiras import PapelMembro, chave_de_componente
from pipeline.domain.services.carteira_por_papel import (
    CarteiraPorPapel,
    build_carteira_por_papel,
    papel_da_chave,
)

_TITULAR, _CONJUGE = "alex", "bia"


def _carteira(dados: list[dict], totais: dict | None = None) -> CarteiraPorPapel:
    return build_carteira_por_papel(
        {"dados": dados, "total_por_membro": totais or {}},
        titular_key=_TITULAR,
        conjuge_key=_CONJUGE,
    )


# Mata: tirar `sem_dono` do domínio do loop. A fixture tem fatia órfã > 0 de
# propósito — com órfã zero o teste seria vacuoso, e o enum não trava sozinho
# (não há mypy/pyright em gate; [[ADR-412]] §Emenda E7).
def test_papel_membro_e_exaustivo_no_produtor():
    carteira = _carteira([{"membro": "", "valor": 100}, {"membro": _TITULAR, "valor": 50}])
    assert set(carteira.baldes) == set(PapelMembro)
    assert carteira[PapelMembro.sem_dono].total_brl > 0 or carteira[PapelMembro.sem_dono].posicoes


# Mata: reinstalar `elif not membro → titular` (reserva_liquidez.py:189-190).
def test_chave_vazia_nao_e_do_titular_nos_dois_graos():
    carteira = _carteira([{"membro": "", "valor": 100}], totais={"": 120, _TITULAR: 50})
    assert carteira[PapelMembro.sem_dono].posicoes
    assert carteira[PapelMembro.titular].posicoes == ()
    assert carteira[PapelMembro.sem_dono].total_brl == Decimal("120")
    assert carteira[PapelMembro.titular].total_brl == Decimal("50")


# Mata: descartar a posição. Hoje ela some — `membro` não-vazio não dispara o
# `elif`, e `member_key in "needs_review"` é False: não entra em liquido nem em
# excluido, embora o valor esteja em `patrimonio.investimentos_nao_atribuidos`.
def test_posicao_needs_review_entra_em_sem_dono_e_nao_some():
    carteira = _carteira([{"membro": "needs_review", "valor": 7}])
    assert len(carteira[PapelMembro.sem_dono].posicoes) == 1
    assert carteira[PapelMembro.titular].posicoes == ()


# Mata: trocar `matches_member_key` por `key in texto`. O gate
# `dev/check_member_key_substring.py` é cego aqui — classifica pelo NOME da
# variável, e neste módulo ela não se chama `*_key`.
def test_substring_nao_atribui():
    assert papel_da_chave("mariana", titular_key="alex", conjuge_key="ana") is PapelMembro.sem_dono
    assert papel_da_chave("alexandre", titular_key="alex", conjuge_key="") is PapelMembro.sem_dono


# Mata: derivar `total_brl` de `sum(posicoes)` — o atalho que "fecha a soma" e
# apaga o resíduo não-detalhado que o consolidador já avisa.
def test_divergencia_item_vs_agregado_e_nomeada():
    carteira = _carteira([{"membro": "", "valor": 100}], totais={"": 120})
    balde = carteira[PapelMembro.sem_dono]
    assert balde.soma_itens_brl == Decimal("100")
    assert balde.total_brl == Decimal("120")
    assert balde.divergencia_item_vs_agregado == Decimal("20")
    assert carteira.divergencia_total == Decimal("20")


# Mata: montar a chave por f-string sobre o enum — vira
# `investimentos_PapelMembro.sem_dono` e o `$def` fechado rejeita os três baldes.
def test_chave_publicada_nunca_vem_de_fstring():
    for papel in PapelMembro:
        balde = CarteiraPorPapel.vazia()[papel]
        assert balde.chave_publicada == chave_de_componente(papel)
        assert "PapelMembro" not in balde.chave_publicada


def test_carteira_vazia_tem_os_tres_papeis():
    vazia = CarteiraPorPapel.vazia()
    assert set(vazia.baldes) == set(PapelMembro)
    assert vazia.total_brl == Decimal("0")
    assert build_carteira_por_papel(None, titular_key=_TITULAR, conjuge_key=_CONJUGE).total_brl == 0


def test_atribuido_deriva_das_chaves_do_agregado():
    carteira = _carteira([], totais={_TITULAR: 50})
    assert carteira[PapelMembro.titular].atribuido is True
    assert carteira[PapelMembro.conjuge].atribuido is False
