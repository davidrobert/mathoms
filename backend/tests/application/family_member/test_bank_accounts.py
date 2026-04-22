"""Use cases de BankAccount — CRUD com validação de pertença."""

from __future__ import annotations

import pytest

from backend.app.application.base.errors import NotFoundError
from backend.app.application.family_member import (
    create_bank_account,
    create_family_member,
    delete_bank_account,
    list_bank_accounts,
    update_bank_account,
)
from backend.app.schemas.dto.family_member import (
    BankAccountCreateCommand,
    BankAccountUpdateCommand,
    FamilyMemberCreateCommand,
)
from backend.tests.fakes import FakeFamilyMemberRepository, FakeVault


async def _seed_member(repo, vault, workspace_id="ws-1"):
    return await create_family_member(
        FamilyMemberCreateCommand(full_name="David", short_name="David", role="titular"),
        workspace_id=workspace_id,
        repo=repo,
        vault=vault,
    )


@pytest.mark.asyncio
async def test_create_bank_account_404_when_member_missing():
    repo = FakeFamilyMemberRepository()

    with pytest.raises(NotFoundError):
        await create_bank_account(
            "missing-member",
            BankAccountCreateCommand(institution_code="itau", account_type="extratoconta"),
            workspace_id="ws-1",
            repo=repo,
        )


@pytest.mark.asyncio
async def test_create_bank_account_returns_account():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    member = await _seed_member(repo, vault)

    account = await create_bank_account(
        member.id,
        BankAccountCreateCommand(
            institution_code="itau",
            account_type="extratoconta",
            agency="1234",
            label="Conta corrente Itaú",
        ),
        workspace_id="ws-1",
        repo=repo,
    )

    assert account.institution_code == "itau"
    assert account.agency == "1234"


@pytest.mark.asyncio
async def test_list_bank_accounts_isolates_by_workspace():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    m_a = await _seed_member(repo, vault, workspace_id="ws-A")
    await create_bank_account(
        m_a.id,
        BankAccountCreateCommand(institution_code="itau", account_type="x"),
        workspace_id="ws-A",
        repo=repo,
    )

    with pytest.raises(NotFoundError):
        await list_bank_accounts(m_a.id, workspace_id="ws-B", repo=repo)


@pytest.mark.asyncio
async def test_update_bank_account_replace_semantics():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    member = await _seed_member(repo, vault)
    account = await create_bank_account(
        member.id,
        BankAccountCreateCommand(institution_code="itau", account_type="x"),
        workspace_id="ws-1",
        repo=repo,
    )

    updated = await update_bank_account(
        member.id,
        account.id,
        BankAccountUpdateCommand(
            institution_code="c6bank",
            account_type="extratoconta",
            label="C6 PF",
        ),
        workspace_id="ws-1",
        repo=repo,
    )

    assert updated.institution_code == "c6bank"
    assert updated.label == "C6 PF"


@pytest.mark.asyncio
async def test_update_bank_account_404_when_account_not_found():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    member = await _seed_member(repo, vault)

    with pytest.raises(NotFoundError):
        await update_bank_account(
            member.id,
            "missing-acc",
            BankAccountUpdateCommand(institution_code="x", account_type="y"),
            workspace_id="ws-1",
            repo=repo,
        )


@pytest.mark.asyncio
async def test_delete_bank_account_removes_from_repo():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    member = await _seed_member(repo, vault)
    account = await create_bank_account(
        member.id,
        BankAccountCreateCommand(institution_code="itau", account_type="x"),
        workspace_id="ws-1",
        repo=repo,
    )

    await delete_bank_account(member.id, account.id, workspace_id="ws-1", repo=repo)

    assert await repo.get_account(member.id, account.id) is None
