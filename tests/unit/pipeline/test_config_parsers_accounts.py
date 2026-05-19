"""Tests do parser ``parse_family_members`` para contas[] aditivo (ADR-226 §2)."""

from pipeline.adapters.config_parsers import parse_family_members


def _conta(member_key: str, raw: str, norm: str) -> dict:
    return {
        "member_key": member_key,
        "institution_code": "itau",
        "account_type": "extratoconta",
        "account_number_raw": raw,
        "account_number_norm": norm,
    }


_TWO_ITAU_MEMBERS = {
    "membros": {
        "david": {"nome_completo": "David", "nome_curto": "David", "papel": "titular"},
        "mariana": {"nome_completo": "Mariana", "nome_curto": "Mariana", "papel": "conjuge"},
    },
    "banco_membro": {"itau": "mariana"},
    "contas": [_conta("david", "12345-6", "123456"), _conta("mariana", "78901-2", "789012")],
}


def test_parses_contas_array() -> None:
    cfg = parse_family_members(_TWO_ITAU_MEMBERS)
    assert len(cfg.accounts) == 2
    by_member = {a.member_key: a for a in cfg.accounts}
    assert by_member["david"].account_number_norm == "123456"
    assert by_member["mariana"].account_number_norm == "789012"


def test_falls_back_when_contas_absent() -> None:
    data = {
        "membros": {"david": {"papel": "titular", "nome_completo": "D", "nome_curto": "D"}},
        "banco_membro": {"itau": "david"},
    }

    cfg = parse_family_members(data)

    assert cfg.accounts == ()
    assert cfg.bank_to_member == {"itau": "david"}


def test_normalizes_account_number_when_only_raw_given() -> None:
    data = {
        "membros": {"d": {"papel": "titular", "nome_completo": "D", "nome_curto": "D"}},
        "contas": [
            {
                "member_key": "d",
                "institution_code": "itau",
                "account_type": "extratoconta",
                "account_number": "55.667-7",
            }
        ],
    }

    cfg = parse_family_members(data)

    assert len(cfg.accounts) == 1
    assert cfg.accounts[0].account_number_norm == "556677"
    assert cfg.accounts[0].account_number_raw == "55.667-7"
