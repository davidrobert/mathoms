"""Testes unitários do ConfigBlobRepository (com DB real).

Usam ``db`` / ``setup_db`` de conftest.py (SQLite in-memory, schema recriado
por teste). Repo é paramétrico — o mesmo método ``get/upsert/delete`` atende
``PipelineConfig``, ``InstitutionConfig`` e ``ReportLayout``. Os testes
cobrem:

- Isolamento por workspace (R13): queries por ``workspace_id``.
- Isolamento por tipo: 3 modelos ocupam tabelas separadas — upsert em um
  não vaza para outro.
- Semântica de upsert: cria quando não existe, substitui ``config_json``
  inteiro quando existe (não faz merge).
- ``get_config_json``: atalho que só retorna o dict.
- ``delete`` idempotente: ``False`` quando nada para apagar.
- Caller é dono do commit — repo só faz flush.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.config_blob import (
    InstitutionConfig,
    PipelineConfig,
    ReportLayout,
)
from backend.app.repositories.config_blob_repository import ConfigBlobRepository
from backend.tests.factories.builders import make_workspace


@pytest_asyncio.fixture
async def workspace_ids(db: AsyncSession) -> tuple[str, str]:
    """2 workspaces para validar isolation multi-tenant."""
    ws_a = await make_workspace(db, name="WS A")
    ws_b = await make_workspace(db, name="WS B")
    await db.commit()
    return ws_a.id, ws_b.id


# ─── get / get_config_json ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_returns_none_when_no_blob(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = ConfigBlobRepository(db)

    # Nenhum dos 3 blobs criado ainda — get retorna None.
    assert await repo.get(ws_id, PipelineConfig) is None
    assert await repo.get(ws_id, InstitutionConfig) is None
    assert await repo.get(ws_id, ReportLayout) is None


@pytest.mark.asyncio
async def test_get_config_json_returns_none_when_no_blob(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = ConfigBlobRepository(db)
    assert await repo.get_config_json(ws_id, PipelineConfig) is None


# ─── upsert: create ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_creates_pipeline_blob(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = ConfigBlobRepository(db)

    cfg_dict = {"llm": {"model": "claude-opus-4.7", "max_tokens": 8000}}
    created = await repo.upsert(ws_id, PipelineConfig, cfg_dict)
    await db.commit()

    assert created.id is not None
    assert created.workspace_id == ws_id
    assert created.config_json == cfg_dict

    # Relê fresh para garantir que persistiu no DB.
    fetched = await repo.get(ws_id, PipelineConfig)
    assert fetched is not None
    assert fetched.config_json == cfg_dict


@pytest.mark.asyncio
async def test_upsert_creates_institution_blob(db: AsyncSession, workspace_ids):
    """Mesmo repo paramétrico atende outro modelo — semântica idêntica."""
    ws_id, _ = workspace_ids
    repo = ConfigBlobRepository(db)

    cfg = {"c6bank": {"doc_type_patterns": {"extratoconta": "_"}}}
    await repo.upsert(ws_id, InstitutionConfig, cfg)
    await db.commit()

    fetched = await repo.get(ws_id, InstitutionConfig)
    assert fetched is not None
    assert fetched.config_json == cfg


@pytest.mark.asyncio
async def test_upsert_creates_report_layout_blob(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = ConfigBlobRepository(db)

    cfg = {"sections": [{"id": "cover", "enabled": True}]}
    await repo.upsert(ws_id, ReportLayout, cfg)
    await db.commit()

    fetched = await repo.get(ws_id, ReportLayout)
    assert fetched is not None
    assert fetched.config_json == cfg


# ─── upsert: update ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_replaces_existing_config_json_fully(db: AsyncSession, workspace_ids):
    """Upsert NÃO faz merge — substitui o ``config_json`` inteiro.

    Merge é responsabilidade do caller (``deep_merge`` no mapper).
    """
    ws_id, _ = workspace_ids
    repo = ConfigBlobRepository(db)

    await repo.upsert(
        ws_id,
        PipelineConfig,
        {"llm": {"model": "old", "max_tokens": 500}},
    )
    await db.commit()

    # Upsert com shape diferente — substituição total.
    await repo.upsert(ws_id, PipelineConfig, {"qa_thresholds": {"score_diff_max": 0.5}})
    await db.commit()

    fetched = await repo.get(ws_id, PipelineConfig)
    assert fetched is not None
    # llm sumiu; só o que está no último upsert persiste.
    assert fetched.config_json == {"qa_thresholds": {"score_diff_max": 0.5}}


@pytest.mark.asyncio
async def test_upsert_preserves_id_on_update(db: AsyncSession, workspace_ids):
    """Update mantém o mesmo PK — não deleta+insere."""
    ws_id, _ = workspace_ids
    repo = ConfigBlobRepository(db)

    first = await repo.upsert(ws_id, PipelineConfig, {"a": 1})
    await db.commit()
    original_id = first.id

    second = await repo.upsert(ws_id, PipelineConfig, {"b": 2})
    await db.commit()

    assert second.id == original_id


# ─── Isolation: por workspace (R13) ───────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_isolated_across_workspaces(db: AsyncSession, workspace_ids):
    """Unique index em workspace_id permite uma linha por ws por tipo."""
    ws_a, ws_b = workspace_ids
    repo = ConfigBlobRepository(db)

    await repo.upsert(ws_a, PipelineConfig, {"model": "a"})
    await repo.upsert(ws_b, PipelineConfig, {"model": "b"})
    await db.commit()

    cfg_a = await repo.get(ws_a, PipelineConfig)
    cfg_b = await repo.get(ws_b, PipelineConfig)

    assert cfg_a is not None and cfg_a.config_json == {"model": "a"}
    assert cfg_b is not None and cfg_b.config_json == {"model": "b"}


@pytest.mark.asyncio
async def test_get_returns_none_for_other_workspace(db: AsyncSession, workspace_ids):
    ws_a, ws_b = workspace_ids
    repo = ConfigBlobRepository(db)

    await repo.upsert(ws_a, PipelineConfig, {"x": 1})
    await db.commit()

    # ws_b não tem blob — invariante multi-tenant.
    assert await repo.get(ws_b, PipelineConfig) is None


# ─── Isolation: por tipo de blob ──────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_isolated_across_blob_types(db: AsyncSession, workspace_ids):
    """3 modelos vivem em tabelas separadas — upsert em um não escreve
    em outro."""
    ws_id, _ = workspace_ids
    repo = ConfigBlobRepository(db)

    await repo.upsert(ws_id, PipelineConfig, {"kind": "pipeline"})
    await repo.upsert(ws_id, InstitutionConfig, {"kind": "institution"})
    await repo.upsert(ws_id, ReportLayout, {"kind": "layout"})
    await db.commit()

    pipe = await repo.get(ws_id, PipelineConfig)
    inst = await repo.get(ws_id, InstitutionConfig)
    lay = await repo.get(ws_id, ReportLayout)

    assert pipe.config_json == {"kind": "pipeline"}
    assert inst.config_json == {"kind": "institution"}
    assert lay.config_json == {"kind": "layout"}


# ─── get_config_json atalho ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_config_json_returns_dict(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = ConfigBlobRepository(db)

    await repo.upsert(ws_id, PipelineConfig, {"a": 1, "b": {"c": 2}})
    await db.commit()

    cfg = await repo.get_config_json(ws_id, PipelineConfig)
    assert cfg == {"a": 1, "b": {"c": 2}}


# ─── delete ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_returns_true_when_deleted(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = ConfigBlobRepository(db)

    await repo.upsert(ws_id, PipelineConfig, {"x": 1})
    await db.commit()

    assert await repo.delete(ws_id, PipelineConfig) is True
    await db.commit()

    # Depois do delete, get retorna None.
    assert await repo.get(ws_id, PipelineConfig) is None


@pytest.mark.asyncio
async def test_delete_returns_false_when_nothing_to_delete(db: AsyncSession, workspace_ids):
    """Delete é idempotente: sem linha para apagar, retorna ``False``."""
    ws_id, _ = workspace_ids
    repo = ConfigBlobRepository(db)

    assert await repo.delete(ws_id, PipelineConfig) is False


@pytest.mark.asyncio
async def test_delete_scoped_to_workspace(db: AsyncSession, workspace_ids):
    """Delete em ws_a não toca no blob do ws_b (invariante multi-tenant)."""
    ws_a, ws_b = workspace_ids
    repo = ConfigBlobRepository(db)

    await repo.upsert(ws_a, PipelineConfig, {"x": "a"})
    await repo.upsert(ws_b, PipelineConfig, {"x": "b"})
    await db.commit()

    assert await repo.delete(ws_a, PipelineConfig) is True
    await db.commit()

    assert await repo.get(ws_a, PipelineConfig) is None
    # ws_b intacto
    cfg_b = await repo.get(ws_b, PipelineConfig)
    assert cfg_b is not None
    assert cfg_b.config_json == {"x": "b"}


@pytest.mark.asyncio
async def test_delete_scoped_to_blob_type(db: AsyncSession, workspace_ids):
    """Delete de PipelineConfig não toca em InstitutionConfig."""
    ws_id, _ = workspace_ids
    repo = ConfigBlobRepository(db)

    await repo.upsert(ws_id, PipelineConfig, {"kind": "pipeline"})
    await repo.upsert(ws_id, InstitutionConfig, {"kind": "institution"})
    await db.commit()

    await repo.delete(ws_id, PipelineConfig)
    await db.commit()

    assert await repo.get(ws_id, PipelineConfig) is None
    # Institution intacto.
    inst = await repo.get(ws_id, InstitutionConfig)
    assert inst is not None
    assert inst.config_json == {"kind": "institution"}


# ─── Transações: caller é dono do commit ──────────────────────────────


@pytest.mark.asyncio
async def test_upsert_does_not_commit(db: AsyncSession, workspace_ids):
    """Repo faz ``flush`` (para id estar disponível), mas NÃO ``commit``.

    Se o caller não commitar, rollback apaga o blob.
    """
    ws_id, _ = workspace_ids
    repo = ConfigBlobRepository(db)

    created = await repo.upsert(ws_id, PipelineConfig, {"x": 1})
    # id foi atribuído pelo flush.
    assert created.id is not None

    await db.rollback()

    # Depois do rollback, o blob não existe.
    assert await repo.get(ws_id, PipelineConfig) is None
