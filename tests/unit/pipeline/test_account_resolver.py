"""Tests do `AccountResolver` puro (ADR-226 §3 · §Emenda 2026-08-31)."""

from pipeline.domain.services.account_resolver import AccountResolver
from pipeline.domain.types.config import BankAccountRecord


def _acc(
    member: str,
    bank: str,
    num: str | None,
    *,
    is_joint: bool = False,
    co_titulares: tuple[str, ...] = (),
) -> BankAccountRecord:
    return BankAccountRecord(
        member_key=member,
        institution_code=bank,
        account_type="extratoconta",
        account_number_norm=num,
        account_number_raw=num,
        is_joint=is_joint,
        co_titulares=co_titulares,
    )


def test_strict_match_by_bank_and_account_number() -> None:
    r = AccountResolver([_acc("david", "itau", "123456"), _acc("mariana", "itau", "789012")])
    res = r.resolve("itau", "12345-6")
    assert res.member_confidence == "strict"
    assert res.member_key == "david"


def test_fallback_bank_single_member() -> None:
    r = AccountResolver([_acc("david", "c6bank", None)])
    res = r.resolve("c6bank", None)
    assert res.member_confidence == "fallback_bank"
    assert res.member_key == "david"


def test_ambiguous_when_two_members_same_bank_no_account_number() -> None:
    r = AccountResolver([_acc("david", "itau", "123456"), _acc("mariana", "itau", "789012")])
    res = r.resolve("itau", None)
    assert res.member_confidence == "ambiguous"
    assert res.member_key is None


def test_unknown_bank_returns_none() -> None:
    r = AccountResolver([_acc("david", "itau", "123456")])
    res = r.resolve("nubank", "111111")
    assert res.member_confidence == "unknown"
    assert res.member_key is None


def test_legacy_banco_membro_used_when_no_accounts_record() -> None:
    r = AccountResolver([], banco_membro_legacy={"itau": "david"})
    res = r.resolve("itau", None)
    assert res.member_confidence == "fallback_bank"
    assert res.member_key == "david"


def test_strict_match_normalizes_account_number() -> None:
    r = AccountResolver([_acc("david", "itau", "123456")])
    for raw in ("12.345-6", "12345-6", "12345/6", "123456"):
        assert r.resolve("itau", raw).member_confidence == "strict"


def test_strict_preferred_over_fallback_when_both_apply() -> None:
    r = AccountResolver([_acc("david", "itau", "123456")])
    res = r.resolve("itau", "12345-6")
    assert res.member_confidence == "strict"
    res2 = r.resolve("itau", None)
    assert res2.member_confidence == "fallback_bank"


def test_two_accounts_same_member_resolves_member_but_not_account() -> None:
    """Titularidade e conta são ortogonais — o resolver responde as duas."""
    # ADR-226 §Emenda 2026-08-31: o antecessor deste teste
    # (test_none_account_number_with_two_same_member_still_ambiguous) NÃO estava
    # errado — protegia uma verdade real (a *conta* não foi identificada) no
    # campo errado. Mantido e re-apontado, não invertido.
    r = AccountResolver([_acc("david", "itau", "123456"), _acc("david", "itau", "789012")])
    res = r.resolve("itau", None)
    assert res.member_confidence == "fallback_bank"
    assert res.member_key == "david"
    assert res.account_confidence == "undetermined"
    assert res.matched_account is None


def test_conta_conjunta_e_ambiguidade_de_titularidade() -> None:
    """Predicado escrito sobre `titulares(conta)`, não sobre `member_key`."""
    # Hoje `is_joint` nunca é populado (V2 reservada na ADR-226 §4); o teste
    # documenta o comportamento para o dia em que for. Sem isto, o predicado
    # `>=2 member_keys` responderia "dono único" a uma conta de dois donos.
    r = AccountResolver([_acc("david", "itau", "123456", is_joint=True, co_titulares=("mariana",))])
    res = r.resolve("itau", None)
    assert res.member_confidence == "ambiguous"
    assert res.member_key is None


def test_account_confidence_resolved_apenas_com_conta_unica() -> None:
    unica = AccountResolver([_acc("david", "c6bank", None)]).resolve("c6bank", None)
    assert unica.account_confidence == "resolved"
    strict = AccountResolver([_acc("david", "itau", "123456")]).resolve("itau", "12345-6")
    assert strict.account_confidence == "resolved"
    legado = AccountResolver([], banco_membro_legacy={"itau": "david"}).resolve("itau", None)
    assert legado.account_confidence == "undetermined", "banco_membro não diz qual conta"


# =============================================================================
# Perna D2 do gate de não-inércia (A40.l96 · ADR-430)
# =============================================================================

# Forma medida do corpus de dogfood em 2026-08-31 (run 79a61e33, 18 contas em 11
# instituições). Chaves de membro neutralizadas; o que importa é a CARDINALIDADE
# de contas e de donos por instituição, que é o que o predicado lê.
_CORPUS: dict[str, tuple[str, ...]] = {
    "bradesco": ("conjuge", "conjuge", "conjuge"),
    "caixa": ("titular", "titular", "titular"),
    "itau": ("titular", "titular"),
    "rico": ("titular", "titular"),
    "nubank": ("titular", "conjuge"),
    "btgpactual": ("conjuge",),
    "c6bank": ("titular",),
    "itausa": ("titular",),
    "picpay": ("titular",),
    "santander": ("titular",),
    "stone": ("titular",),
}
_SINGLETONS_MULTI_CONTA = ("bradesco", "caixa", "itau", "rico")
_AMBIGUIDADE_REAL = ("nubank",)


def _resolver_do_corpus() -> AccountResolver:
    contas = [_acc(dono, inst, None) for inst, donos in _CORPUS.items() for dono in donos]
    return AccountResolver(contas)


def test_corpus_singletons_multi_conta_resolvem_o_dono() -> None:
    """Metade 1: instituição com N contas de UM dono não é 'não sei de quem é'."""
    # Sob o predicado por conta, estas 4 vinham `ambiguous` e a fatia ia para o
    # balde sem-dono do relatório.
    r = _resolver_do_corpus()
    for inst in _SINGLETONS_MULTI_CONTA:
        res = r.resolve(inst, None)
        assert res.member_confidence == "fallback_bank", inst
        assert res.member_key == _CORPUS[inst][0], inst
        assert res.account_confidence == "undetermined", f"{inst}: qual conta segue em aberto"


def test_corpus_ambiguidade_real_sobrevive() -> None:
    """Metade 2 — sem ela o gate fica verde para o 'fix' que apaga o estado."""
    # `ambiguous` tem caso de uso vivo: instituição com contas de DOIS membros.
    # Um PR que resolvesse D2 removendo o estado passaria na metade 1 e
    # quebraria o produto em silêncio.
    r = _resolver_do_corpus()
    for inst in _AMBIGUIDADE_REAL:
        res = r.resolve(inst, None)
        assert res.member_confidence == "ambiguous", inst
        assert res.member_key is None, inst


def test_corpus_discrimina_as_duas_metades() -> None:
    """Não-vácuo: se uma das classes esvaziar, os dois testes acima param de medir."""
    assert _SINGLETONS_MULTI_CONTA, "sem singleton multi-conta o predicado novo é inerte"
    assert _AMBIGUIDADE_REAL, "sem ambiguidade real o gate aceita apagar o estado"
    donos_por_inst = {i: len(set(d)) for i, d in _CORPUS.items()}
    assert all(donos_por_inst[i] == 1 for i in _SINGLETONS_MULTI_CONTA)
    assert all(donos_por_inst[i] >= 2 for i in _AMBIGUIDADE_REAL)
    assert all(
        len(_CORPUS[i]) > 1 for i in _SINGLETONS_MULTI_CONTA
    ), "singleton com 1 conta só já resolvia antes — não discrimina o predicado"


def test_predicado_novo_e_inerte_sem_contas() -> None:
    """Por que D2 pode mergear sozinho: em produção `bank_accounts` tem 0 rows."""
    # Sem contas o resolver nunca alcança o ramo do predicado — devolve
    # `unknown` em toda instituição, exatamente como antes. É o que a
    # §Contrafactual da A40.l96 mediu como {D2} inerte.
    vazio = AccountResolver([])
    for inst in _CORPUS:
        res = vazio.resolve(inst, None)
        assert res.member_confidence == "unknown", inst
        assert res.member_key is None, inst
