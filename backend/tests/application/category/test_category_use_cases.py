"""Use cases do agregado ``Category`` — testes puros com fakes (sem DB)."""

from __future__ import annotations

import pytest

from backend.app.application.base.errors import ConflictError, NotFoundError
from backend.app.application.category import (
    create_category,
    delete_category,
    list_categories,
    update_category,
)
from backend.app.schemas.dto.category import (
    CategoryCreateCommand,
    CategoryUpdateCommand,
)
from backend.tests.fakes import FakeCategoryRepository


def _create_cmd(**overrides) -> CategoryCreateCommand:
    base = dict(
        code="moradia",
        name="Moradia",
        category_type="expense",
        keywords=["aluguel", "iptu"],
    )
    base.update(overrides)
    return CategoryCreateCommand(**base)


@pytest.mark.asyncio
async def test_create_returns_response_with_keywords():
    repo = FakeCategoryRepository()

    resp = await create_category(_create_cmd(), workspace_id="ws-1", repo=repo)

    assert resp.code == "moradia"
    assert resp.keywords == ["aluguel", "iptu"]


@pytest.mark.asyncio
async def test_create_duplicate_code_raises_conflict():
    repo = FakeCategoryRepository()
    await create_category(_create_cmd(), workspace_id="ws-1", repo=repo)

    with pytest.raises(ConflictError) as exc:
        await create_category(_create_cmd(name="Outra"), workspace_id="ws-1", repo=repo)
    assert exc.value.code == "duplicate_code"


@pytest.mark.asyncio
async def test_create_same_code_different_workspace_ok():
    repo = FakeCategoryRepository()
    await create_category(_create_cmd(), workspace_id="ws-A", repo=repo)
    resp = await create_category(_create_cmd(), workspace_id="ws-B", repo=repo)

    assert resp.code == "moradia"


@pytest.mark.asyncio
async def test_list_returns_workspace_categories():
    repo = FakeCategoryRepository()
    await create_category(_create_cmd(), workspace_id="ws-1", repo=repo)
    await create_category(
        _create_cmd(code="transporte", name="Transporte", keywords=[]),
        workspace_id="ws-1",
        repo=repo,
    )

    resp = await list_categories("ws-1", repo=repo, global_defaults=None)

    assert resp.total == 2
    assert {c.code for c in resp.categories} == {"moradia", "transporte"}


@pytest.mark.asyncio
async def test_list_falls_back_to_global_defaults_when_empty():
    repo = FakeCategoryRepository()
    defaults = {
        "expense_keywords": {"moradia": ["aluguel"]},
        "income_keywords": {"salario": ["salario", "pagamento"]},
    }

    resp = await list_categories("ws-1", repo=repo, global_defaults=defaults)

    assert resp.total == 2
    # Ordem: expense antes, income depois (derivado do mapper).
    codes = [c.code for c in resp.categories]
    assert codes == ["moradia", "salario"]


@pytest.mark.asyncio
async def test_update_partial_preserves_keywords_when_absent():
    repo = FakeCategoryRepository()
    created = await create_category(_create_cmd(), workspace_id="ws-1", repo=repo)

    resp = await update_category(
        created.id,
        CategoryUpdateCommand(name="Moradia Atualizada"),
        workspace_id="ws-1",
        repo=repo,
    )

    assert resp.name == "Moradia Atualizada"
    assert resp.keywords == ["aluguel", "iptu"]  # keywords intactas


@pytest.mark.asyncio
async def test_update_with_empty_keywords_list_clears():
    repo = FakeCategoryRepository()
    created = await create_category(_create_cmd(), workspace_id="ws-1", repo=repo)

    resp = await update_category(
        created.id,
        CategoryUpdateCommand(keywords=[]),
        workspace_id="ws-1",
        repo=repo,
    )

    assert resp.keywords == []


@pytest.mark.asyncio
async def test_update_code_collision_raises_conflict():
    repo = FakeCategoryRepository()
    await create_category(_create_cmd(), workspace_id="ws-1", repo=repo)
    second = await create_category(
        _create_cmd(code="transporte", name="Transporte", keywords=[]),
        workspace_id="ws-1",
        repo=repo,
    )

    with pytest.raises(ConflictError) as exc:
        await update_category(
            second.id,
            CategoryUpdateCommand(code="moradia"),
            workspace_id="ws-1",
            repo=repo,
        )
    assert exc.value.code == "duplicate_code"


@pytest.mark.asyncio
async def test_update_not_found_raises():
    repo = FakeCategoryRepository()

    with pytest.raises(NotFoundError):
        await update_category(
            "missing-id",
            CategoryUpdateCommand(name="X"),
            workspace_id="ws-1",
            repo=repo,
        )


@pytest.mark.asyncio
async def test_delete_not_found_raises():
    repo = FakeCategoryRepository()

    with pytest.raises(NotFoundError):
        await delete_category("missing", workspace_id="ws-1", repo=repo)


@pytest.mark.asyncio
async def test_delete_removes_category():
    repo = FakeCategoryRepository()
    created = await create_category(_create_cmd(), workspace_id="ws-1", repo=repo)

    await delete_category(created.id, workspace_id="ws-1", repo=repo)

    assert await repo.get_by_id("ws-1", created.id) is None


@pytest.mark.asyncio
async def test_delete_other_workspace_raises_not_found():
    repo = FakeCategoryRepository()
    created = await create_category(_create_cmd(), workspace_id="ws-1", repo=repo)

    with pytest.raises(NotFoundError):
        await delete_category(created.id, workspace_id="ws-other", repo=repo)
