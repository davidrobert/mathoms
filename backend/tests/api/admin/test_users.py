"""Testes de /admin/users/*.

Padrão: setup via `db` fixture + commit, chamar endpoint, verificar via
API subsequente (evita split-brain entre fixture session e sessão do
endpoint quando StaticPool + aiosqlite estão em jogo).
"""

from __future__ import annotations

import pytest

from backend.tests.factories import make_user


async def _with_cookie(client, token: str):
    client.cookies.set("ops_session", token, domain="test", path="/admin")


@pytest.mark.asyncio
async def test_list_users(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    await make_user(db, email="a@test.com", full_name="Alice Test")
    await make_user(db, email="b@test.com", full_name="Bob Test")
    await db.commit()

    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.get("/admin/users")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
    emails = {u["email"] for u in body["users"]}
    assert {"a@test.com", "b@test.com"}.issubset(emails)


@pytest.mark.asyncio
async def test_anonymize(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    user = await make_user(db, email="to_anon@test.com")
    await db.commit()
    user_id = user.id
    await _with_cookie(client, ops_session_token_superadmin)

    resp = await client.post(f"/admin/users/{user_id}/anonymize", json={"confirm": "delete"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == user_id
    assert body["anonymized_email"].endswith("@anonymized.invalid")

    listing = await client.get("/admin/users")
    found = [u for u in listing.json()["users"] if u["id"] == user_id]
    assert found and found[0]["is_active"] is False
    assert found[0]["email"].endswith("@anonymized.invalid")


@pytest.mark.asyncio
async def test_anonymize_requires_confirm_literal(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    user = await make_user(db)
    await db.commit()
    user_id = user.id
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.post(f"/admin/users/{user_id}/anonymize", json={"confirm": "nope"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_hard_delete_requires_superadmin(
    ops_session_token_ops, admin_ui_enabled, ops_yaml, client, db
) -> None:
    user = await make_user(db)
    await db.commit()
    user_id = user.id

    await _with_cookie(client, ops_session_token_ops)
    resp = await client.post(
        f"/admin/users/{user_id}/hard-delete",
        json={"reason": "GDPR", "confirm": "hard_delete"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_hard_delete_ok(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    user = await make_user(db, email="victim@test.com")
    await db.commit()
    user_id = user.id

    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.post(
        f"/admin/users/{user_id}/hard-delete",
        json={"reason": "LGPD deletion request", "confirm": "hard_delete"},
    )
    assert resp.status_code == 200

    listing = await client.get("/admin/users")
    assert not any(u["id"] == user_id for u in listing.json()["users"])


@pytest.mark.asyncio
async def test_reset_password_generates(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    user = await make_user(db)
    await db.commit()
    user_id = user.id

    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.post(f"/admin/users/{user_id}/reset-password", json={})
    assert resp.status_code == 200
    assert len(resp.json()["temp_password"]) == 16


@pytest.mark.asyncio
async def test_developer_flag(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    user = await make_user(db, email="dev@test.com")
    await db.commit()
    user_id = user.id

    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.post(f"/admin/users/{user_id}/developer-flag", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json()["is_developer"] is True

    listing = await client.get("/admin/users")
    found = [u for u in listing.json()["users"] if u["id"] == user_id]
    assert found and found[0]["is_developer"] is True


@pytest.mark.asyncio
async def test_update_email_conflict(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    await make_user(db, email="a@test.com")
    b = await make_user(db, email="b@test.com")
    await db.commit()
    b_id = b.id

    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.patch(f"/admin/users/{b_id}/email", json={"new_email": "a@test.com"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_profile(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    user = await make_user(db, full_name="Old", email="prof@test.com")
    await db.commit()
    user_id = user.id

    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.patch(
        f"/admin/users/{user_id}/profile",
        json={"full_name": "New", "is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["changed"] is True

    listing = await client.get("/admin/users")
    found = [u for u in listing.json()["users"] if u["id"] == user_id]
    assert found and found[0]["full_name"] == "New" and found[0]["is_active"] is False
