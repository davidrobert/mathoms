"""Tests dos helpers ``export_bank_account`` / ``export_member_info`` (ADR-226 PR1)."""

from datetime import date

from backend.app.models.family_member import BankAccount, FamilyMember
from backend.app.services._family_export_helpers import (
    export_bank_account,
    export_member_info,
)


def test_export_bank_account_with_dirty_number_normalizes() -> None:
    acc = BankAccount(
        member_id="m1",
        workspace_id="ws1",
        institution_code="itau",
        account_type="extratoconta",
        agency="1234",
        account_number="12.345-6",
        is_joint=False,
        co_titulares=None,
    )

    exported = export_bank_account(acc, "david")

    assert exported["account_number_raw"] == "12.345-6"
    assert exported["account_number_norm"] == "123456"
    assert exported["member_key"] == "david"
    assert exported["is_joint"] is False
    assert exported["co_titulares"] == []


def test_export_bank_account_handles_null_number() -> None:
    acc = BankAccount(
        member_id="m1",
        workspace_id="ws1",
        institution_code="nubank",
        account_type="faturaunique",
        account_number=None,
    )

    exported = export_bank_account(acc, "mariana")

    assert exported["account_number_raw"] is None
    assert exported["account_number_norm"] is None


def test_export_bank_account_preserves_is_joint_flag() -> None:
    acc = BankAccount(
        member_id="m1",
        workspace_id="ws1",
        institution_code="bradesco",
        account_type="extratoconta",
        is_joint=True,
        co_titulares=["m2", "m3"],
    )

    exported = export_bank_account(acc, "david")

    assert exported["is_joint"] is True
    assert exported["co_titulares"] == ["m2", "m3"]


def test_export_member_info_strips_unknown_keys_into_extra() -> None:
    m = FamilyMember(
        id="m1",
        workspace_id="ws1",
        key="david",
        full_name="David Robert",
        short_name="David",
        role="titular",
        order=0,
        birth_date=date(1990, 1, 1),
        extra={"profissao": "CTO"},
    )

    info = export_member_info(m)

    assert info["nome_completo"] == "David Robert"
    assert info["nome_curto"] == "David"
    assert info["papel"] == "titular"
    assert info["data_nascimento"] == "1990-01-01"
    assert info["profissao"] == "CTO"
