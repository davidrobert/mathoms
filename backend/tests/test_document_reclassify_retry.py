"""Tests — self-heal de docs parkados (A37.l3 · ADR-329).

Regressões da lane:
(a) ``stored_path`` stale + arquivo em ``inbox_processed/`` → retry relocaliza
    via ``content_hash`` e reclassifica (antes: ``no_file`` para sempre);
(b) key presente só em ``llm_config`` (sem env) → retry roda LLM (antes: gate
    env-only pulava silencioso).
Match de relocação é EXCLUSIVAMENTE por content_hash — nunca por basename.
Fixtures 100% sintéticas (zero PII).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import backend.app.services.documents.document_reclassify_bulk_service as bulk_mod
import backend.app.services.documents.document_reclassify_retry as retry_mod
from backend.app.core.database import SyncSessionLocal
from backend.app.models.document import Document, DocumentType
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.services.documents.document_reclassify_bulk_service import (
    reclassify_workspace_documents,
)
from backend.app.services.documents.document_reclassify_retry import (
    retry_parked_documents_sync,
)
from backend.app.services.security.vault import get_vault
from backend.app.services.storage import StorageService
from backend.tests.factories import make_document, make_llm_config, make_workspace

_CONTENT = b"%PDF-1.4 conteudo sintetico informe pj mathoms a37l3"
_CONTENT_HASH = hashlib.sha256(_CONTENT).hexdigest()


def _fake_clf() -> dict:
    """Classificação confiante SEM rota p/ data/ (dest_group=None → 'reclassified')."""
    return {
        "doc_type": DocumentType.investment_report,
        "bank_code": "btgpactual",
        "period": "202601",
        "dest_group": None,
        "e0_doc_type": None,
        "classification_meta": {"source": "llm_fallback", "confidence": 0.9},
        "confidence": 0.9,
        "needs_review": False,
    }


async def _seed_parked_doc(db, ws, stored_path: str) -> Document:
    doc = await make_document(
        db, workspace=ws, stored_path=stored_path, doc_type="other", content_hash=_CONTENT_HASH
    )
    doc.needs_review = True
    doc.classification_confidence = 0.0
    doc.classification_meta = {"llm_skipped_reason": "missing_api_key"}
    await db.commit()
    return doc


def _write_file(tenant_root: Path, rel: str, content: bytes) -> Path:
    p = tenant_root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    return p


def _capture_classify(monkeypatch, module) -> list:
    """Stubba ``classify_document`` no módulo; retorna lista de ``(path, api_key)``."""
    calls: list = []

    def _fake(path, _base=None, **kw):
        calls.append((path, kw.get("api_key")))
        return _fake_clf()

    monkeypatch.setattr(module, "classify_document", _fake)
    return calls


def _run_retry_sync(ws_id: str, storage_root: Path, tenant_root: Path) -> dict[str, int]:
    with SyncSessionLocal() as sdb:
        stats = retry_parked_documents_sync(
            ws_id,
            db=sdb,
            storage=StorageService(storage_root=storage_root),
            tenant_root=tenant_root,
        )
        sdb.commit()
    return stats


def _get_doc(doc_id: str) -> Document:
    with SyncSessionLocal() as sdb:
        return sdb.get(Document, doc_id)


@pytest.mark.asyncio
async def test_stale_stored_path_relocates_via_content_hash(db, tmp_path, monkeypatch):
    """(a) stored_path stale + arquivo em inbox_processed/ → reloca por hash e reclassifica."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-env")
    ws = await make_workspace(db)
    doc = await _seed_parked_doc(db, ws, "inbox/informe_pj_2025.pdf")
    tenant_root = tmp_path / ws.id
    moved = _write_file(tenant_root, "inbox_processed/2026-07-01/nome_diferente.pdf", _CONTENT)
    # decoy: MESMO basename do stored_path antigo, conteúdo diferente — nunca usado
    _write_file(tenant_root, "inbox_processed/2026-07-02/informe_pj_2025.pdf", b"conteudo alheio")
    calls = _capture_classify(monkeypatch, retry_mod)

    stats = _run_retry_sync(ws.id, tmp_path, tenant_root)

    assert (stats["no_file"], stats["relocated"], stats["reclassified"]) == (0, 1, 1)
    assert [c[0] for c in calls] == [moved]
    healed = _get_doc(doc.id)
    assert healed.stored_path == "inbox_processed/2026-07-01/nome_diferente.pdf"
    assert healed.needs_review is False


@pytest.mark.asyncio
async def test_no_hash_match_never_relinks_by_basename(db, tmp_path, monkeypatch):
    """Basename igual + hash diferente NÃO reloca (re-linkaria a conteúdo alheio) → no_file."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-env")
    ws = await make_workspace(db)
    doc = await _seed_parked_doc(db, ws, "inbox/extrato_sumido.pdf")
    _write_file(tmp_path / ws.id, "inbox_processed/2026-07-01/extrato_sumido.pdf", b"outro doc")
    calls = _capture_classify(monkeypatch, retry_mod)

    stats = _run_retry_sync(ws.id, tmp_path, tmp_path / ws.id)

    assert (stats["no_file"], stats["relocated"]) == (1, 0)
    assert not calls
    assert _get_doc(doc.id).stored_path == "inbox/extrato_sumido.pdf"


@pytest.mark.asyncio
async def test_key_only_in_llm_config_runs_retry(db, tmp_path, monkeypatch):
    """(b) Key só em llm_config (sem env) → retry roda e propaga a key DB-backed."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ws = await make_workspace(db)
    encrypted = get_vault().encrypt("sk-ant-db-key")
    await make_llm_config(db, workspace=ws, api_key_encrypted=encrypted)
    doc = await _seed_parked_doc(db, ws, "inbox/doc_parkado.pdf")
    _write_file(tmp_path / ws.id, "inbox/doc_parkado.pdf", _CONTENT)
    calls = _capture_classify(monkeypatch, retry_mod)

    stats = _run_retry_sync(ws.id, tmp_path, tmp_path / ws.id)

    assert stats["retried"] == 1
    assert [c[1] for c in calls] == ["sk-ant-db-key"]
    assert _get_doc(doc.id).needs_review is False


@pytest.mark.asyncio
async def test_no_key_anywhere_skips_without_classify(db, tmp_path, monkeypatch):
    """Sem env E sem llm_config → retry sai cedo (contadores zerados, LLM intocado)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ws = await make_workspace(db)
    await _seed_parked_doc(db, ws, "inbox/x.pdf")
    calls = _capture_classify(monkeypatch, retry_mod)

    stats = _run_retry_sync(ws.id, tmp_path, tmp_path / ws.id)

    assert not calls
    assert all(v == 0 for v in stats.values())


@pytest.mark.asyncio
async def test_non_retriable_needs_review_counts_as_skipped(db, tmp_path, monkeypatch):
    """Telemetria A37.l3: docs needs_review não-retentáveis aparecem em ``skipped``."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-env")
    ws = await make_workspace(db)
    doc = await make_document(db, workspace=ws, stored_path="inbox/a.pdf", doc_type="other")
    doc.needs_review = True
    doc.classification_meta = {"llm_skipped_reason": "sdk_not_installed"}
    await db.commit()

    stats = _run_retry_sync(ws.id, tmp_path, tmp_path / ws.id)

    assert stats["skipped"] == 1
    assert stats["scanned"] == 0


@pytest.mark.asyncio
async def test_bulk_reclassify_relocates_stale_stored_path(db, tmp_path, monkeypatch):
    """Bulk: stored_path stale era skip silencioso; agora reloca por content_hash."""
    ws = await make_workspace(db)
    doc = await _seed_parked_doc(db, ws, "inbox/planilha_gastos.xlsx")
    _write_file(tmp_path / ws.id, "inbox_processed/2026-07-03/planilha_renomeada.xlsx", _CONTENT)
    _capture_classify(monkeypatch, bulk_mod)

    stats = await reclassify_workspace_documents(
        ws.id, db=db, repo=DocumentRepository(db), storage=StorageService(storage_root=tmp_path)
    )
    await db.commit()

    assert (stats.updated, stats.skipped) == (1, 0)
    healed = _get_doc(doc.id)
    assert healed.stored_path == "inbox_processed/2026-07-03/planilha_renomeada.xlsx"
    assert healed.needs_review is False
