"""LGPD self-service — endpoints, async export, soft-then-hard delete (Art. 18, V e VI)."""

from __future__ import annotations

import json
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_access_token
from backend.app.models import (
    AuditLog,
    DataExportRequest,
    DataExportRequestStatus,
    User,
    Workspace,
)
from backend.tests.factories import (
    make_category,
    make_member,
    make_task,
    make_user,
    make_workspace,
)


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=user.id, token_version=user.token_version)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _no_celery(monkeypatch):
    """Substitui o dispatch Celery por no-op — toda a suíte LGPD roda
    o worker síncrono via `process_data_export.run(id)`."""
    monkeypatch.setattr(
        "backend.app.api.me._enqueue_export",
        lambda _request_id: None,
    )


async def _seed_user_with_data(db: AsyncSession) -> tuple[User, Workspace]:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    await make_member(db, workspace=ws, full_name="Titular Teste", key="titular")
    await make_category(
        db,
        workspace=ws,
        code="alimentacao_lgpd",
        name="Alimentação LGPD",
    )
    await make_task(db, workspace=ws, title="Tarefa LGPD")
    await db.commit()
    return user, ws


@pytest.mark.asyncio
async def test_data_export_includes_all_user_data(
    client: AsyncClient, db: AsyncSession, tmp_path: Path, monkeypatch
) -> None:
    """Happy path: user pede export, worker monta tar.gz, manifest tem todos
    os arquivos esperados, payloads contêm dados que seedamos."""
    monkeypatch.setattr(
        "backend.app.services.lgpd_export_service.export_storage_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "backend.app.api.me._enqueue_export",
        lambda _request_id: None,
    )
    user, _ws = await _seed_user_with_data(db)
    headers = _auth_headers(user)

    resp = await client.post("/api/v1/me/data-export", headers=headers)
    assert resp.status_code == 202, resp.text
    body = resp.json()
    request_id = body["request_id"]
    assert body["status"] == DataExportRequestStatus.pending

    # In tests Celery roda eager? Não — tarefa não dispara. Chamamos direto.
    from backend.app.tasks.lgpd_export import process_data_export

    result = process_data_export.run(request_id)
    assert result["status"] == "ready"

    status_resp = await client.get(f"/api/v1/me/data-export/{request_id}", headers=headers)
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["status"] == DataExportRequestStatus.ready
    assert status_body["download_url"]

    download_url = status_body["download_url"].replace("/api/v1", "/api/v1")
    dl_resp = await client.get(download_url, headers=headers)
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"].startswith("application/gzip")

    archive_path = tmp_path / f"{request_id}.tar.gz"
    # one-shot consumiu o arquivo no disco; usar bytes da response.
    archive_bytes = dl_resp.content
    archive_path.write_bytes(archive_bytes)

    with tarfile.open(archive_path, "r:gz") as tar:
        names = sorted(tar.getnames())
        assert "manifest.json" in names
        assert "user.ndjson" in names
        assert "workspaces.ndjson" in names
        assert "tasks.ndjson" in names
        assert "categories.ndjson" in names

        manifest_member = tar.extractfile("manifest.json")
        assert manifest_member is not None
        manifest = json.loads(manifest_member.read())
        assert manifest["spec"].startswith("LGPD")
        files = {f["table"]: f for f in manifest["files"]}
        assert files["user"]["rows"] == 1
        assert files["categories"]["rows"] >= 1
        assert files["tasks"]["rows"] >= 1
        assert files["workspaces"]["rows"] >= 1

        tasks_member = tar.extractfile("tasks.ndjson")
        assert tasks_member is not None
        tasks_payload = [json.loads(line) for line in tasks_member.read().splitlines()]
        assert any(t.get("title") == "Tarefa LGPD" for t in tasks_payload)

        user_member = tar.extractfile("user.ndjson")
        assert user_member is not None
        user_payload = json.loads(user_member.read().splitlines()[0])
        assert "hashed_password" not in user_payload
        assert user_payload["email"] == user.email

    # one-shot: segundo download retorna 410.
    dl_again = await client.get(download_url, headers=headers)
    assert dl_again.status_code in (403, 410)


@pytest.mark.asyncio
async def test_data_export_concurrent_request_blocked(
    client: AsyncClient, db: AsyncSession
) -> None:
    user, _ws = await _seed_user_with_data(db)
    headers = _auth_headers(user)
    first = await client.post("/api/v1/me/data-export", headers=headers)
    assert first.status_code == 202
    second = await client.post("/api/v1/me/data-export", headers=headers)
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "data_export_already_in_progress"


@pytest.mark.asyncio
async def test_data_export_audit_trail(
    client: AsyncClient, db: AsyncSession, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "backend.app.services.lgpd_export_service.export_storage_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "backend.app.api.me._enqueue_export",
        lambda _request_id: None,
    )
    user, _ws = await _seed_user_with_data(db)
    headers = _auth_headers(user)

    resp = await client.post("/api/v1/me/data-export", headers=headers)
    request_id = resp.json()["request_id"]

    from backend.app.tasks.lgpd_export import process_data_export

    process_data_export.run(request_id)

    status_resp = await client.get(f"/api/v1/me/data-export/{request_id}", headers=headers)
    download_url = status_resp.json()["download_url"]
    await client.get(download_url, headers=headers)

    actions = (
        await db.execute(select(AuditLog.action).where(AuditLog.actor_user_id == user.id))
    ).all()
    action_set = {a[0] for a in actions}
    assert "lgpd.export_requested" in action_set
    assert "lgpd.export_ready" in action_set
    assert "lgpd.export_downloaded" in action_set


@pytest.mark.asyncio
async def test_data_export_expires_after_ttl(
    client: AsyncClient, db: AsyncSession, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "backend.app.services.lgpd_export_service.export_storage_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "backend.app.api.me._enqueue_export",
        lambda _request_id: None,
    )
    user, _ws = await _seed_user_with_data(db)
    headers = _auth_headers(user)
    resp = await client.post("/api/v1/me/data-export", headers=headers)
    request_id = resp.json()["request_id"]
    from backend.app.tasks.lgpd_export import process_data_export
    from backend.app.tasks.periodic_tasks import expire_data_exports

    process_data_export.run(request_id)

    # Backdate expires_at para forçar expiração.
    req = (
        await db.execute(select(DataExportRequest).where(DataExportRequest.id == request_id))
    ).scalar_one()
    req.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db.commit()

    result = expire_data_exports.run()
    assert result["expired"] >= 1

    status_resp = await client.get(f"/api/v1/me/data-export/{request_id}", headers=headers)
    body = status_resp.json()
    assert body["status"] == DataExportRequestStatus.expired

    actions = (
        await db.execute(
            select(AuditLog.action).where(
                AuditLog.actor_user_id == user.id,
                AuditLog.action == "lgpd.export_expired",
            )
        )
    ).all()
    assert len(actions) >= 1


@pytest.mark.asyncio
async def test_deletion_request_soft_then_hard(client: AsyncClient, db: AsyncSession) -> None:
    """Marca user p/ deletion → backdate timestamp → cron faz hard-delete."""
    user = await make_user(db, email="will_delete@test.com")
    await make_workspace(db, owner=user)
    await db.commit()
    headers = _auth_headers(user)

    resp = await client.post("/api/v1/me/delete-request", headers=headers)
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["user_id"] == user.id
    assert body["deletion_requested_at"]
    assert body["hard_delete_after"]

    refreshed = (
        await db.execute(
            select(User).where(User.id == user.id).execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert refreshed.deletion_requested_at is not None
    initial_token_version = refreshed.token_version
    assert initial_token_version >= 1

    # Stale token (pre-bump) deve ser rejeitado pelo get_current_user.
    stale_token = create_access_token(subject=user.id, token_version=0)
    me_resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {stale_token}"}
    )
    assert me_resp.status_code == 401

    # Backdate p/ disparar cron.
    refreshed.deletion_requested_at = datetime.now(timezone.utc) - timedelta(days=31)
    await db.commit()

    from backend.app.tasks.periodic_tasks import process_user_deletions

    result = process_user_deletions.run()
    assert result["hard_deleted"] >= 1

    gone = (await db.execute(select(User).where(User.id == user.id))).scalar_one_or_none()
    assert gone is None


@pytest.mark.asyncio
async def test_deletion_request_audited(client: AsyncClient, db: AsyncSession) -> None:
    user = await make_user(db, email="audit_delete@test.com")
    await make_workspace(db, owner=user)
    await db.commit()
    headers = _auth_headers(user)

    await client.post("/api/v1/me/delete-request", headers=headers)

    new_token = create_access_token(
        subject=user.id,
        token_version=user.token_version + 1,
    )
    actions_after_request = (
        await db.execute(select(AuditLog.action).where(AuditLog.actor_user_id == user.id))
    ).all()
    assert "lgpd.deletion_requested" in {a[0] for a in actions_after_request}

    # Backdate + cron — completed audit fica com actor_user_id NULL
    # (anonimização). Filtramos só pela ação para confirmar entrada.
    refreshed = (
        await db.execute(
            select(User).where(User.id == user.id).execution_options(populate_existing=True)
        )
    ).scalar_one()
    refreshed.deletion_requested_at = datetime.now(timezone.utc) - timedelta(days=31)
    await db.commit()

    from backend.app.tasks.periodic_tasks import process_user_deletions

    process_user_deletions.run()

    completed_rows = (
        (await db.execute(select(AuditLog).where(AuditLog.action == "lgpd.deletion_completed")))
        .scalars()
        .all()
    )
    assert any(r.resource_id == user.id for r in completed_rows)
    # Nova token issued antes do hard-delete está obsoleto após user
    # apagado — qualquer endpoint deve rejeitar.
    me_after = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert me_after.status_code == 401


@pytest.mark.asyncio
async def test_deletion_request_can_be_canceled(client: AsyncClient, db: AsyncSession) -> None:
    user = await make_user(db, email="will_cancel@test.com")
    await make_workspace(db, owner=user)
    await db.commit()
    headers = _auth_headers(user)

    resp = await client.post("/api/v1/me/delete-request", headers=headers)
    assert resp.status_code == 202

    # Re-emit token after token_version bump so cancel call passes auth.
    refreshed = (
        await db.execute(
            select(User).where(User.id == user.id).execution_options(populate_existing=True)
        )
    ).scalar_one()
    new_headers = _auth_headers(refreshed)

    cancel = await client.delete("/api/v1/me/delete-request", headers=new_headers)
    assert cancel.status_code == 200
    assert cancel.json()["user_id"] == user.id

    final = (
        await db.execute(
            select(User).where(User.id == user.id).execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert final.deletion_requested_at is None

    actions = (
        await db.execute(select(AuditLog.action).where(AuditLog.actor_user_id == user.id))
    ).all()
    assert "lgpd.deletion_canceled" in {a[0] for a in actions}


@pytest.mark.asyncio
async def test_data_export_invalid_token_403(
    client: AsyncClient, db: AsyncSession, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "backend.app.services.lgpd_export_service.export_storage_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "backend.app.api.me._enqueue_export",
        lambda _request_id: None,
    )
    user, _ws = await _seed_user_with_data(db)
    headers = _auth_headers(user)
    resp = await client.post("/api/v1/me/data-export", headers=headers)
    request_id = resp.json()["request_id"]
    from backend.app.tasks.lgpd_export import process_data_export

    process_data_export.run(request_id)

    bad = await client.get(
        f"/api/v1/me/data-export/{request_id}/download?token=NOT_A_REAL_TOKEN_OK_LONG",
        headers=headers,
    )
    assert bad.status_code == 403


@pytest.mark.asyncio
async def test_other_user_cannot_see_export(
    client: AsyncClient, db: AsyncSession, tmp_path: Path, monkeypatch
) -> None:
    """Tenancy: dono A pede export; user B autenticado tenta ler — 404."""
    monkeypatch.setattr(
        "backend.app.services.lgpd_export_service.export_storage_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "backend.app.api.me._enqueue_export",
        lambda _request_id: None,
    )
    user_a, _ = await _seed_user_with_data(db)
    user_b = await make_user(db, email="b_lgpd@test.com")
    await db.commit()

    headers_a = _auth_headers(user_a)
    headers_b = _auth_headers(user_b)

    create = await client.post("/api/v1/me/data-export", headers=headers_a)
    request_id = create.json()["request_id"]

    leak_attempt = await client.get(f"/api/v1/me/data-export/{request_id}", headers=headers_b)
    assert leak_attempt.status_code == 404
