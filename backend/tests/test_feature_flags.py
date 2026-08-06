"""Testes de feature_flags_service + API (ADR-074)."""

from __future__ import annotations

import pytest

from backend.app.core.security import create_access_token
from backend.app.services import feature_flags_service
from backend.tests import factories

# ─── Service ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_flags_returns_defaults_for_new_workspace(db):
    ws = await factories.make_workspace(db)
    flags = await feature_flags_service.get_flags(ws.id, db=db)
    assert flags == feature_flags_service.DEFAULTS


def test_report_provenance_defaults_off():
    """A25.l5 (ADR-279): rollout do selo/popover é opt-in por workspace —
    default True aqui seria cutover global silencioso."""
    assert feature_flags_service.DEFAULTS["report_provenance_enabled"] is False


def test_dedup_natural_key_v2_defaults_on():
    """A25.l2 (ADR-287): cutover concluído — default True pós-G-f (zero delta no
    dado real) + goldens v2≡v1. Rollback é flag off por workspace, não o default."""
    assert feature_flags_service.DEFAULTS["dedup_natural_key_v2_enabled"] is True


@pytest.mark.asyncio
async def test_set_flag_persists_override(db):
    ws = await factories.make_workspace(db)
    flags = await feature_flags_service.set_flag(ws.id, "tasks_v2_enabled", False, db=db)
    await db.commit()
    assert flags["tasks_v2_enabled"] is False
    # Outras flags mantêm default
    assert flags["report_tasks_snapshot_enabled"] is True


@pytest.mark.asyncio
async def test_set_flag_twice_updates_in_place(db):
    ws = await factories.make_workspace(db)
    await feature_flags_service.set_flag(ws.id, "tasks_v2_enabled", False, db=db)
    await db.commit()
    flags = await feature_flags_service.set_flag(ws.id, "tasks_v2_enabled", True, db=db)
    await db.commit()
    assert flags["tasks_v2_enabled"] is True


@pytest.mark.asyncio
async def test_set_flag_rejects_unknown_flag(db):
    ws = await factories.make_workspace(db)
    with pytest.raises(ValueError, match="desconhecida"):
        await feature_flags_service.set_flag(ws.id, "nonexistent_flag", True, db=db)


@pytest.mark.asyncio
async def test_is_enabled_shortcut(db):
    ws = await factories.make_workspace(db)
    assert await feature_flags_service.is_enabled(ws.id, "tasks_v2_enabled", db=db) is True
    assert await feature_flags_service.is_enabled(ws.id, "nonexistent", db=db) is False


@pytest.mark.asyncio
async def test_flags_isolated_between_workspaces(db):
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    await feature_flags_service.set_flag(ws_a.id, "tasks_v2_enabled", False, db=db)
    await db.commit()

    flags_a = await feature_flags_service.get_flags(ws_a.id, db=db)
    flags_b = await feature_flags_service.get_flags(ws_b.id, db=db)
    assert flags_a["tasks_v2_enabled"] is False
    assert flags_b["tasks_v2_enabled"] is True  # default


# ─── API ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_flags_endpoint(db, client):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(user.id)}"

    resp = await client.get(f"/api/workspaces/{ws.id}/feature-flags")
    assert resp.status_code == 200
    flags = resp.json()["flags"]
    assert "tasks_v2_enabled" in flags


@pytest.mark.asyncio
async def test_put_flag_endpoint(db, client):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(user.id)}"

    resp = await client.put(
        f"/api/workspaces/{ws.id}/feature-flags/tasks_v2_enabled",
        json={"enabled": False},
    )
    assert resp.status_code == 200
    assert resp.json()["flags"]["tasks_v2_enabled"] is False

    # Segunda chamada persiste
    resp = await client.get(f"/api/workspaces/{ws.id}/feature-flags")
    assert resp.json()["flags"]["tasks_v2_enabled"] is False


# A6e.4 slice: flag desconhecida virou ValidationError → 422 (padrão global
# ADR-101 R15). Antes era HTTPException(400) inline no router.
@pytest.mark.asyncio
async def test_put_unknown_flag_returns_422(db, client):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(user.id)}"

    resp = await client.put(
        f"/api/workspaces/{ws.id}/feature-flags/made_up_flag",
        json={"enabled": True},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_cross_tenant_get_flags_returns_403(db, client):
    user_a = await factories.make_user(db)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(user_a.id)}"

    resp = await client.get(f"/api/workspaces/{ws_b.id}/feature-flags")
    assert resp.status_code == 403


async def _put_flag(db, client, flag: str, *, operator_only: frozenset, monkeypatch):
    """Setup comum: deny-list injetada + workspace autenticado + PUT na flag."""
    from backend.app.services import feature_flags_service

    monkeypatch.setattr(feature_flags_service, "OPERATOR_ONLY", operator_only)
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(user.id)}"
    return await client.put(f"/api/workspaces/{ws.id}/feature-flags/{flag}", json={"enabled": True})


@pytest.mark.asyncio
async def test_flag_operator_only_recusa_flip_pelo_workspace(db, client, monkeypatch):
    """A40.l2 D1: flag que governa mutação destrutiva não é flipável pelo workspace."""
    # A pré-condição dela é medida FORA do request (gate de override); flipável pelo
    # endpoint normal, o gate viraria decorativo. `learning_loop_enabled` é cobaia:
    # prova o MECANISMO sem depender da flag do enforce, que só nasce no PR3.
    resp = await _put_flag(
        db,
        client,
        "learning_loop_enabled",
        operator_only=frozenset({"learning_loop_enabled"}),
        monkeypatch=monkeypatch,
    )

    assert resp.status_code == 422
    assert "operator-only" in resp.text


@pytest.mark.asyncio
async def test_flag_fora_da_deny_list_continua_flipavel(db, client, monkeypatch):
    """Prova que a guarda DISCRIMINA — sem isto, um `raise` incondicional passaria."""
    resp = await _put_flag(
        db,
        client,
        "learning_loop_enabled",
        operator_only=frozenset({"outra_flag"}),
        monkeypatch=monkeypatch,
    )

    assert resp.status_code == 200
