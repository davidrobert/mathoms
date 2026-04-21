"""Use case ``update_family_member`` — partial update + derivações."""

from __future__ import annotations

import pytest

from backend.app.application.base.errors import ConflictError, NotFoundError
from backend.app.application.family_member import (
    create_family_member,
    update_family_member,
)
from backend.app.schemas.dto.family_member import (
    FamilyMemberCreateCommand,
    FamilyMemberUpdateCommand,
)
from backend.tests.fakes import FakeFamilyMemberRepository, FakeVault


async def _seed(repo, vault, **extras):
    return await create_family_member(
        FamilyMemberCreateCommand(
            full_name="David", short_name="David", role="titular", **extras
        ),
        workspace_id="ws-1",
        repo=repo,
        vault=vault,
    )


@pytest.mark.asyncio
async def test_update_not_found_raises():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()

    with pytest.raises(NotFoundError):
        await update_family_member(
            "missing-id",
            FamilyMemberUpdateCommand(short_name="Novo"),
            workspace_id="ws-1",
            repo=repo,
            vault=vault,
        )


@pytest.mark.asyncio
async def test_update_partial_preserves_unspecified_fields():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    created = await _seed(repo, vault)

    resp = await update_family_member(
        created.id,
        FamilyMemberUpdateCommand(short_name="Davi"),
        workspace_id="ws-1",
        repo=repo,
        vault=vault,
    )

    assert resp.short_name == "Davi"
    assert resp.full_name == "David"  # inalterado
    assert resp.role == "titular"


@pytest.mark.asyncio
async def test_update_cpf_re_encrypts_via_vault():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    created = await _seed(repo, vault, cpf="12345678901")

    resp = await update_family_member(
        created.id,
        FamilyMemberUpdateCommand(cpf="98765432100"),
        workspace_id="ws-1",
        repo=repo,
        vault=vault,
    )

    stored = await repo.get_by_id("ws-1", created.id)
    assert stored.cpf_encrypted == "enc:98765432100"
    assert resp.cpf == "98765432100"


@pytest.mark.asyncio
async def test_update_birth_name_sets_extra():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    created = await _seed(repo, vault)

    resp = await update_family_member(
        created.id,
        FamilyMemberUpdateCommand(birth_name="Silva"),
        workspace_id="ws-1",
        repo=repo,
        vault=vault,
    )

    assert resp.birth_name == "Silva"
    assert resp.extra == {"nome_nascimento": "Silva"}


@pytest.mark.asyncio
async def test_update_key_collision_raises_conflict():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    first = await _seed(repo, vault)
    second = await create_family_member(
        FamilyMemberCreateCommand(
            key="mariana", full_name="Mariana", short_name="Mari", role="conjuge"
        ),
        workspace_id="ws-1",
        repo=repo,
        vault=vault,
    )

    with pytest.raises(ConflictError) as exc:
        await update_family_member(
            second.id,
            FamilyMemberUpdateCommand(key=first.key),
            workspace_id="ws-1",
            repo=repo,
            vault=vault,
        )
    assert exc.value.code == "duplicate_key"


@pytest.mark.asyncio
async def test_update_same_key_no_conflict():
    repo = FakeFamilyMemberRepository()
    vault = FakeVault()
    created = await _seed(repo, vault)

    # Manda o mesmo key — não deve levantar (exclude_id do próprio).
    resp = await update_family_member(
        created.id,
        FamilyMemberUpdateCommand(key=created.key, short_name="Davi"),
        workspace_id="ws-1",
        repo=repo,
        vault=vault,
    )
    assert resp.key == created.key
