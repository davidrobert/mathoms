"""Testes unitários do FamilyMemberRepository (com DB real).

Usam as fixtures `db` / `setup_db` de conftest.py (SQLite in-memory com
schema recriado por teste). Cobrem:

- list/get/key_exists com isolamento por workspace (R13)
- create/update/delete + cascade de BankAccount
- exclude_id em key_exists para unicidade em updates
- BankAccount CRUD como sub-entidade
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.family_member_repository import FamilyMemberRepository
from backend.tests.factories.builders import make_workspace


@pytest_asyncio.fixture
async def workspace_ids(db: AsyncSession) -> tuple[str, str]:
    """Cria 2 workspaces (cada um com owner próprio) p/ validar isolation."""
    ws_a = await make_workspace(db, name="WS A")
    ws_b = await make_workspace(db, name="WS B")
    await db.commit()
    return ws_a.id, ws_b.id


@pytest.mark.asyncio
async def test_create_and_get_by_id(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = FamilyMemberRepository(db)

    created = await repo.create(
        ws_id,
        key="david",
        full_name="David R.",
        short_name="David",
        role="titular",
    )

    assert created.id is not None
    assert created.key == "david"
    assert created.accounts == []  # agregado hidratado com lista vazia

    fetched = await repo.get_by_id(ws_id, created.id)
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_list_by_workspace_is_isolated(db: AsyncSession, workspace_ids):
    ws_a, ws_b = workspace_ids
    repo = FamilyMemberRepository(db)

    await repo.create(ws_a, key="a1", full_name="A One", short_name="A1", role="titular")
    await repo.create(ws_a, key="a2", full_name="A Two", short_name="A2", role="conjuge")
    await repo.create(ws_b, key="b1", full_name="B One", short_name="B1", role="titular")

    members_a = await repo.list_by_workspace(ws_a)
    members_b = await repo.list_by_workspace(ws_b)

    assert {m.key for m in members_a} == {"a1", "a2"}
    assert {m.key for m in members_b} == {"b1"}


@pytest.mark.asyncio
async def test_list_orders_by_order_then_key(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = FamilyMemberRepository(db)

    await repo.create(ws_id, key="zeta", full_name="Z", short_name="Z", role="titular", order=2)
    await repo.create(ws_id, key="alpha", full_name="A", short_name="A", role="titular", order=0)
    await repo.create(ws_id, key="beta", full_name="B", short_name="B", role="titular", order=0)

    members = await repo.list_by_workspace(ws_id)

    # order=0 vem primeiro; empate desempata por key asc.
    assert [m.key for m in members] == ["alpha", "beta", "zeta"]


@pytest.mark.asyncio
async def test_key_exists_scoped_to_workspace(db: AsyncSession, workspace_ids):
    ws_a, ws_b = workspace_ids
    repo = FamilyMemberRepository(db)

    await repo.create(ws_a, key="shared", full_name="A", short_name="A", role="titular")

    assert await repo.key_exists(ws_a, "shared") is True
    # mesma key em outro workspace → não colide (é isolation multi-tenant)
    assert await repo.key_exists(ws_b, "shared") is False


@pytest.mark.asyncio
async def test_key_exists_with_exclude_id(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = FamilyMemberRepository(db)

    m1 = await repo.create(ws_id, key="k1", full_name="M1", short_name="M1", role="titular")
    m2 = await repo.create(ws_id, key="k2", full_name="M2", short_name="M2", role="conjuge")

    # m1.key exists globalmente no ws, mas excluindo ele mesmo: não existe
    # (simula update que não muda a chave)
    assert await repo.key_exists(ws_id, "k1", exclude_id=m1.id) is False
    # excluir outro membro preserva a colisão
    assert await repo.key_exists(ws_id, "k1", exclude_id=m2.id) is True


@pytest.mark.asyncio
async def test_update_mutates_fields(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = FamilyMemberRepository(db)

    m = await repo.create(ws_id, key="x", full_name="Old", short_name="O", role="titular")

    updated = await repo.update(m, updates={"full_name": "New", "order": 5})

    assert updated.full_name == "New"
    assert updated.order == 5
    assert updated.key == "x"  # inalterado


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_cross_workspace(db: AsyncSession, workspace_ids):
    ws_a, ws_b = workspace_ids
    repo = FamilyMemberRepository(db)

    m = await repo.create(ws_a, key="x", full_name="X", short_name="X", role="titular")

    # Consulta com workspace errado deve retornar None (multi-tenant invariant).
    assert await repo.get_by_id(ws_b, m.id) is None


@pytest.mark.asyncio
async def test_delete_cascades_to_accounts(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = FamilyMemberRepository(db)
    m = await repo.create(ws_id, key="acc_owner", full_name="A", short_name="A", role="titular")
    common = {"workspace_id": ws_id, "account_type": "extratoconta"}
    await repo.add_account(m.id, institution_code="itau", **common)
    await repo.add_account(m.id, institution_code="c6bank", **common)
    assert len(await repo.list_accounts(m.id)) == 2
    await repo.delete(m)
    assert await repo.get_by_id(ws_id, m.id) is None
    assert await repo.list_accounts(m.id) == []


@pytest.mark.asyncio
async def test_add_and_update_account(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = FamilyMemberRepository(db)
    m = await repo.create(ws_id, key="owner", full_name="O", short_name="O", role="titular")
    acc = await repo.add_account(
        m.id,
        workspace_id=ws_id,
        institution_code="itau",
        account_type="extratoconta",
        agency="0001",
    )
    assert acc.institution_code == "itau"
    updated = await repo.update_account(
        acc,
        institution_code="c6bank",
        account_type="faturaunique",
        agency="0002",
        account_number="12345",
        label="Principal",
    )
    assert updated.institution_code == "c6bank"
    assert updated.agency == "0002"
    assert updated.label == "Principal"


@pytest.mark.asyncio
async def test_get_account_is_scoped_to_member(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = FamilyMemberRepository(db)
    m_a = await repo.create(ws_id, key="a", full_name="A", short_name="A", role="titular")
    m_b = await repo.create(ws_id, key="b", full_name="B", short_name="B", role="conjuge")

    acc_a = await repo.add_account(
        m_a.id, workspace_id=ws_id, institution_code="itau", account_type="extratoconta"
    )

    assert await repo.get_account(m_a.id, acc_a.id) is not None
    # buscar com outro member_id → não encontra (isolamento)
    assert await repo.get_account(m_b.id, acc_a.id) is None


@pytest.mark.asyncio
async def test_get_by_id_with_accounts_eager_loads(db: AsyncSession, workspace_ids):
    """Garantia do invariante: repo não retorna instância sem accounts carregadas."""
    ws_id, _ = workspace_ids
    repo = FamilyMemberRepository(db)
    m = await repo.create(ws_id, key="eager", full_name="E", short_name="E", role="titular")
    await repo.add_account(
        m.id, workspace_id=ws_id, institution_code="itau", account_type="extratoconta"
    )

    fetched = await repo.get_by_id_with_accounts(ws_id, m.id)
    assert fetched is not None
    # Acessar .accounts fora de async context funciona se estiver eager.
    assert len(fetched.accounts) == 1
    assert fetched.accounts[0].institution_code == "itau"


@pytest.mark.asyncio
async def test_get_by_key_returns_member(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = FamilyMemberRepository(db)
    m = await repo.create(ws_id, key="maria", full_name="M", short_name="M", role="titular")

    fetched = await repo.get_by_key(ws_id, "maria")
    assert fetched is not None
    assert fetched.id == m.id

    # chave inexistente
    assert await repo.get_by_key(ws_id, "nobody") is None


@pytest.mark.asyncio
async def test_delete_all_in_workspace(db: AsyncSession, workspace_ids):
    ws_a, ws_b = workspace_ids
    repo = FamilyMemberRepository(db)

    await repo.create(ws_a, key="a1", full_name="A1", short_name="A1", role="titular")
    await repo.create(ws_a, key="a2", full_name="A2", short_name="A2", role="conjuge")
    await repo.create(ws_b, key="b1", full_name="B1", short_name="B1", role="titular")

    count = await repo.delete_all_in_workspace(ws_a)
    await db.commit()  # delete_all usa flush; commit pra persistir

    assert count == 2
    assert await repo.list_by_workspace(ws_a) == []
    # outro workspace intacto
    members_b = await repo.list_by_workspace(ws_b)
    assert len(members_b) == 1
