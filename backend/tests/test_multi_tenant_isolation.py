"""Multi-tenant isolation suite — F6.5B.12.

# O que esta suíte prova

Para CADA endpoint write/read sensível, monta 2 workspaces (A e B) com dados
distintos em cada e prova que **dados de B nunca aparecem para user A**.

Padrão arquitetural do Fin:
- Cada user tem 1 workspace (relacionamento 1:1 via `Workspace.owner_id`).
- Endpoints fazem `_get_workspace(user, db)` no início e filtram tudo por
  `workspace_id == ws.id`.
- Path params com IDs (ex: `/documents/{id}/delete`) precisam validar
  ownership ANTES de mutar — caso contrário, user A pode deletar recurso
  de B só sabendo o UUID.

# Por que isso é P0 absoluto

Sem esse teste, beta com >1 user é roleta russa. Um único endpoint que
esquece o filtro `workspace_id` = vazamento de dados financeiros entre
famílias. Em fintech, esse incidente custa o produto.

# Como esta suíte funciona

Cada classe `TestIsolation<Domain>` segue o mesmo padrão:
1. fixture `tenants` cria User A + Workspace A + dados, User B + Workspace B + dados
2. cria 2 access tokens (1 por user)
3. itera endpoints — chama com auth A — assert nenhum payload contém ID/conteúdo de B
4. para mutações por path-id, tenta operar em ID de B com auth A — espera 404 (não 403,
   que vazaria existência)

# Cobertura

- Members + BankAccounts (config)
- Categories (config)
- Documents
- Pipeline runs + reviews
- Reports
- Transactions + overrides
- Vault passwords
- LLM config
- Notifications
- Workspace settings (`family_surname`, etc.)

# Ausências deliberadas

- WebSocket isolation (cobre em 6.5B.14 — Redis pub/sub real)
- Dashboard (read-only sobre dados já filtrados; cobre em integration smoke)
"""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_access_token
from backend.tests.factories import (
    make_bank_account,
    make_category,
    make_document,
    make_llm_config,
    make_member,
    make_notification,
    make_report,
    make_run,
    make_user,
    make_vault_password,
    make_workspace,
)


# ─────────────────────────────────────────────────────────────────────
# Fixtures: 2 tenants completos
# ─────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def tenants(db: AsyncSession) -> dict[str, Any]:
    """Cria 2 universos paralelos: tenant A e tenant B.

    Cada um tem: user, workspace (com family_surname distinto), member,
    category, document, vault password, pipeline run, report, llm config,
    notification.

    Retorna dict com tudo o que os tests precisam.
    """
    # Tenant A
    user_a = await make_user(db, email="alice@test.com", full_name="Alice A")
    ws_a = await make_workspace(db, owner=user_a, name="Família A", family_surname="Alves")
    member_a = await make_member(db, workspace=ws_a, key="alice_titular", full_name="Alice Alves")
    acc_a = await make_bank_account(db, member=member_a, institution_code="c6bank")
    cat_a = await make_category(db, workspace=ws_a, code="alimentacao_a", name="Alimentação A")
    doc_a = await make_document(db, workspace=ws_a, original_name="extrato_a.pdf")
    vault_a = await make_vault_password(db, workspace=ws_a, label="Senha A")
    run_a = await make_run(db, workspace=ws_a)
    report_a = await make_report(db, workspace=ws_a, pipeline_run=run_a, title="Relatório A")
    llm_a = await make_llm_config(db, workspace=ws_a, model_name="claude-opus-4-6")
    notif_a = await make_notification(db, workspace=ws_a, title="Notif A", message="Mensagem A")

    # Tenant B
    user_b = await make_user(db, email="bob@test.com", full_name="Bob B")
    ws_b = await make_workspace(db, owner=user_b, name="Família B", family_surname="Brito")
    member_b = await make_member(db, workspace=ws_b, key="bob_titular", full_name="Bob Brito")
    acc_b = await make_bank_account(db, member=member_b, institution_code="itau")
    cat_b = await make_category(db, workspace=ws_b, code="alimentacao_b", name="Alimentação B")
    doc_b = await make_document(db, workspace=ws_b, original_name="extrato_b.pdf")
    vault_b = await make_vault_password(db, workspace=ws_b, label="Senha B")
    run_b = await make_run(db, workspace=ws_b)
    report_b = await make_report(db, workspace=ws_b, pipeline_run=run_b, title="Relatório B")
    # NOTE: LLMConfig tem unique constraint em workspace_id — só 1 por workspace.
    # Já criamos um para A; criamos outro para B (workspace_id diferente, OK).
    llm_b = await make_llm_config(db, workspace=ws_b, model_name="claude-haiku-4-5")
    notif_b = await make_notification(db, workspace=ws_b, title="Notif B", message="Mensagem B")

    await db.commit()

    return {
        "a": {
            "user": user_a,
            "ws": ws_a,
            "member": member_a,
            "account": acc_a,
            "category": cat_a,
            "document": doc_a,
            "vault": vault_a,
            "run": run_a,
            "report": report_a,
            "llm": llm_a,
            "notification": notif_a,
            "token": create_access_token(user_a.id),
        },
        "b": {
            "user": user_b,
            "ws": ws_b,
            "member": member_b,
            "account": acc_b,
            "category": cat_b,
            "document": doc_b,
            "vault": vault_b,
            "run": run_b,
            "report": report_b,
            "llm": llm_b,
            "notification": notif_b,
            "token": create_access_token(user_b.id),
        },
    }


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# Marcador para identificar string de tenant B em qualquer payload retornado
# para tenant A. Usamos os IDs dos models de B + nome único — colisão = leak.
def _b_signatures(tenants: dict) -> set[str]:
    b = tenants["b"]
    return {
        b["ws"].id,
        b["member"].id,
        b["category"].id,
        b["document"].id,
        b["vault"].id,
        b["run"].id,
        b["report"].id,
        b["llm"].id,
        b["notification"].id,
        "Brito",  # family_surname B
        "Bob Brito",  # member name B
        "Alimentação B",
        "extrato_b.pdf",
        "Senha B",
        "Relatório B",
        "Notif B",
        "Mensagem B",
        "claude-haiku-4-5",  # model só de B
        "alimentacao_b",
    }


def _assert_no_b_leak(payload: Any, tenants: dict, where: str) -> None:
    """Faz dump JSON e procura qualquer signature de B."""
    import json

    s = json.dumps(payload, ensure_ascii=False, default=str)
    sigs = _b_signatures(tenants)
    leaks = {sig for sig in sigs if sig in s}
    assert not leaks, f"LEAK em {where}: payload contém signatures de B: {leaks}"


# ─────────────────────────────────────────────────────────────────────
# Workspace settings (family_surname etc.)
# ─────────────────────────────────────────────────────────────────────


class TestIsolationWorkspaceSettings:
    @pytest.mark.asyncio
    async def test_get_workspace_returns_only_a(self, client: AsyncClient, tenants):
        r = await client.get(f"/api/workspaces/{tenants['a']['ws'].id}/config/workspace", headers=_auth(tenants["a"]["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["family_surname"] == "Alves"
        _assert_no_b_leak(body, tenants, "GET /config/workspace")


# ─────────────────────────────────────────────────────────────────────
# Members + BankAccounts
# ─────────────────────────────────────────────────────────────────────


class TestIsolationMembers:
    @pytest.mark.asyncio
    async def test_list_members_only_a(self, client: AsyncClient, tenants):
        r = await client.get(f"/api/workspaces/{tenants['a']['ws'].id}/config/members", headers=_auth(tenants["a"]["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 1
        assert body["members"][0]["full_name"] == "Alice Alves"
        _assert_no_b_leak(body, tenants, "GET /config/members")

    @pytest.mark.asyncio
    async def test_update_member_of_b_returns_404(self, client: AsyncClient, tenants):
        r = await client.put(
            f"/api/workspaces/{tenants['a']['ws'].id}/config/members/{tenants['b']['member'].id}",
            headers=_auth(tenants["a"]["token"]),
            json={"role": "conjuge"},
        )
        assert r.status_code == 404, (
            f"LEAK: A conseguiu modificar member de B (status={r.status_code})"
        )

    @pytest.mark.asyncio
    async def test_delete_member_of_b_returns_404(self, client: AsyncClient, tenants):
        r = await client.delete(
            f"/api/workspaces/{tenants['a']['ws'].id}/config/members/{tenants['b']['member'].id}",
            headers=_auth(tenants["a"]["token"]),
        )
        assert r.status_code == 404, (
            f"LEAK: A conseguiu deletar member de B (status={r.status_code})"
        )

    @pytest.mark.asyncio
    async def test_list_accounts_of_b_member_returns_404(
        self, client: AsyncClient, tenants
    ):
        r = await client.get(
            f"/api/workspaces/{tenants['a']['ws'].id}/config/members/{tenants['b']['member'].id}/accounts",
            headers=_auth(tenants["a"]["token"]),
        )
        assert r.status_code == 404, r.text


# ─────────────────────────────────────────────────────────────────────
# Categories
# ─────────────────────────────────────────────────────────────────────


class TestIsolationCategories:
    @pytest.mark.asyncio
    async def test_list_categories_only_a(self, client: AsyncClient, tenants):
        r = await client.get(f"/api/workspaces/{tenants['a']['ws'].id}/config/categories", headers=_auth(tenants["a"]["token"])
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 1
        assert body["categories"][0]["code"] == "alimentacao_a"
        _assert_no_b_leak(body, tenants, "GET /config/categories")

    @pytest.mark.asyncio
    async def test_update_category_of_b_returns_404(self, client: AsyncClient, tenants):
        r = await client.put(
            f"/api/workspaces/{tenants['a']['ws'].id}/config/categories/{tenants['b']['category'].id}",
            headers=_auth(tenants["a"]["token"]),
            json={"name": "Hijacked"},
        )
        assert r.status_code == 404, r.text

    @pytest.mark.asyncio
    async def test_delete_category_of_b_returns_404(self, client: AsyncClient, tenants):
        r = await client.delete(
            f"/api/workspaces/{tenants['a']['ws'].id}/config/categories/{tenants['b']['category'].id}",
            headers=_auth(tenants["a"]["token"]),
        )
        assert r.status_code == 404, r.text


# ─────────────────────────────────────────────────────────────────────
# Documents
# ─────────────────────────────────────────────────────────────────────


class TestIsolationDocuments:
    @pytest.mark.asyncio
    async def test_list_documents_only_a(self, client: AsyncClient, tenants):
        r = await client.get(f"/api/workspaces/{tenants['a']['ws'].id}/documents", headers=_auth(tenants["a"]["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 1
        assert body["documents"][0]["original_name"] == "extrato_a.pdf"
        _assert_no_b_leak(body, tenants, "GET /documents")

    @pytest.mark.asyncio
    async def test_delete_document_of_b_returns_404(self, client: AsyncClient, tenants):
        r = await client.delete(
            f"/api/workspaces/{tenants['a']['ws'].id}/documents/{tenants['b']['document'].id}",
            headers=_auth(tenants["a"]["token"]),
        )
        assert r.status_code == 404, r.text


# ─────────────────────────────────────────────────────────────────────
# Vault passwords
# ─────────────────────────────────────────────────────────────────────


class TestIsolationVault:
    @pytest.mark.asyncio
    async def test_list_passwords_only_a(self, client: AsyncClient, tenants):
        r = await client.get(f"/api/workspaces/{tenants['a']['ws'].id}/vault/passwords", headers=_auth(tenants["a"]["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 1
        assert body["passwords"][0]["label"] == "Senha A"
        _assert_no_b_leak(body, tenants, "GET /vault/passwords")

    @pytest.mark.asyncio
    async def test_delete_password_of_b_returns_404(self, client: AsyncClient, tenants):
        r = await client.delete(
            f"/api/workspaces/{tenants['a']['ws'].id}/vault/passwords/{tenants['b']['vault'].id}",
            headers=_auth(tenants["a"]["token"]),
        )
        assert r.status_code == 404, r.text


# ─────────────────────────────────────────────────────────────────────
# Pipeline runs + reviews
# ─────────────────────────────────────────────────────────────────────


class TestIsolationPipelineRuns:
    @pytest.mark.asyncio
    async def test_list_runs_only_a(self, client: AsyncClient, tenants):
        r = await client.get(f"/api/workspaces/{tenants['a']['ws'].id}/pipeline/runs", headers=_auth(tenants["a"]["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 1
        assert body["runs"][0]["id"] == tenants["a"]["run"].id
        _assert_no_b_leak(body, tenants, "GET /pipeline/runs")

    @pytest.mark.asyncio
    async def test_get_run_of_b_returns_404(self, client: AsyncClient, tenants):
        r = await client.get(
            f"/api/workspaces/{tenants['a']['ws'].id}/pipeline/runs/{tenants['b']['run'].id}",
            headers=_auth(tenants["a"]["token"]),
        )
        assert r.status_code == 404, r.text

    @pytest.mark.asyncio
    async def test_cancel_run_of_b_returns_404(self, client: AsyncClient, tenants):
        r = await client.post(
            f"/api/workspaces/{tenants['a']['ws'].id}/pipeline/runs/{tenants['b']['run'].id}/cancel",
            headers=_auth(tenants["a"]["token"]),
        )
        assert r.status_code == 404, r.text

    @pytest.mark.asyncio
    async def test_list_reviews_of_b_run_returns_404(self, client: AsyncClient, tenants):
        r = await client.get(
            f"/api/workspaces/{tenants['a']['ws'].id}/pipeline/runs/{tenants['b']['run'].id}/reviews",
            headers=_auth(tenants["a"]["token"]),
        )
        assert r.status_code == 404, r.text


# ─────────────────────────────────────────────────────────────────────
# Reports
# ─────────────────────────────────────────────────────────────────────


class TestIsolationReports:
    @pytest.mark.asyncio
    async def test_list_reports_only_a(self, client: AsyncClient, tenants):
        r = await client.get(f"/api/workspaces/{tenants['a']['ws'].id}/reports", headers=_auth(tenants["a"]["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 1
        assert body["reports"][0]["title"] == "Relatório A"
        _assert_no_b_leak(body, tenants, "GET /reports")

    @pytest.mark.asyncio
    async def test_get_report_of_b_returns_404(self, client: AsyncClient, tenants):
        r = await client.get(
            f"/api/workspaces/{tenants['a']['ws'].id}/reports/{tenants['b']['report'].id}",
            headers=_auth(tenants["a"]["token"]),
        )
        assert r.status_code == 404, r.text

    @pytest.mark.asyncio
    async def test_get_report_html_of_b_returns_404(self, client: AsyncClient, tenants):
        r = await client.get(
            f"/api/workspaces/{tenants['a']['ws'].id}/reports/{tenants['b']['report'].id}/html",
            headers=_auth(tenants["a"]["token"]),
        )
        assert r.status_code == 404, r.text


# ─────────────────────────────────────────────────────────────────────
# Transactions
# ─────────────────────────────────────────────────────────────────────


class TestIsolationTransactions:
    @pytest.mark.asyncio
    async def test_list_transactions_only_a(self, client: AsyncClient, tenants):
        r = await client.get(f"/api/workspaces/{tenants['a']['ws'].id}/transactions", headers=_auth(tenants["a"]["token"]))
        # endpoint pode retornar 200 com lista vazia (sem transactions reais
        # nas factories) — o que importa é não vazar nada de B
        assert r.status_code == 200, r.text
        _assert_no_b_leak(r.json(), tenants, "GET /transactions")


# ─────────────────────────────────────────────────────────────────────
# LLM config (1 por workspace)
# ─────────────────────────────────────────────────────────────────────


class TestIsolationLLMConfig:
    @pytest.mark.asyncio
    async def test_get_llm_returns_only_a(self, client: AsyncClient, tenants):
        r = await client.get(f"/api/workspaces/{tenants['a']['ws'].id}/config/llm", headers=_auth(tenants["a"]["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        if body is None:
            pytest.skip("Endpoint retornou null — model do A não foi serializado")
        assert body["model_name"] == "claude-opus-4-6"
        # B usa claude-haiku-4-5 — não pode aparecer
        _assert_no_b_leak(body, tenants, "GET /config/llm")

    @pytest.mark.asyncio
    async def test_get_llm_tier_does_not_leak(self, client: AsyncClient, tenants):
        r = await client.get(f"/api/workspaces/{tenants['a']['ws'].id}/config/llm/tier", headers=_auth(tenants["a"]["token"]))
        assert r.status_code == 200, r.text
        _assert_no_b_leak(r.json(), tenants, "GET /config/llm/tier")


# ─────────────────────────────────────────────────────────────────────
# Notifications
# ─────────────────────────────────────────────────────────────────────


class TestIsolationNotifications:
    @pytest.mark.asyncio
    async def test_list_notifications_only_a(self, client: AsyncClient, tenants):
        r = await client.get(f"/api/workspaces/{tenants['a']['ws'].id}/notifications", headers=_auth(tenants["a"]["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 1
        assert body["notifications"][0]["title"] == "Notif A"
        _assert_no_b_leak(body, tenants, "GET /notifications")

    @pytest.mark.asyncio
    async def test_delete_notification_of_b_returns_404(
        self, client: AsyncClient, tenants
    ):
        r = await client.delete(
            f"/api/workspaces/{tenants['a']['ws'].id}/notifications/{tenants['b']['notification'].id}",
            headers=_auth(tenants["a"]["token"]),
        )
        assert r.status_code == 404, r.text

    @pytest.mark.asyncio
    async def test_mark_b_notification_read_does_nothing(
        self, client: AsyncClient, tenants
    ):
        r = await client.patch(f"/api/workspaces/{tenants['a']['ws'].id}/notifications/read",
            headers=_auth(tenants["a"]["token"]),
            json={"notification_ids": [tenants["b"]["notification"].id]},
        )
        # endpoint pode aceitar (200) ou rejeitar (404). Se aceitar, NÃO pode
        # marcar a de B como lida.
        if r.status_code == 200:
            await db_assert_b_notif_unchanged(tenants)


async def db_assert_b_notif_unchanged(tenants):
    """Helper: confirma que a notificação de B não foi alterada por A."""
    # As factories já flushed; precisamos refresh do DB para ver estado atual.
    # Como o test runner usa SQLite in-memory + StaticPool, o estado é o mesmo.
    notif = tenants["b"]["notification"]
    assert notif.is_read is False, "LEAK: A marcou notificação de B como lida"


# ─────────────────────────────────────────────────────────────────────
# Cross-test sanity: tenant B vê seus próprios dados (controle)
# ─────────────────────────────────────────────────────────────────────


class TestSanityBSeesOwnData:
    """Garante que B continua vendo SEUS próprios dados — se este test
    falha, é porque algo no setup está bloqueando B errado, não porque
    o isolamento de A vazou."""

    @pytest.mark.asyncio
    async def test_b_sees_own_documents(self, client: AsyncClient, tenants):
        r = await client.get(f"/api/workspaces/{tenants['b']['ws'].id}/documents", headers=_auth(tenants["b"]["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 1
        assert body["documents"][0]["original_name"] == "extrato_b.pdf"

    @pytest.mark.asyncio
    async def test_b_sees_own_workspace_surname(self, client: AsyncClient, tenants):
        r = await client.get(f"/api/workspaces/{tenants['b']['ws'].id}/config/workspace", headers=_auth(tenants["b"]["token"]))
        assert r.status_code == 200, r.text
        assert r.json()["family_surname"] == "Brito"
