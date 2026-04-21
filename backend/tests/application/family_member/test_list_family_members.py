"""Use case ``list_family_members`` — fallback a defaults quando workspace vazio."""

from __future__ import annotations

import pytest

from backend.app.application.family_member import (
    create_family_member,
    list_family_members,
)
from backend.app.schemas.dto.family_member import FamilyMemberCreateCommand
from backend.tests.fakes import FakeFamilyMemberRepository, FakeVault


@pytest.mark.asyncio
async def test_list_returns_workspace_members_when_present():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    await create_family_member(
        FamilyMemberCreateCommand(
            full_name="David", short_name="David", role="titular"
        ),
        workspace_id="ws-1",
        repo=repo,
        vault=vault,
    )

    resp = await list_family_members(
        "ws-1", repo=repo, vault=vault, global_defaults=None
    )

    assert resp.total == 1
    assert resp.members[0].key == "david"


@pytest.mark.asyncio
async def test_list_falls_back_to_global_defaults_when_empty():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    defaults = {
        "membros": {
            "titular_exemplo": {"papel": "titular"},
            "conjuge_exemplo": {"papel": "conjuge"},
        }
    }

    resp = await list_family_members(
        "ws-1", repo=repo, vault=vault, global_defaults=defaults
    )

    assert resp.total == 2
    # F6.5E.6: fallback usa placeholders neutros.
    assert all(m.cpf is None for m in resp.members)
    assert all("Exemplo" in m.full_name for m in resp.members)


@pytest.mark.asyncio
async def test_list_returns_empty_when_no_workspace_and_no_defaults():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()

    resp = await list_family_members(
        "ws-1", repo=repo, vault=vault, global_defaults=None
    )

    assert resp.total == 0
    assert resp.members == []
