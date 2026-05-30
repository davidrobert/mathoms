"""LGPD Art.37 (ADR-275 l7) — auditoria de acesso: guarda de cobertura sobre as rotas GET sensíveis (auditada OU allowlist justificada, default invertido anti-drift), guarda anti-PII de escrita (CPF/valor rejeitados), e integração provando que GET auditado grava 1 linha em ``audit_logs`` sem PII enquanto rota allowlist não grava."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.main import app
from backend.app.models.audit_log import AuditLog
from backend.app.services.access_audit import (
    AccessAuditDetails,
    AccessAuditPIIError,
    assert_pii_free,
)
from backend.app.services.audit import READ_ACCESS_ACTIONS

# --- Superfície sensível e allowlist justificada -----------------------------

# Segmentos de path que servem dado financeiro/PII do titular (Art.37).
_SENSITIVE_SEGMENTS = ("/reports", "/transactions", "/config/members", "/documents")

# Rotas GET na superfície sensível que NÃO precisam de audit de acesso, com
# justificativa explícita. Default é invertido: rota nova não-allowlistada sem
# dependency falha o teste (força decisão consciente — anti-drift).
_ACCESS_AUDIT_ALLOWLIST: dict[str, str] = {
    "/api/v1/workspaces/{workspace_id}/reports/{report_id}/tasks": "status de tasks, sem payload financeiro",
    "/api/v1/workspaces/{workspace_id}/reports/publications": "metadados de publicação (status/share), sem payload financeiro",
    "/api/v1/workspaces/{workspace_id}/reports/{period_yyyymm}/publication": "metadados de publicação, sem payload financeiro",
    "/api/v1/workspaces/{workspace_id}/reports/{report_id}/notes": "410 Gone (ADR-154 M2) — serve nenhum dado",
    "/api/v1/workspaces/{workspace_id}/reports/{report_id}/kanban": "410 Gone (ADR-154 M2) — serve nenhum dado",
    "/api/v1/workspaces/{workspace_id}/documents": "lista de metadados de documento (nome/tipo/status), não conteúdo extraído",
}


def _is_sensitive_titular_get(route) -> bool:
    methods = getattr(route, "methods", None) or set()
    path = getattr(route, "path", "")
    return (
        "GET" in methods
        and getattr(route, "include_in_schema", True)
        and "/workspaces/{workspace_id}" in path
        and any(seg in path for seg in _SENSITIVE_SEGMENTS)
    )


def _has_access_audit(route) -> bool:
    return any(getattr(dep.call, "_is_access_audit", False) for dep in route.dependant.dependencies)


def test_every_sensitive_get_is_audited_or_allowlisted():
    """Anti-drift: toda GET sensível do titular tem audit de acesso OU está na allowlist justificada."""
    offenders = []
    for route in app.routes:
        if not hasattr(route, "dependant") or not _is_sensitive_titular_get(route):
            continue
        if _has_access_audit(route):
            continue
        if route.path in _ACCESS_AUDIT_ALLOWLIST:
            continue
        offenders.append(route.path)
    assert (
        not offenders
    ), f"rotas GET sensíveis sem audit de acesso nem allowlist (ADR-275): {sorted(set(offenders))}"


def test_allowlist_has_no_stale_entries():
    """Allowlist não acumula entradas órfãs — cada path allowlistado existe e não é auditado."""
    live_paths = {
        r.path
        for r in app.routes
        if hasattr(r, "dependant") and _is_sensitive_titular_get(r) and not _has_access_audit(r)
    }
    stale = set(_ACCESS_AUDIT_ALLOWLIST) - live_paths
    assert not stale, f"entradas de allowlist órfãs (remova): {sorted(stale)}"


# --- Guarda anti-PII de escrita ----------------------------------------------


def test_assert_pii_free_rejects_cpf():
    with pytest.raises(AccessAuditPIIError):
        assert_pii_free({"route": "/x", "leak": "000.000.000-00"})


def test_assert_pii_free_rejects_monetary():
    with pytest.raises(AccessAuditPIIError):
        assert_pii_free({"route": "/x", "leak": "saldo 1.234,56"})


def test_assert_pii_free_passes_benign_metadata():
    payload = {"method": "GET", "route": "/reports/{report_id}/data", "query_keys": ["period"]}
    assert assert_pii_free(payload) == payload


def test_access_details_forbids_extra_field():
    with pytest.raises(ValidationError):
        AccessAuditDetails(method="GET", route="/x", saldo="999999")  # type: ignore[call-arg]


# --- Integração: choke-point grava acesso, allowlist não ---------------------


async def _count_audit(db: AsyncSession, action: str | None = None) -> int:
    # rollback encerra a txn aberta da sessão → próxima query lê snapshot fresco
    # (a dependency de acesso commitou numa sessão paralela; StaticPool compartilha
    # a conexão, mas a sessão do teste precisa reabrir a leitura).
    await db.rollback()
    stmt = select(func.count()).select_from(AuditLog)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    return (await db.execute(stmt)).scalar_one()


@pytest.mark.asyncio
async def test_audited_get_writes_access_row(auth_client: AsyncClient, db: AsyncSession):
    before = await _count_audit(db, "report.read")
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports")
    assert resp.status_code == 200
    after = await _count_audit(db, "report.read")
    assert after == before + 1

    await db.rollback()
    row = (
        (
            await db.execute(
                select(AuditLog)
                .where(AuditLog.action == "report.read")
                .order_by(AuditLog.created_at.desc())
            )
        )
        .scalars()
        .first()
    )
    assert row is not None
    assert row.workspace_id == auth_client.ws_id
    assert row.actor_user_id is not None
    assert row.resource_type == "report"
    assert "report.read" in READ_ACCESS_ACTIONS
    # details é só metadado — zero PII.
    assert row.details["method"] == "GET"
    assert "reports" in row.details["route"]
    assert assert_pii_free(row.details) == row.details


@pytest.mark.asyncio
async def test_allowlisted_get_writes_no_access_row(auth_client: AsyncClient, db: AsyncSession):
    before = await _count_audit(db)
    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/nonexistent-id/tasks"
    )
    # 404 (report inexistente) ou 200 — em qualquer caso, sem linha de audit.
    assert resp.status_code in (200, 404)
    after = await _count_audit(db)
    assert after == before


@pytest.mark.asyncio
async def test_resource_id_captured_for_path_param(auth_client: AsyncClient, db: AsyncSession):
    rid = "report-xyz"
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}")
    # 404 esperado (não existe) — mas o acesso já foi auditado antes do handler.
    assert resp.status_code in (200, 404)
    await db.rollback()
    row = (
        (
            await db.execute(
                select(AuditLog).where(
                    AuditLog.action == "report.read", AuditLog.resource_id == rid
                )
            )
        )
        .scalars()
        .first()
    )
    assert row is not None
    assert row.resource_id == rid
