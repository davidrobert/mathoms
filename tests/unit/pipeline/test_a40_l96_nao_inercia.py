"""Gate de não-inércia da A40.l96: reverter QUALQUER um dos defeitos volta a órfã (ADR-430)."""

# A §Contrafactual da lane mediu que 5 dos 6 subconjuntos próprios não-vazios de
# {D1,D2,D3} são INERTES, e que o sexto — {D1,D3} — é PIOR que inerte: move o
# número publicado sem resolver o problema, e um PR prudente tentaria justamente
# ele. Este gate encoda a tabela: cada perna é revertida em isolamento e a fatia
# órfã tem de voltar. Sem isso, um "fix" parcial sai verde parecendo progresso.

from pipeline.domain.services.account_resolver import AccountResolver
from pipeline.domain.services.atribuicao_de_titularidade import (
    atribuir_por_conta,
    soma_inferida,
)
from pipeline.domain.services.carteira_por_papel import papel_da_chave
from pipeline.domain.services.member_name_resolver import MemberNameResolver
from pipeline.domain.types.config import BankAccountRecord

_TITULAR = "rafael_pereira_souza"
_CONJUGE = "renata_souza"
_FAMILY = {
    "membros": {
        _TITULAR: {"papel": "titular", "nome_curto": "Rafael", "nome_completo": "Rafael P Souza"},
        _CONJUGE: {"papel": "conjuge", "nome_curto": "Renata", "nome_completo": "Renata Souza"},
    }
}

# Forma do corpus de dogfood: 4 instituições singleton com MÚLTIPLAS contas, 1
# com dois donos (ambiguidade real) e 1 sem cadastro (órfã legítima).
_CONTAS_HINT = [
    ("rafael", "bradesco"),
    ("rafael", "bradesco"),
    ("rafael", "caixa"),
    ("rafael", "caixa"),
    ("rafael", "itau"),
    ("rafael", "itau"),
    ("rafael", "rico"),
    ("rafael", "rico"),
    ("rafael", "nubank"),
    ("renata", "nubank"),
    # UMA conta só: resolve por `fallback_bank` mesmo sob o predicado ANTIGO.
    # Sem ela, {D1,D3} sai inerte na fixture e o gate deixa de reproduzir o
    # perigo que a lane nomeia — o subconjunto que MOVE o número publicado sem
    # resolver o problema, e que um PR prudente tentaria primeiro.
    ("rafael", "c6bank"),
]
_POSICOES = [
    {"instituicao": "itau", "valor": 100.0},
    {"instituicao": "rico", "valor": 300.0},
    {"instituicao": "bradesco", "valor": 200.0},
    {"instituicao": "caixa", "valor": 150.0},
    {"instituicao": "c6bank", "valor": 250.0},
    {"instituicao": "binance", "valor": 5.0},  # órfã legítima: sem cadastro
]
_TOTAL = sum(p["valor"] for p in _POSICOES)
_ORFA_LEGITIMA_PCT = 5.0 / _TOTAL * 100


def _nr() -> MemberNameResolver:
    return MemberNameResolver.from_family_config(_FAMILY)


def _rec(member: str, inst: str) -> BankAccountRecord:
    return BankAccountRecord(member_key=member, institution_code=inst, account_type="cc")


def _contas(*, com_d1: bool) -> list[BankAccountRecord]:
    """D1 = o mapa instituição→membro do E1 alcança o resolver do E4."""
    # Chaves CURTAS do artefato E1 de propósito: a canonicalização é o eixo D3
    # e tem de poder ser desligada em separado. A primeira versão deste helper
    # canonicalizava aqui, e o "controle de D3" não controlava nada — {D1,D2}
    # dava 0,66% igual ao fecho (A40.l96 §Gate de não-inércia).
    return [_rec(m, i) for m, i in _CONTAS_HINT] if com_d1 else []


def _pct_orfa(*, com_d1: bool, com_d2: bool, com_d3: bool) -> float:
    resolver = AccountResolver(_contas(com_d1=com_d1))
    if not com_d2:
        resolver = _resolver_predicado_antigo(resolver)
    orfa = 0.0
    for pos in _POSICOES:
        if com_d3:
            membro, _fonte = atribuir_por_conta(
                {}, pos["instituicao"], account_resolver=resolver, name_resolver=_nr()
            )
        else:
            # D3 revertido: a saída do resolver entra CRUA, no espaço de chave
            # curto do LLM — `papel_da_chave('rafael')` contra
            # `titular_key='rafael_pereira_souza'` devolve `sem_dono`.
            membro = resolver.resolve(pos["instituicao"], None).member_key or ""
        papel = papel_da_chave(str(membro).lower(), titular_key=_TITULAR, conjuge_key=_CONJUGE)
        if papel.name == "sem_dono":
            orfa += pos["valor"]
    return round(orfa / _TOTAL * 100, 2)


def _resolver_predicado_antigo(resolver: AccountResolver) -> AccountResolver:
    """D2 revertido: `ambiguous` por CONTAS, sem olhar quantos donos."""
    from pipeline.domain.services.account_resolver import AccountResolution

    class _Antigo(AccountResolver):
        def _from_bank(self, contas_bank):
            if len(contas_bank) == 1:
                c = contas_bank[0]
                return AccountResolution(c.member_key, "fallback_bank", "resolved", c)
            return AccountResolution(None, "ambiguous", "undetermined")

    clone = _Antigo([])
    clone.__dict__.update(resolver.__dict__)
    return clone


def test_fecho_completo_deixa_so_a_orfa_legitima() -> None:
    assert _pct_orfa(com_d1=True, com_d2=True, com_d3=True) == round(_ORFA_LEGITIMA_PCT, 2)


def test_reverter_qualquer_perna_devolve_a_carteira_para_sem_dono() -> None:
    """A tabela dos 8 subconjuntos — nenhum subconjunto próprio resolve."""
    cheio = round(_ORFA_LEGITIMA_PCT, 2)
    subconjuntos = {
        (False, False, False): "vazio (hoje)",
        (True, False, False): "{D1}",
        (False, True, False): "{D2}",
        (False, False, True): "{D3}",
        (True, True, False): "{D1,D2}",
        (True, False, True): "{D1,D3} — o que move o número SEM resolver",
        (False, True, True): "{D2,D3}",
    }
    for (d1, d2, d3), rotulo in subconjuntos.items():
        pct = _pct_orfa(com_d1=d1, com_d2=d2, com_d3=d3)
        assert pct > cheio, f"{rotulo}: órfã {pct}% deveria ser PIOR que o fecho ({cheio}%)"


def test_d1_d3_e_o_subconjunto_perigoso_move_o_numero_sem_resolver() -> None:
    """Ele parece progresso no relatório — é o que o critério de aceite manda barrar."""
    parcial = _pct_orfa(com_d1=True, com_d2=False, com_d3=True)
    nada = _pct_orfa(com_d1=False, com_d2=False, com_d3=False)
    fecho = round(_ORFA_LEGITIMA_PCT, 2)
    assert parcial < nada, "a instituição de conta única resolve mesmo sem D2 — o número MOVE"
    assert parcial > fecho, "e mesmo movendo, não alcança o fecho: o problema continua"


def test_perna_d4_a_provenance_sobrevive_ate_o_agregado() -> None:
    """Sem esta perna o PR sai verde publicando 0% órfã e apagando fato vs hint."""
    resolver = AccountResolver(_contas(com_d1=True))
    dados = []
    for pos in _POSICOES:
        membro, fonte = atribuir_por_conta(
            {}, pos["instituicao"], account_resolver=resolver, name_resolver=_nr()
        )
        dados.append({"valor_atual": pos["valor"], "membro": membro, "atribuicao_fonte": fonte})
    fontes = {d["atribuicao_fonte"] for d in dados}
    assert "banco_unico" in fontes, "atribuição por banco de dono único tem de ser rotulada"
    assert "sem_dono" in fontes, "a órfã legítima continua nomeada"
    assert soma_inferida({"dados": dados}) > 0, "o agregado LÊ a provenance"


def test_fixture_discrimina_as_tres_pernas() -> None:
    """Não-vácuo: se o corpus deixar de exercitar uma perna, os testes acima param de medir."""
    insts = {i for _, i in _CONTAS_HINT}
    donos_por_inst = {i: {m for m, x in _CONTAS_HINT if x == i} for i in insts}
    assert any(
        len(v) == 1 and sum(1 for _, x in _CONTAS_HINT if x == i) > 1
        for i, v in donos_por_inst.items()
    ), "sem singleton multi-conta, D2 é inerte"
    assert any(len(v) >= 2 for v in donos_por_inst.values()), "sem 2 donos, o guard não mede"
    assert any(p["instituicao"] not in insts for p in _POSICOES), "sem órfã legítima, o fecho é 0%"
