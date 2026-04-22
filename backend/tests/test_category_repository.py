"""Testes unitários do CategoryRepository (com DB real).

Usam as fixtures ``db`` / ``setup_db`` de conftest.py (SQLite in-memory com
schema recriado por teste). Cobrem:

- list/get/code_exists com isolamento por workspace (R13)
- create/update/delete + cascade de CategoryKeyword
- exclude_id em code_exists para unicidade em updates
- replace_keywords (semântica ``keywords=None|[]|lista``)
- delete_all_in_workspace (usado pelo import)
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.category import CategoryKeyword
from backend.app.repositories.category_repository import CategoryRepository
from backend.tests.factories.builders import make_workspace


@pytest_asyncio.fixture
async def workspace_ids(db: AsyncSession) -> tuple[str, str]:
    """Cria 2 workspaces para validar isolation multi-tenant."""
    ws_a = await make_workspace(db, name="WS A")
    ws_b = await make_workspace(db, name="WS B")
    await db.commit()
    return ws_a.id, ws_b.id


@pytest.mark.asyncio
async def test_create_and_get_by_id(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = CategoryRepository(db)

    created = await repo.create(
        ws_id,
        code="moradia",
        name="Moradia",
        category_type="expense",
        keywords=["aluguel", "iptu"],
    )

    assert created.id is not None
    assert created.code == "moradia"
    # Repo devolve agregado hidratado com keywords eager. Ordem é por UUID
    # (relationship order_by=CategoryKeyword.id), não por inserção.
    assert {kw.keyword for kw in created.keywords} == {"aluguel", "iptu"}

    fetched = await repo.get_by_id(ws_id, created.id)
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_list_by_workspace_is_isolated(db: AsyncSession, workspace_ids):
    ws_a, ws_b = workspace_ids
    repo = CategoryRepository(db)

    await repo.create(ws_a, code="moradia", name="Moradia", category_type="expense")
    await repo.create(ws_a, code="transporte", name="Transporte", category_type="expense")
    await repo.create(ws_b, code="moradia", name="Moradia", category_type="expense")

    cats_a = await repo.list_by_workspace(ws_a)
    cats_b = await repo.list_by_workspace(ws_b)

    assert {c.code for c in cats_a} == {"moradia", "transporte"}
    assert {c.code for c in cats_b} == {"moradia"}


@pytest.mark.asyncio
async def test_list_orders_by_order_then_code(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = CategoryRepository(db)

    await repo.create(ws_id, code="zeta", name="Z", category_type="expense", order=2)
    await repo.create(ws_id, code="alpha", name="A", category_type="expense", order=0)
    await repo.create(ws_id, code="beta", name="B", category_type="expense", order=0)

    cats = await repo.list_by_workspace(ws_id)

    # order=0 vem primeiro; empate desempata por code asc.
    assert [c.code for c in cats] == ["alpha", "beta", "zeta"]


@pytest.mark.asyncio
async def test_code_exists_scoped_to_workspace(db: AsyncSession, workspace_ids):
    ws_a, ws_b = workspace_ids
    repo = CategoryRepository(db)

    await repo.create(ws_a, code="shared", name="S", category_type="expense")

    assert await repo.code_exists(ws_a, "shared") is True
    # mesmo code em outro workspace → não colide (isolation multi-tenant)
    assert await repo.code_exists(ws_b, "shared") is False


@pytest.mark.asyncio
async def test_code_exists_with_exclude_id(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = CategoryRepository(db)

    c1 = await repo.create(ws_id, code="c1", name="C1", category_type="expense")
    c2 = await repo.create(ws_id, code="c2", name="C2", category_type="expense")

    # c1.code existe no ws, mas excluindo ele mesmo: não existe (simula
    # update que mantém a chave atual).
    assert await repo.code_exists(ws_id, "c1", exclude_id=c1.id) is False
    # excluir outra categoria preserva a colisão
    assert await repo.code_exists(ws_id, "c1", exclude_id=c2.id) is True


@pytest.mark.asyncio
async def test_get_by_code(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = CategoryRepository(db)
    created = await repo.create(ws_id, code="moradia", name="Moradia", category_type="expense")

    fetched = await repo.get_by_code(ws_id, "moradia")
    assert fetched is not None
    assert fetched.id == created.id

    assert await repo.get_by_code(ws_id, "inexistente") is None


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_cross_workspace(db: AsyncSession, workspace_ids):
    ws_a, ws_b = workspace_ids
    repo = CategoryRepository(db)

    cat = await repo.create(ws_a, code="x", name="X", category_type="expense")

    # Consulta com workspace errado retorna None (invariante multi-tenant).
    assert await repo.get_by_id(ws_b, cat.id) is None


@pytest.mark.asyncio
async def test_get_by_id_with_keywords_eager_loads(db: AsyncSession, workspace_ids):
    """Garantia do invariante: repo retorna agregado com keywords eager."""
    ws_id, _ = workspace_ids
    repo = CategoryRepository(db)
    created = await repo.create(
        ws_id,
        code="lazer",
        name="Lazer",
        category_type="expense",
        keywords=["cinema", "restaurante"],
    )

    fetched = await repo.get_by_id_with_keywords(ws_id, created.id)

    assert fetched is not None
    # Acesso a .keywords fora de async context funciona só se for eager.
    assert {kw.keyword for kw in fetched.keywords} == {
        "cinema",
        "restaurante",
    }


@pytest.mark.asyncio
async def test_update_mutates_fields_and_preserves_keywords(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = CategoryRepository(db)
    cat = await repo.create(
        ws_id,
        code="x",
        name="Old",
        category_type="expense",
        keywords=["a", "b"],
    )

    updated = await repo.update(cat, updates={"name": "New", "order": 5}, keywords=None)

    assert updated.name == "New"
    assert updated.order == 5
    assert updated.code == "x"  # inalterado
    # keywords=None → não altera a lista
    assert {kw.keyword for kw in updated.keywords} == {"a", "b"}


@pytest.mark.asyncio
async def test_update_empty_keywords_clears_all(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = CategoryRepository(db)
    cat = await repo.create(
        ws_id,
        code="x",
        name="X",
        category_type="expense",
        keywords=["a", "b", "c"],
    )

    updated = await repo.update(cat, updates={}, keywords=[])

    # keywords=[] → apaga todas
    assert updated.keywords == []


@pytest.mark.asyncio
async def test_update_replaces_keyword_list(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = CategoryRepository(db)
    cat = await repo.create(
        ws_id,
        code="x",
        name="X",
        category_type="expense",
        keywords=["antigo1", "antigo2"],
    )

    updated = await repo.update(cat, updates={}, keywords=["novo1", "novo2", "novo3"])

    assert {kw.keyword for kw in updated.keywords} == {
        "novo1",
        "novo2",
        "novo3",
    }


@pytest.mark.asyncio
async def test_delete_cascades_to_keywords(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = CategoryRepository(db)
    cat = await repo.create(
        ws_id,
        code="moradia",
        name="Moradia",
        category_type="expense",
        keywords=["aluguel", "iptu"],
    )

    # Keywords presentes antes do delete
    kws_before = (
        (await db.execute(select(CategoryKeyword).where(CategoryKeyword.category_id == cat.id)))
        .scalars()
        .all()
    )
    assert len(kws_before) == 2

    await repo.delete(cat)

    # Categoria sumiu
    assert await repo.get_by_id(ws_id, cat.id) is None
    # Keywords também foram apagadas (delete explícito no repo, não confia
    # em ondelete='CASCADE' do SQLite em testes)
    kws_after = (
        (await db.execute(select(CategoryKeyword).where(CategoryKeyword.category_id == cat.id)))
        .scalars()
        .all()
    )
    assert kws_after == []


@pytest.mark.asyncio
async def test_replace_keywords_without_commit(db: AsyncSession, workspace_ids):
    """``replace_keywords`` não faz commit — caller é responsável.

    A ordem das keywords vem do ``order_by=CategoryKeyword.id`` no
    relationship (UUIDs) — não é ordem de inserção. Usa set para checar
    conteúdo.
    """
    ws_id, _ = workspace_ids
    repo = CategoryRepository(db)
    cat = await repo.create(
        ws_id,
        code="x",
        name="X",
        category_type="expense",
        keywords=["old1", "old2"],
    )

    await repo.replace_keywords(cat, ["new1", "new2", "new3"])
    await db.commit()

    # Relê fresh para garantir que persistiu.
    fetched = await repo.get_by_id_with_keywords(ws_id, cat.id)
    assert {kw.keyword for kw in fetched.keywords} == {
        "new1",
        "new2",
        "new3",
    }


@pytest.mark.asyncio
async def test_delete_all_in_workspace(db: AsyncSession, workspace_ids):
    ws_a, ws_b = workspace_ids
    repo = CategoryRepository(db)

    await repo.create(ws_a, code="a1", name="A1", category_type="expense", keywords=["x"])
    await repo.create(ws_a, code="a2", name="A2", category_type="income")
    await repo.create(ws_b, code="b1", name="B1", category_type="expense")

    count = await repo.delete_all_in_workspace(ws_a)
    await db.commit()  # método usa flush — caller faz o commit.

    assert count == 2
    assert await repo.list_by_workspace(ws_a) == []
    # Outro workspace intacto
    cats_b = await repo.list_by_workspace(ws_b)
    assert len(cats_b) == 1
