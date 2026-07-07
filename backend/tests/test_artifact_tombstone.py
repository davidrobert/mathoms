"""Tests — tombstone de artifacts E2* na reclassificação (A32.l5, ADR-311).

Cobre o service (`artifact_tombstone`), o hook do bulk reclassify e a
regressão fim-a-fim do cenário do dogfood 2026-07-07: doc `cdbdetalhes`
reclassificado para informe (`doc_type=informe_rendimentos_anuais`) deixava
o artifact E2-llm órfão envenenando o E3 a cada run.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Document, PipelineArtifact, PipelineRun, PipelineRunStatus
from backend.app.models.document import DocumentType
from backend.app.services.artifact_tombstone import (
    e2_tombstone_stage_names,
    tombstone_e2_artifacts_for_document,
)
from backend.app.services.document_reclassify_bulk_service import (
    _tombstone_if_extraction_changed,
)
from backend.tests.factories import make_document, make_workspace

_HASH_A = "aaaaaaaaaaaa" + "0" * 52
_HASH_B = "bbbbbbbbbbbb" + "0" * 52


async def _seed_run(db: AsyncSession, workspace_id: str) -> str:
    run = PipelineRun(workspace_id=workspace_id, status=PipelineRunStatus.running)
    db.add(run)
    await db.flush()
    return run.id


async def _seed_ws_doc_run(db: AsyncSession, **doc_kwargs) -> tuple:
    """(workspace, document, run_id) — documento com content_hash A por default."""
    ws = await make_workspace(db)
    doc = await make_document(db, workspace=ws, content_hash=_HASH_A, **doc_kwargs)
    run_id = await _seed_run(db, ws.id)
    return ws, doc, run_id


def _artifact(
    ws_id: str, run_id: str, *, stage: str, key: str, document_id: str | None = None
) -> PipelineArtifact:
    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage=stage,
        artifact_key=key,
        document_id=document_id,
        content_json={"synthetic": True},
    )


async def _remaining_keys(db: AsyncSession) -> set[tuple[str, str]]:
    rows = (await db.execute(select(PipelineArtifact.stage, PipelineArtifact.artifact_key))).all()
    return {(r[0], r[1]) for r in rows}


async def _tombstone_doc(db: AsyncSession, ws_id: str, doc) -> int:
    return await tombstone_e2_artifacts_for_document(
        db, workspace_id=ws_id, document_id=doc.id, content_hash=doc.content_hash
    )


def test_stage_names_cover_legacy_and_descriptive_forms():
    names = set(e2_tombstone_stage_names())
    assert {"E2", "E2-llm", "extract_with_llm", "E2-extratos", "extract_statements"} <= names
    assert {"E2-faturas", "extract_invoices", "extract_informes_anuais"} <= names
    assert "reconcile_transactions" not in names
    assert "E3" not in names


@pytest.mark.asyncio
async def test_tombstone_matches_fk_and_hash_prefix_in_both_stage_forms(db: AsyncSession):
    ws, doc, run_id = await _seed_ws_doc_run(db)
    db.add_all(
        [
            # FK populada, key sem prefixo — match pela FK.
            _artifact(
                ws.id, run_id, stage="extract_with_llm", key="sem_prefixo", document_id=doc.id
            ),
            # FK NULL (writers E2 históricos), grafia legada — match pelo prefixo hash.
            _artifact(ws.id, run_id, stage="E2-llm", key="aaaaaaaaaaaa_btg_cdbdetalhes_2024"),
        ]
    )
    await db.flush()

    assert await _tombstone_doc(db, ws.id, doc) == 2
    assert await _remaining_keys(db) == set()


async def _seed_preservation_corpus(db: AsyncSession) -> tuple:
    """Alvo E2-llm + controles: E3 mesmo prefixo, outro doc, outro workspace."""
    ws, doc, run_id = await _seed_ws_doc_run(db)
    ws_other = await make_workspace(db)
    run_other = await _seed_run(db, ws_other.id)
    db.add_all(
        [
            _artifact(ws.id, run_id, stage="E2-llm", key="aaaaaaaaaaaa_btg_cdbdetalhes_2024"),
            # E3 é run-scoped/recomputado — fora do escopo do tombstone (ADR-311).
            _artifact(ws.id, run_id, stage="reconcile_transactions", key="aaaaaaaaaaaa_btg_x"),
            # Outro documento (prefixo B) no mesmo workspace.
            _artifact(ws.id, run_id, stage="extract_with_llm", key="bbbbbbbbbbbb_itau_extrato"),
            # Mesmo prefixo, outro workspace — isolamento multi-tenant.
            _artifact(
                ws_other.id, run_other, stage="E2-llm", key="aaaaaaaaaaaa_btg_cdbdetalhes_2024"
            ),
        ]
    )
    await db.flush()
    return ws, doc


@pytest.mark.asyncio
async def test_tombstone_preserves_downstream_other_docs_and_other_workspaces(db: AsyncSession):
    ws, doc = await _seed_preservation_corpus(db)

    assert await _tombstone_doc(db, ws.id, doc) == 1
    remaining = await _remaining_keys(db)
    assert ("reconcile_transactions", "aaaaaaaaaaaa_btg_x") in remaining
    assert ("extract_with_llm", "bbbbbbbbbbbb_itau_extrato") in remaining
    assert ("E2-llm", "aaaaaaaaaaaa_btg_cdbdetalhes_2024") in remaining  # ws_other


@pytest.mark.asyncio
async def test_tombstone_hash_prefix_underscore_is_not_like_wildcard(db: AsyncSession):
    """``autoescape``: `_` do prefixo não pode casar caractere arbitrário."""
    ws, doc, run_id = await _seed_ws_doc_run(db)
    db.add(_artifact(ws.id, run_id, stage="E2-llm", key="aaaaaaaaaaaaX_btg_2024"))
    await db.flush()

    assert await _tombstone_doc(db, ws.id, doc) == 0
    assert ("E2-llm", "aaaaaaaaaaaaX_btg_2024") in await _remaining_keys(db)


@pytest.mark.asyncio
async def test_bulk_hook_noop_when_extraction_identity_unchanged(db: AsyncSession):
    ws, doc, run_id = await _seed_ws_doc_run(db, doc_type="investment_report")
    doc.pipeline_last_run_at = datetime.now(timezone.utc)
    db.add(_artifact(ws.id, run_id, stage="E2-llm", key="aaaaaaaaaaaa_btg_cdbdetalhes_2024"))
    await db.flush()

    await _tombstone_if_extraction_changed(doc, ("investment_report", doc.bank_code), db)

    assert ("E2-llm", "aaaaaaaaaaaa_btg_cdbdetalhes_2024") in await _remaining_keys(db)
    assert doc.pipeline_last_run_at is not None


@pytest.mark.asyncio
async def test_bulk_hook_tombstones_and_requeues_when_doc_type_changed(db: AsyncSession):
    ws, doc, run_id = await _seed_ws_doc_run(db, doc_type="investment_report")
    doc.pipeline_last_run_at = datetime.now(timezone.utc)
    doc.pipeline_e2_extract_ok = True
    db.add(_artifact(ws.id, run_id, stage="E2-llm", key="aaaaaaaaaaaa_btg_cdbdetalhes_2024"))
    await db.flush()

    # doc_type mudou (cenário cdbdetalhes→informe) → tombstone + re-queue.
    doc.doc_type = DocumentType.informe_rendimentos_anuais
    await _tombstone_if_extraction_changed(doc, ("investment_report", doc.bank_code), db)

    assert await _remaining_keys(db) == set()
    assert doc.pipeline_last_run_at is None
    assert doc.pipeline_e2_extract_ok is None


def _cdb_document(ws_id: str) -> Document:
    return Document(
        workspace_id=ws_id,
        original_name="aaaaaaaaaaaa_btgpactual_cdbdetalhes_2024-0_original.pdf",
        doc_type=DocumentType.investment_report,
        bank_code="btgpactual",
        content_hash=_HASH_A,
        pipeline_last_run_at=datetime.now(timezone.utc),
    )


async def _seed_patch_scenario(db: AsyncSession, ws_id: str) -> Document:
    """Doc `cdbdetalhes` + artifact E2-llm órfão-a-ser + artifact de outro doc."""
    doc = _cdb_document(ws_id)
    db.add(doc)
    await db.flush()
    run_id = await _seed_run(db, ws_id)
    db.add_all(
        [
            _artifact(
                ws_id, run_id, stage="E2-llm", key="aaaaaaaaaaaa_btgpactual_cdbdetalhes_2024"
            ),
            _artifact(ws_id, run_id, stage="extract_with_llm", key="bbbbbbbbbbbb_outro_doc"),
        ]
    )
    await db.commit()
    return doc


@pytest.mark.asyncio
async def test_patch_reclassify_regression_cdbdetalhes_para_informe(
    auth_client: AsyncClient, db: AsyncSession
):
    """Regressão ADR-311 (dogfood): PATCH que muda doc_type deleta os artifacts E2* do doc — `cdbdetalhes` → `informe_rendimentos_anuais` deixava o E2-llm órfão."""
    ws_id = auth_client.ws_id
    doc = await _seed_patch_scenario(db, ws_id)

    resp = await auth_client.patch(
        f"/api/workspaces/{ws_id}/documents/{doc.id}",
        json={"doc_type": "informe_rendimentos_anuais"},
    )

    assert resp.status_code == 200
    assert resp.json()["doc_type"] == "informe_rendimentos_anuais"
    remaining = await _remaining_keys(db)
    assert ("E2-llm", "aaaaaaaaaaaa_btgpactual_cdbdetalhes_2024") not in remaining
    assert ("extract_with_llm", "bbbbbbbbbbbb_outro_doc") in remaining
