"""ADR-226 §3 — Golden multi-membro: 2 contas Itaú David/Mariana resolvem ao membro certo."""

from pipeline.domain.services.account_resolver import AccountResolver
from pipeline.domain.types.config import BankAccountRecord


def _make_resolver_two_itau() -> AccountResolver:
    accounts = (
        BankAccountRecord(
            member_key="david",
            institution_code="itau",
            account_type="extratoconta",
            account_number_norm="123456",
            account_number_raw="12345-6",
        ),
        BankAccountRecord(
            member_key="mariana",
            institution_code="itau",
            account_type="extratoconta",
            account_number_norm="789012",
            account_number_raw="78901-2",
        ),
    )
    return AccountResolver(accounts, banco_membro_legacy={"itau": "mariana"})


def test_two_itau_members_resolve_to_correct_owner() -> None:
    resolver = _make_resolver_two_itau()
    assert resolver.resolve("itau", "12345-6").member_key == "david"
    assert resolver.resolve("itau", "12.345-6").member_key == "david"
    assert resolver.resolve("itau", "123456").member_key == "david"
    assert resolver.resolve("itau", "78901-2").member_key == "mariana"
    assert resolver.resolve("itau", "789012").member_key == "mariana"


def test_ambiguity_when_account_number_missing() -> None:
    resolver = _make_resolver_two_itau()
    res = resolver.resolve("itau", None)
    assert res.confidence == "ambiguous"
    assert res.member_key is None


def test_unknown_account_number_falls_to_ambiguous_when_2_members() -> None:
    """Conta com account_number desconhecido → ambíguo (2 candidatos no banco)."""
    resolver = _make_resolver_two_itau()
    res = resolver.resolve("itau", "999999")
    assert res.confidence == "ambiguous"
