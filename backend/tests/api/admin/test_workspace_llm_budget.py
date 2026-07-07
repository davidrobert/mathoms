"""Endpoints do editor de budget LLM (A30.l1 · ADR-116 + ADR-173).

PATCH /admin/workspaces/{id}/llm-budget + GET /admin/llm-budget-by-workspace
(janela mês-calendário UTC — paridade com o hard-stop, não rolling 30d).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from backend.app.models.llm_call_log import LLMCallLog
from backend.tests.factories.builders import make_workspace


async def _with_cookie(client, token: str) -> None:
    client.cookies.set("ops_session", token, domain="test", path="/admin")


def _call_row(ws_id: str, cost: str, *, created_at: datetime | None = None) -> LLMCallLog:
    row = LLMCallLog(
        workspace_id=ws_id,
        stage="E5",
        model_name="claude-test",
        tokens_in=10,
        tokens_out=5,
        cost_usd=Decimal(cost),
    )
    if created_at is not None:
        row.created_at = created_at
    return row


@pytest.mark.asyncio
async def test_patch_requires_operator(admin_ui_enabled, ops_yaml, client, db) -> None:
    ws = await make_workspace(db)
    await db.commit()
    resp = await client.patch(f"/admin/workspaces/{ws.id}/llm-budget", json={"cap_usd": "10"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_patch_sets_cap(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    ws = await make_workspace(db)
    await db.commit()
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.patch(f"/admin/workspaces/{ws.id}/llm-budget", json={"cap_usd": "20"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["monthly_budget_usd"] == "20.00"
    assert body["previous_budget_usd"] == "5.00"
    assert body["remove_cap"] is False


@pytest.mark.asyncio
async def test_patch_remove_cap(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    ws = await make_workspace(db)
    await db.commit()
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.patch(f"/admin/workspaces/{ws.id}/llm-budget", json={"remove_cap": True})
    assert resp.status_code == 200
    assert resp.json()["monthly_budget_usd"] is None


@pytest.mark.asyncio
async def test_patch_404_unknown_workspace(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.patch("/admin/workspaces/nope/llm-budget", json={"cap_usd": "10"})
    assert resp.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"cap_usd": "-1"},
        {"cap_usd": "nan"},
        {"cap_usd": "999999"},
        {},
        {"cap_usd": "10", "remove_cap": True},
    ],
)
async def test_patch_422_invalid_payloads(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db, payload
) -> None:
    ws = await make_workspace(db)
    await db.commit()
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.patch(f"/admin/workspaces/{ws.id}/llm-budget", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_month_window_excludes_previous_month(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    ws = await make_workspace(db)
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    db.add(_call_row(ws.id, "3.00", created_at=month_start + timedelta(hours=1)))
    db.add(_call_row(ws.id, "99.00", created_at=month_start - timedelta(days=1)))
    await db.commit()
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.get("/admin/llm-budget-by-workspace")
    assert resp.status_code == 200
    body = resp.json()
    assert body["month"] == month_start.strftime("%Y-%m")
    item = next(i for i in body["items"] if i["workspace_id"] == ws.id)
    assert item["spent_month_usd"] == "3.00"  # o gasto do mês anterior fica fora
    assert item["cap_usd"] == "5.00"
    assert item["status"] == "ok"  # 60% < warn 80%


@pytest.mark.asyncio
async def test_get_status_classification(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    ws_ok = await make_workspace(db)
    ws_warn = await make_workspace(db)
    ws_stop = await make_workspace(db)
    db.add(_call_row(ws_ok.id, "1.00"))
    db.add(_call_row(ws_warn.id, "4.50"))
    db.add(_call_row(ws_stop.id, "5.57"))
    await db.commit()
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.get("/admin/llm-budget-by-workspace")
    by_id = {i["workspace_id"]: i for i in resp.json()["items"]}
    assert by_id[ws_ok.id]["status"] == "ok"  # 20% do cap 5.00
    assert by_id[ws_warn.id]["status"] == "warn"  # 90% ≥ 80%
    assert by_id[ws_stop.id]["status"] == "hard_stop"  # 111.4% ≥ 110%


@pytest.mark.asyncio
async def test_get_uncapped_workspace(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    ws = await make_workspace(db)
    ws.monthly_llm_budget_usd = None
    db.add(_call_row(ws.id, "999.00"))
    await db.commit()
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.get("/admin/llm-budget-by-workspace")
    item = next(i for i in resp.json()["items"] if i["workspace_id"] == ws.id)
    assert item["status"] == "uncapped"
    assert item["pct_of_cap"] is None
