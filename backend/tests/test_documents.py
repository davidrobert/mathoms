"""Tests for Documents API — upload, list, delete, retry-unlock."""

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document, DocumentStatus, DocumentType

_PROC = "backend.app.services.document_upload_service.process_uploaded_document"


def _mock_process(
    file_path, passwords, config_dir, tenant_root=None, workspace_id=None, content_hash=None
):
    """Deterministic mock for process_uploaded_document that classifies by extension/content.

    Kwargs ``tenant_root`` / ``workspace_id`` / ``content_hash`` kept for parity
    with the real signature.
    """
    ext = Path(file_path).suffix.lower()
    base = {
        "bank_code": None,
        "period": None,
        "confidence": 1.0,
        "needs_review": False,
        "error_message": None,
        "stored_path_relative": None,
    }
    if ext == ".json":
        try:
            data = json.loads(Path(file_path).read_text())
            if isinstance(data, dict):
                if "membros" in data or "members" in data:
                    return {
                        **base,
                        "status": DocumentStatus.ready,
                        "doc_type": DocumentType.e1_members_json,
                        "classification_meta": {"source": "json_structure"},
                    }
                if "patrimonio" in data or "baseline" in data:
                    return {
                        **base,
                        "status": DocumentStatus.ready,
                        "doc_type": DocumentType.e1_5_baseline_json,
                        "classification_meta": {"source": "json_structure"},
                    }
        except Exception:
            pass
    return {
        **base,
        "status": DocumentStatus.ready,
        "doc_type": DocumentType.other,
        "classification_meta": {"source": "test_mock"},
        "confidence": 0.0,
        "needs_review": True,
    }


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_csv_file(auth_client: AsyncClient):
    content = b"date,description,value\n2026-01-01,Test,100.00\n"
    with patch(_PROC, side_effect=_mock_process):
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/documents/upload",
            files=[("files", ("extrato_itau_202601.csv", io.BytesIO(content), "text/csv"))],
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_uploaded"] == 1
    doc = data["documents"][0]
    assert doc["original_name"] == "extrato_itau_202601.csv"
    assert doc["file_size_bytes"] == len(content)
    assert doc["status"] == "ready"


@pytest.mark.asyncio
async def test_upload_multiple_files(auth_client: AsyncClient):
    files = [
        ("files", ("file1.csv", io.BytesIO(b"data1"), "text/csv")),
        ("files", ("file2.csv", io.BytesIO(b"data2"), "text/csv")),
        ("files", ("file3.csv", io.BytesIO(b"data3"), "text/csv")),
    ]
    with patch(_PROC, side_effect=_mock_process):
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/documents/upload", files=files
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_uploaded"] == 3
    assert len(data["documents"]) == 3


@pytest.mark.asyncio
async def test_upload_invalid_extension(auth_client: AsyncClient):
    resp = await auth_client.post(
        f"/api/workspaces/{auth_client.ws_id}/documents/upload",
        files=[("files", ("virus.exe", io.BytesIO(b"malware"), "application/octet-stream"))],
    )
    assert resp.status_code == 201
    doc = resp.json()["documents"][0]
    assert doc["status"] == "error"
    assert doc["error_message"] is not None


@pytest.mark.asyncio
async def test_upload_empty_file(auth_client: AsyncClient):
    resp = await auth_client.post(
        f"/api/workspaces/{auth_client.ws_id}/documents/upload",
        files=[("files", ("empty.csv", io.BytesIO(b""), "text/csv"))],
    )
    assert resp.status_code == 201
    doc = resp.json()["documents"][0]
    assert doc["status"] == "error"
    assert "vazio" in doc["error_message"].lower()


# ---------------------------------------------------------------------------
# Dedupe — regression coverage for validation-failure + content_hash leak.
#
# Bug: ``_record_validation_failure`` historicamente persistia ``Document``
# com ``content_hash=NULL``, e o partial unique index
# ``ux_documents_workspace_content_hash WHERE content_hash IS NOT NULL`` não
# bloqueava re-upload das mesmas bytes. Resultado em produção: usuário fez
# upload de ``082.xls`` → "Erro" (NULL hash) → re-upload mais tarde passou
# como "Não classificado" sem ser deduplicado.
# ---------------------------------------------------------------------------


async def _upload_exe(auth_client: AsyncClient, name: str, payload: bytes):
    return await auth_client.post(
        f"/api/workspaces/{auth_client.ws_id}/documents/upload",
        files=[("files", (name, io.BytesIO(payload), "application/octet-stream"))],
    )


@pytest.mark.asyncio
async def test_re_upload_after_validation_error_is_skipped(auth_client: AsyncClient):
    """Mesmas bytes em dois uploads que falham validação → segundo é skipped."""
    payload = b"malware-bytes-for-test"
    first = await _upload_exe(auth_client, "virus.exe", payload)
    assert first.status_code == 201
    assert first.json()["documents"][0]["status"] == "error"

    second = await _upload_exe(auth_client, "virus.exe", payload)
    assert second.status_code == 201
    body2 = second.json()
    assert body2["total_uploaded"] == 0
    assert body2["total_skipped"] == 1
    assert "virus.exe" in body2["skipped_duplicates"]


@pytest.mark.asyncio
async def test_valid_upload_after_validation_error_blocked_by_hash(auth_client: AsyncClient):
    """Mesmo content_hash, validação distinta — segundo upload (válido) é deduplicado."""
    payload = b"date,description,value\n2026-01-01,Test,100.00\n"
    first = await auth_client.post(
        f"/api/workspaces/{auth_client.ws_id}/documents/upload",
        files=[("files", ("data.exe", io.BytesIO(payload), "application/octet-stream"))],
    )
    assert first.status_code == 201
    assert first.json()["documents"][0]["status"] == "error"

    with patch(_PROC, side_effect=_mock_process):
        second = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/documents/upload",
            files=[("files", ("data.csv", io.BytesIO(payload), "text/csv"))],
        )
    assert second.status_code == 201
    body2 = second.json()
    assert body2["total_uploaded"] == 0
    assert body2["total_skipped"] == 1
    assert "data.csv" in body2["skipped_duplicates"]


@pytest.mark.asyncio
async def test_re_upload_empty_file_is_skipped(auth_client: AsyncClient):
    """Arquivo vazio também é content-addressed: SHA-256 de bytes vazios é determinístico."""
    first = await auth_client.post(
        f"/api/workspaces/{auth_client.ws_id}/documents/upload",
        files=[("files", ("empty.csv", io.BytesIO(b""), "text/csv"))],
    )
    assert first.status_code == 201
    assert first.json()["documents"][0]["status"] == "error"

    second = await auth_client.post(
        f"/api/workspaces/{auth_client.ws_id}/documents/upload",
        files=[("files", ("empty.csv", io.BytesIO(b""), "text/csv"))],
    )
    assert second.status_code == 201
    body2 = second.json()
    assert body2["total_uploaded"] == 0
    assert body2["total_skipped"] == 1


@pytest.mark.asyncio
async def test_upload_json_e1_members(auth_client: AsyncClient):
    members_json = json.dumps({"membros": [{"nome": "David", "cpf": "123"}]}).encode()
    with patch(_PROC, side_effect=_mock_process):
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/documents/upload",
            files=[("files", ("members.json", io.BytesIO(members_json), "application/json"))],
        )
    assert resp.status_code == 201
    doc = resp.json()["documents"][0]
    assert doc["doc_type"] == "e1_members_json"
    assert doc["status"] == "ready"


@pytest.mark.asyncio
async def test_upload_json_e15_baseline(auth_client: AsyncClient):
    baseline_json = json.dumps({"patrimonio": {"total": 100000}}).encode()
    with patch(_PROC, side_effect=_mock_process):
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/documents/upload",
            files=[("files", ("baseline.json", io.BytesIO(baseline_json), "application/json"))],
        )
    assert resp.status_code == 201
    doc = resp.json()["documents"][0]
    assert doc["doc_type"] == "e1_5_baseline_json"
    assert doc["status"] == "ready"


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_documents_empty(auth_client: AsyncClient):
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["documents"] == []


@pytest.mark.asyncio
async def test_list_documents_after_upload(auth_client: AsyncClient):
    with patch(_PROC, side_effect=_mock_process):
        await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/documents/upload",
            files=[("files", ("test.csv", io.BytesIO(b"data"), "text/csv"))],
        )
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/documents")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_list_documents_filter_by_status(auth_client: AsyncClient):
    with patch(_PROC, side_effect=_mock_process):
        await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/documents/upload",
            files=[("files", ("good.csv", io.BytesIO(b"data"), "text/csv"))],
        )
    await auth_client.post(
        f"/api/workspaces/{auth_client.ws_id}/documents/upload",
        files=[("files", ("bad.exe", io.BytesIO(b"data"), "application/octet-stream"))],
    )

    resp_error = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/documents?status=error"
    )
    assert resp_error.status_code == 200
    for doc in resp_error.json()["documents"]:
        assert doc["status"] == "error"


@pytest.mark.asyncio
async def test_list_documents_invalid_status_filter(auth_client: AsyncClient):
    # A6e.4 slice 10: list delega a use case que lança ValidationError →
    # handler global ADR-101 R15 traduz para 422 (antes 400 inline).
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/documents?status=bogus")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_documents_filter_ready_comma_processed(
    auth_client: AsyncClient, db: AsyncSession
):
    ws_id = auth_client.ws_id
    db.add(
        Document(
            workspace_id=ws_id,
            original_name="pipeline_ok.pdf",
            stored_path="data/bank/pipeline_ok-0_original.pdf",
            doc_type=DocumentType.bank_statement,
            status=DocumentStatus.processed,
            file_size_bytes=1,
        )
    )
    await db.commit()

    resp = await auth_client.get(f"/api/workspaces/{ws_id}/documents?status=ready,processed")
    assert resp.status_code == 200
    bodies = resp.json()["documents"]
    assert any(d["status"] == "processed" for d in bodies)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_document(auth_client: AsyncClient):
    with patch(_PROC, side_effect=_mock_process):
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/documents/upload",
            files=[("files", ("delete_me.csv", io.BytesIO(b"data"), "text/csv"))],
        )
    doc_id = resp.json()["documents"][0]["id"]

    del_resp = await auth_client.delete(f"/api/workspaces/{auth_client.ws_id}/documents/{doc_id}")
    assert del_resp.status_code == 204

    list_resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/documents")
    ids = [d["id"] for d in list_resp.json()["documents"]]
    assert doc_id not in ids


@pytest.mark.asyncio
async def test_delete_document_not_found(auth_client: AsyncClient):
    resp = await auth_client.delete(f"/api/workspaces/{auth_client.ws_id}/documents/nonexistent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Retry-unlock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_unlock_no_passwords(auth_client: AsyncClient):
    resp = await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/documents/retry-unlock")
    assert resp.status_code == 400
    assert "senha" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_retry_unlock_no_pending_docs(auth_client: AsyncClient):
    await auth_client.post(
        f"/api/workspaces/{auth_client.ws_id}/vault/passwords",
        json={"label": "test", "password": "pw"},
    )
    resp = await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/documents/retry-unlock")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_unauthorized(client: AsyncClient):
    resp = await client.post(
        "/api/workspaces/00000000-0000-0000-0000-000000000000/documents/upload",
        files=[("files", ("test.csv", io.BytesIO(b"data"), "text/csv"))],
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_unauthorized(client: AsyncClient):
    resp = await client.get("/api/workspaces/00000000-0000-0000-0000-000000000000/documents")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_delete_unauthorized(client: AsyncClient):
    resp = await client.delete(
        "/api/workspaces/00000000-0000-0000-0000-000000000000/documents/some-id"
    )
    assert resp.status_code in (401, 403)
