"""Núcleo do harness de estabilidade da [[A42.l15]] (`dev/measure_e15_identity_stability.py`)."""

# Fixtures SINTÉTICAS — payload E1.5a real carrega descrição de ativo, CPF e valor, e
# CLAUDE.md proíbe isso em fixture. A casca de I/O (DB + Fernet) fica no CLI; o que decide
# o veredito é puro e está aqui.
#
# Os três estados são o ponto: a 1ª execução real do harness colapsava `sem investimento`
# em `controle moveu`, e o operador lia falha de controle onde não havia nada a medir.

from __future__ import annotations

import pytest

from dev.measure_e15_identity_stability import (
    K_MINIMO,
    avaliar_grupo,
    controles_que_moveram,
    era_do_payload,
    identity_set,
    medir,
)


def _item(**over) -> dict:
    base = {
        "codigo": "41",
        "descricao": "CDB BANCO EXEMPLO",
        "categoria_hint": "investimento",
        "secao": "bens_direitos",
        "valor_brl": "1000.00",
        "membro": "m1",
        "ano": 2024,
    }
    return {**base, **over}


def _payload(itens: list[dict] | None = None, **over) -> dict:
    corpo = itens if itens is not None else [_item()]
    base = {
        "payload_version": 2,
        "prompt_version": "1.3.0",
        "itens": corpo,
        "resumo": {
            "total_ativos": "1000.00",
            "total_passivos": "0.00",
            "patrimonio_liquido": "1000.00",
            "ano_referencia": 2024,
            "membros": ["m1"],
        },
    }
    return {**base, **over}


def _grupo(payloads: list[dict]):
    return avaliar_grupo("doc", "1.3.0", payloads)


def test_era_vem_do_payload_e_ausencia_vira_null() -> None:
    assert era_do_payload(_payload()) == "1.3.0"
    assert era_do_payload(_payload(prompt_version=None)) == "NULL"


def test_identidade_muda_quando_a_descricao_muda() -> None:
    """É a hipótese da lane — sem esta sensibilidade o harness não mede nada."""
    a = identity_set(_payload())
    b = identity_set(_payload([_item(descricao="CDB BANCO EXEMPLO S/A")]))
    assert a and b and a != b


def test_amostras_identicas_dao_estabilidade_total() -> None:
    grupo = _grupo([_payload() for _ in range(K_MINIMO)])
    assert grupo.valido and grupo.estabilidade_pct == 100.0


def test_descricao_que_churna_derruba_a_estabilidade() -> None:
    variantes = [_payload([_item(descricao=f"CDB BANCO EXEMPLO {i}")]) for i in range(K_MINIMO)]
    grupo = _grupo(variantes)
    assert grupo.valido and grupo.estabilidade_pct == 0.0
    assert grupo.uniao > 0, "sem união o resultado seria N/A, não 0%"


@pytest.mark.parametrize("controle", ["secao", "categoria_hint"])
def test_controle_negativo_que_se_move_INVALIDA_o_grupo(controle: str) -> None:
    """O número é SUPRIMIDO, não anotado — `estabilidade_pct` devolve `None`."""
    outro = {"secao": "dividas_onus", "categoria_hint": "imovel"}[controle]
    grupo = _grupo([_payload()] * (K_MINIMO - 1) + [_payload([_item(**{controle: outro})])])
    assert controle in grupo.controles_que_moveram
    assert not grupo.valido
    assert grupo.estabilidade_pct is None


def test_documento_sem_investimento_e_NA_e_nao_falha_de_controle() -> None:
    """Terceiro estado: `aplicavel=False` sem nenhum controle ter se movido."""
    vazio = [_payload([_item(categoria_hint="imovel", codigo="11")]) for _ in range(K_MINIMO)]
    grupo = _grupo(vazio)
    assert not grupo.aplicavel
    assert grupo.controles_que_moveram == (), "sem investimento NÃO é controle movido"
    assert grupo.estabilidade_pct is None


def test_cardinalidade_media_expoe_o_100_por_cento_trivial() -> None:
    """100% sobre 1 id não é 100% sobre 17 — medido no corpus real, e engana sem isto."""
    um = _grupo([_payload() for _ in range(K_MINIMO)])
    dois = _grupo([_payload([_item(), _item(descricao="LCI OUTRO")]) for _ in range(K_MINIMO)])
    assert um.cardinalidade_media == 1.0
    assert dois.cardinalidade_media == 2.0
    assert um.estabilidade_pct == dois.estabilidade_pct == 100.0


def test_pares_byte_identicos_sao_contados_suspeita_de_cache() -> None:
    """§Armadilha D: `use_cache=True` numa linha leva a estabilidade a ~100% sem consertar nada."""
    assert _grupo([_payload() for _ in range(K_MINIMO)]).pares_byte_identicos == 10
    variados = [_payload([_item(descricao=f"CDB {i}")]) for i in range(K_MINIMO)]
    assert _grupo(variados).pares_byte_identicos == 0


def test_grupo_abaixo_de_K_e_excluido_E_contado() -> None:
    """Truncagem silenciosa lê como cobertura — o excluído precisa aparecer no rodapé."""
    poucos = [("doc-curto", _payload()) for _ in range(K_MINIMO - 1)]
    bastantes = [("doc-longo", _payload()) for _ in range(K_MINIMO)]
    corrida = medir(poucos + bastantes)
    assert corrida.excluidos_por_k == 1
    assert [g.documento for g in corrida.grupos] == ["doc-longo"]


def test_eras_diferentes_nao_se_misturam_no_mesmo_grupo() -> None:
    """Agrupar por era é o que impede comparar vocabulário velho com novo."""
    mistura = [("doc", _payload(prompt_version="1.2.0")) for _ in range(K_MINIMO)]
    mistura += [("doc", _payload(prompt_version="1.3.0")) for _ in range(K_MINIMO)]
    corrida = medir(mistura)
    assert sorted(g.era for g in corrida.grupos) == ["1.2.0", "1.3.0"]


def test_controles_que_moveram_e_multiset_nao_ordem() -> None:
    """Ordem dos itens não é sinal; contagem é."""
    a = _payload([_item(descricao="X"), _item(descricao="Y", categoria_hint="imovel")])
    b = _payload([_item(descricao="Y", categoria_hint="imovel"), _item(descricao="X")])
    assert controles_que_moveram([a, b]) == ()
