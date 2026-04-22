"""Use case ``create_family_member`` — testes puros com fakes (sem DB)."""

from __future__ import annotations

import pytest

from backend.app.application.base.errors import ConflictError
from backend.app.application.family_member import create_family_member
from backend.app.schemas.dto.family_member import FamilyMemberCreateCommand
from backend.tests.fakes import FakeFamilyMemberRepository, FakeVault


def _cmd(**overrides) -> FamilyMemberCreateCommand:
    base = dict(
        full_name="David Roberto",
        short_name="David",
        role="titular",
    )
    base.update(overrides)
    return FamilyMemberCreateCommand(**base)


@pytest.mark.asyncio
async def test_create_allocates_slug_when_key_missing():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()

    resp = await create_family_member(_cmd(), workspace_id="ws-1", repo=repo, vault=vault)

    assert resp.key == "david_roberto"
    assert resp.full_name == "David Roberto"
    assert resp.accounts == []


@pytest.mark.asyncio
async def test_create_uses_explicit_key_when_provided():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()

    resp = await create_family_member(
        _cmd(key="david"), workspace_id="ws-1", repo=repo, vault=vault
    )

    assert resp.key == "david"


@pytest.mark.asyncio
async def test_create_conflict_on_duplicate_explicit_key():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    await create_family_member(_cmd(key="david"), workspace_id="ws-1", repo=repo, vault=vault)

    with pytest.raises(ConflictError) as exc:
        await create_family_member(
            _cmd(key="david", full_name="David 2"),
            workspace_id="ws-1",
            repo=repo,
            vault=vault,
        )
    assert exc.value.code == "duplicate_key"


@pytest.mark.asyncio
async def test_create_auto_suffixes_slug_on_collision():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    await create_family_member(_cmd(), workspace_id="ws-1", repo=repo, vault=vault)
    resp = await create_family_member(_cmd(), workspace_id="ws-1", repo=repo, vault=vault)

    assert resp.key == "david_roberto_1"


@pytest.mark.asyncio
async def test_create_encrypts_cpf_via_vault():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()

    resp = await create_family_member(
        _cmd(cpf="12345678901"),
        workspace_id="ws-1",
        repo=repo,
        vault=vault,
    )

    member_id = resp.id
    assert member_id is not None
    stored = await repo.get_by_id("ws-1", member_id)
    assert stored is not None
    assert stored.cpf_encrypted == "enc:12345678901"
    assert resp.cpf == "12345678901"  # response decripta


@pytest.mark.asyncio
async def test_create_places_birth_name_in_extra():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()

    resp = await create_family_member(
        _cmd(birth_name="Silva"),
        workspace_id="ws-1",
        repo=repo,
        vault=vault,
    )

    assert resp.birth_name == "Silva"
    assert resp.extra == {"nome_nascimento": "Silva"}


@pytest.mark.asyncio
async def test_create_isolates_by_workspace():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    await create_family_member(_cmd(key="david"), workspace_id="ws-1", repo=repo, vault=vault)
    resp = await create_family_member(
        _cmd(key="david"), workspace_id="ws-2", repo=repo, vault=vault
    )

    assert resp.key == "david"  # mesmo key, outro workspace → ok
