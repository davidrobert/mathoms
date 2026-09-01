"""Atribuição de titularidade de posição: quem é o dono, e por qual evidência (ADR-430 §3)."""

from pipeline.domain.services.account_resolver import AccountResolver
from pipeline.domain.services.atribuicao_de_titularidade import (
    atribuir_por_conta,
    canonicalizar_membro,
    soma_inferida,
)
from pipeline.domain.services.carteira_por_papel import papel_da_chave
from pipeline.domain.services.member_name_resolver import MemberNameResolver
from pipeline.domain.types.config import BankAccountRecord

_TITULAR = "rafael_pereira_souza"
_CONJUGE = "renata_souza"
_FAMILY = {
    "membros": {
        _TITULAR: {
            "papel": "titular",
            "nome_curto": "Rafael Pereira",
            "nome_completo": "Rafael Pereira Souza",
        },
        _CONJUGE: {"papel": "conjuge", "nome_curto": "Renata", "nome_completo": "Renata Souza"},
    }
}


def _nr() -> MemberNameResolver:
    return MemberNameResolver.from_family_config(_FAMILY)


def _acc(member: str, bank: str, num: str | None = None) -> BankAccountRecord:
    return BankAccountRecord(
        member_key=member,
        institution_code=bank,
        account_type="extratoconta",
        account_number_norm=num,
        account_number_raw=num,
    )


def test_canonicalizar_leva_chave_curta_do_e1_para_a_canonica() -> None:
    """D3 da A40.l96 — sem isto `papel_da_chave` devolve `sem_dono` para o titular."""
    assert canonicalizar_membro("rafael", _nr()) == _TITULAR
    assert papel_da_chave("rafael", titular_key=_TITULAR, conjuge_key=_CONJUGE).name == "sem_dono"
    assert papel_da_chave(_TITULAR, titular_key=_TITULAR, conjuge_key=_CONJUGE).name == "titular"


def test_canonicalizar_preserva_bruto_quando_nao_casa() -> None:
    # Sem match, preservar o bruto mantém a auditoria; zerar apagaria a evidência.
    assert canonicalizar_membro("zzz", _nr()) == "zzz"
    assert canonicalizar_membro("rafael", None) == "rafael"
    assert canonicalizar_membro("", _nr()) == ""


def test_fonte_distingue_conta_casada_de_banco_unico() -> None:
    """Fato ≠ hint (ADR-394): casar por número de conta não é deduzir do banco."""
    r = AccountResolver([_acc("rafael", "itau", "123456")])
    assert atribuir_por_conta(
        {"numero_conta": "12345-6"}, "itau", account_resolver=r, name_resolver=_nr()
    ) == (
        _TITULAR,
        "conta_casada",
    )
    assert atribuir_por_conta({}, "itau", account_resolver=r, name_resolver=_nr()) == (
        _TITULAR,
        "banco_unico",
    )


def test_fonte_indeterminada_preserva_a_sentinela_da_adr_346() -> None:
    # A sentinela `needs_review` é load-bearing em `_resolved_siblings`
    # (ADR-346 §4b). Matá-la aqui reabriria decisão alheia — ADR-430 §3 Correção.
    r = AccountResolver([_acc("rafael", "nubank"), _acc("renata", "nubank")])
    assert atribuir_por_conta({}, "nubank", account_resolver=r, name_resolver=_nr()) == (
        "needs_review",
        "indeterminada",
    )


def test_fonte_sem_dono_quando_nao_ha_candidato() -> None:
    r = AccountResolver([_acc("rafael", "itau", "123456")])
    assert atribuir_por_conta({}, "xpto", account_resolver=r, name_resolver=_nr()) == (
        "",
        "sem_dono",
    )


def test_soma_inferida_conta_so_o_hint() -> None:
    """O leitor de `atribuicao_fonte` — sem ele o campo nasceria morto (A40.l88)."""
    dados = [
        {"valor_atual": 100.0, "atribuicao_fonte": "banco_unico"},
        {"valor_atual": 50.0, "atribuicao_fonte": "banco_unico"},
        {"valor_atual": 900.0, "atribuicao_fonte": "declarada"},
        {"valor_atual": 700.0, "atribuicao_fonte": "conta_casada"},
        {"valor_atual": 300.0, "atribuicao_fonte": "sem_dono"},
    ]
    assert soma_inferida({"dados": dados}) == 150.0
    assert soma_inferida({"dados": []}) == 0.0
    assert soma_inferida(None) == 0.0


def test_soma_inferida_ignora_posicao_sem_o_campo() -> None:
    # Artefato de run anterior ao ADR-430 não tem o campo; ausência é "não sei",
    # nunca "inferido" — inflaria pct_inferido sobre payload histórico.
    assert soma_inferida({"dados": [{"valor_atual": 100.0}]}) == 0.0


def _resolver_com(nome_curto: str) -> MemberNameResolver:
    return MemberNameResolver.from_family_config(
        {
            "membros": {
                "davi_pereira_souza": {
                    "papel": "titular",
                    "nome_curto": nome_curto,
                    "nome_completo": "Davi Pereira Souza",
                }
            }
        }
    )


def test_limite_medido_chave_curta_abaixo_de_5_chars_nao_resolve() -> None:
    """Limite MEDIDO do remédio de D3 — contrato do resolver, não bug deste módulo."""
    # `MemberNameResolver._MIN_SUBSTRING_LEN` é 5 (ADR-243, para evitar "ana"
    # casar em "fernanda"). Chave curta do E1 com <=4 chars só resolve por match
    # EXATO de `short_name`; caindo no substring devolve o bruto, e
    # `papel_da_chave` do bruto é `sem_dono`. Nomes brasileiros de 4 letras são
    # comuns (Ana, Davi, Luiz, Caio, Nina) — e isto morde também o merge de hint
    # do PR seguinte, que mapeia a chave curta do E1 para a canônica do DB.
    assert canonicalizar_membro("davi", _resolver_com("Davi Pereira")) == "davi"
    assert papel_da_chave("davi", titular_key="davi_pereira_souza", conjuge_key="").name == (
        "sem_dono"
    )
    assert canonicalizar_membro("davi", _resolver_com("Davi")) == "davi_pereira_souza"
