"""Tests do `AccountResolver` puro (ADR-226 §3)."""

from pipeline.domain.services.account_resolver import AccountResolver
from pipeline.domain.types.config import BankAccountRecord


def _acc(member: str, bank: str, num: str | None) -> BankAccountRecord:
    return BankAccountRecord(
        member_key=member,
        institution_code=bank,
        account_type="extratoconta",
        account_number_norm=num,
        account_number_raw=num,
    )


def test_strict_match_by_bank_and_account_number() -> None:
    r = AccountResolver([_acc("david", "itau", "123456"), _acc("mariana", "itau", "789012")])
    res = r.resolve("itau", "12345-6")
    assert res.confidence == "strict"
    assert res.member_key == "david"


def test_fallback_bank_single_member() -> None:
    r = AccountResolver([_acc("david", "c6bank", None)])
    res = r.resolve("c6bank", None)
    assert res.confidence == "fallback_bank"
    assert res.member_key == "david"


def test_ambiguous_when_two_members_same_bank_no_account_number() -> None:
    r = AccountResolver([_acc("david", "itau", "123456"), _acc("mariana", "itau", "789012")])
    res = r.resolve("itau", None)
    assert res.confidence == "ambiguous"
    assert res.member_key is None


def test_unknown_bank_returns_none() -> None:
    r = AccountResolver([_acc("david", "itau", "123456")])
    res = r.resolve("nubank", "111111")
    assert res.confidence == "unknown"
    assert res.member_key is None


def test_legacy_banco_membro_used_when_no_accounts_record() -> None:
    r = AccountResolver([], banco_membro_legacy={"itau": "david"})
    res = r.resolve("itau", None)
    assert res.confidence == "fallback_bank"
    assert res.member_key == "david"


def test_strict_match_normalizes_account_number() -> None:
    r = AccountResolver([_acc("david", "itau", "123456")])
    for raw in ("12.345-6", "12345-6", "12345/6", "123456"):
        assert r.resolve("itau", raw).confidence == "strict"


def test_strict_preferred_over_fallback_when_both_apply() -> None:
    r = AccountResolver([_acc("david", "itau", "123456")])
    res = r.resolve("itau", "12345-6")
    assert res.confidence == "strict"
    res2 = r.resolve("itau", None)
    assert res2.confidence == "fallback_bank"


def test_none_account_number_with_two_same_member_still_ambiguous() -> None:
    r = AccountResolver([_acc("david", "itau", "123456"), _acc("david", "itau", "789012")])
    res = r.resolve("itau", None)
    assert res.confidence == "ambiguous"
