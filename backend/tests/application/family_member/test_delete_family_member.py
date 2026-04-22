"""Use case ``delete_family_member`` — 404 ou cascade de contas."""

from __future__ import annotations

import pytest

from backend.app.application.base.errors import NotFoundError
from backend.app.application.family_member import (
    create_bank_account,
    create_family_member,
    delete_family_member,
)
from backend.app.schemas.dto.family_member import (
    BankAccountCreateCommand,
    FamilyMemberCreateCommand,
)
from backend.tests.fakes import FakeFamilyMemberRepository, FakeVault


@pytest.mark.asyncio
async def test_delete_not_found_raises():
    repo = FakeFamilyMemberRepository()

    with pytest.raises(NotFoundError):
        await delete_family_member("missing", workspace_id="ws-1", repo=repo)


@pytest.mark.asyncio
async def test_delete_removes_member_and_accounts():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    member = await create_family_member(
        FamilyMemberCreateCommand(full_name="David", short_name="David", role="titular"),
        workspace_id="ws-1",
        repo=repo,
        vault=vault,
    )
    await create_bank_account(
        member.id,
        BankAccountCreateCommand(institution_code="itau", account_type="extratoconta"),
        workspace_id="ws-1",
        repo=repo,
    )

    await delete_family_member(member.id, workspace_id="ws-1", repo=repo)

    assert await repo.get_by_id("ws-1", member.id) is None
    assert await repo.list_accounts(member.id) == []


@pytest.mark.asyncio
async def test_delete_other_workspace_raises_not_found():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    member = await create_family_member(
        FamilyMemberCreateCommand(full_name="David", short_name="David", role="titular"),
        workspace_id="ws-1",
        repo=repo,
        vault=vault,
    )

    with pytest.raises(NotFoundError):
        await delete_family_member(member.id, workspace_id="ws-other", repo=repo)
