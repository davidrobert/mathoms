"""Casamento chave↔texto por token — A40.l69 item 3b ([[ADR-394]] §Emenda (b) D8).

`titular_key in nome` casa DENTRO de nome alheio. O eixo do teste é a colisão que
a substring produz e o token não.
"""

from __future__ import annotations

import pytest

from pipeline.domain.services.member_key_matcher import matches_member_key, tokens
from pipeline.domain.services.patrimonio_resolvers import resolve_members
from pipeline.domain.services.patrimonio_types import MemberIdentity


# Cada par aqui casava por substring e é pessoa diferente. É a classe inteira.
@pytest.mark.parametrize(
    ("chave", "nome"),
    [
        ("ana", "Mariana Souza"),
        ("luis", "Luisa Prado"),
        ("marco", "Marcos Antonio"),
        ("rita", "Margarita Lopes"),
        ("ana", "Joana Lima"),
    ],
)
def test_chave_dentro_de_nome_alheio_nao_casa(chave: str, nome: str) -> None:
    assert chave in nome.lower(), "guard: o par tem de casar por substring, senão não prova nada"
    assert not matches_member_key(chave, nome)


@pytest.mark.parametrize(
    ("chave", "nome"),
    [
        ("david", "David Robert Silva"),
        ("david", "DAVID ROBERT"),
        ("joao", "João da Silva"),
        ("joão", "Joao da Silva"),
        ("mariana", "Mariana Souza"),
        ("david_robert", "David Robert Silva"),
        ("maria clara", "Maria Clara Prado"),
    ],
)
def test_token_legitimo_segue_casando(chave: str, nome: str) -> None:
    """O caso que o baseline em lista-de-dicts usa para resolver membro."""
    assert matches_member_key(chave, nome)


def test_chave_vazia_nunca_casa() -> None:
    """Família de 1 titular tem `conjuge_key=''` — casar tudo seria pior que nada."""
    assert not matches_member_key("", "David Robert Silva")
    assert not matches_member_key(None, "David Robert Silva")
    assert not matches_member_key("david", "")


def test_tokens_normaliza_acento_e_pontuacao() -> None:
    assert tokens("João D'Ávila-Souza") == ("joao", "d", "avila", "souza")


def test_resolve_members_nao_troca_pessoa_por_colisao_de_slug() -> None:
    """Ponta a ponta: o cônjuge deixa de ser resolvido pela chave do titular."""
    identity = MemberIdentity(
        titular_key="ana", conjuge_key="mariana", titular_nome="Ana", conjuge_nome="Mariana"
    )
    baseline = {
        "members": [
            {"nome": "Mariana Souza", "total_bens": 200},
            {"nome": "Ana Prado", "total_bens": 100},
        ]
    }

    titular, conjuge = resolve_members(baseline, identity)

    assert titular.get("nome") == "Ana Prado", "substring dava 'Mariana Souza' aqui"
    assert conjuge.get("nome") == "Mariana Souza"


def test_resolve_members_preserva_o_caso_legitimo() -> None:
    """Guard anti-vacuidade: match exato de string devolveria None para os dois."""
    identity = MemberIdentity(
        titular_key="david", conjuge_key="mariana", titular_nome="D", conjuge_nome="M"
    )
    baseline = {"members": [{"nome": "David Robert Silva"}, {"nome": "Mariana Souza"}]}

    titular, conjuge = resolve_members(baseline, identity)

    assert titular["nome"] == "David Robert Silva"
    assert conjuge["nome"] == "Mariana Souza"


# =============================================================================
# Posse exclusiva — o predicado que decide dívida/imóvel do cônjuge
# =============================================================================


def test_exclusividade_recusa_texto_que_nomeia_os_dois() -> None:
    """P5: `"David e Mariana"` não é posse exclusiva de ninguém."""
    from pipeline.domain.services.member_key_matcher import matches_member_exclusively

    assert not matches_member_exclusively("mariana", "david", "David e Mariana Souza")


def test_exclusividade_aceita_texto_que_nomeia_so_um() -> None:
    from pipeline.domain.services.member_key_matcher import matches_member_exclusively

    assert matches_member_exclusively("mariana", "david", "Mariana Souza")
    assert not matches_member_exclusively("mariana", "david", "David Robert")


def test_exclusividade_com_chave_vazia_e_falsa() -> None:
    """Família de 1 titular: `conjuge_key=''` não possui nada exclusivamente."""
    from pipeline.domain.services.member_key_matcher import matches_member_exclusively

    assert not matches_member_exclusively("", "david", "Qualquer Coisa")
