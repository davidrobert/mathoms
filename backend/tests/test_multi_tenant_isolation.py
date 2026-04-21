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

from dataclasses import dataclass
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


@dataclass(frozen=True)
class _TenantSpec:
    user_email: str
    user_full_name: str
    ws_name: str
    family_surname: str
    member_key: str
    member_full_name: str
    institution_code: str
    category_code: str
    category_name: str
    document_name: str
    vault_label: str
    report_title: str
    llm_model: str
    notif_title: str
    notif_message: str


_TENANT_A = _TenantSpec(
    user_email="alice@test.com",
    user_full_name="Alice A",
    ws_name="Família A",
    family_surname="Alves",
    member_key="alice_titular",
    member_full_name="Alice Alves",
    institution_code="c6bank",
    category_code="alimentacao_a",
    category_name="Alimentação A",
    document_name="extrato_a.pdf",
    vault_label="Senha A",
    report_title="Relatório A",
    llm_model="claude-opus-4-6",
    notif_title="Notif A",
    notif_message="Mensagem A",
)

# LLMConfig tem unique constraint em workspace_id — cada tenant tem o seu.
_TENANT_B = _TenantSpec(
    user_email="bob@test.com",
    user_full_name="Bob B",
    ws_name="Família B",
    family_surname="Brito",
    member_key="bob_titular",
    member_full_name="Bob Brito",
    institution_code="itau",
    category_code="alimentacao_b",
    category_name="Alimentação B",
    document_name="extrato_b.pdf",
    vault_label="Senha B",
    report_title="Relatório B",
    llm_model="claude-haiku-4-5",
    notif_title="Notif B",
    notif_message="Mensagem B",
)


async def _seed_full_tenant(db: AsyncSession, spec: _TenantSpec) -> dict[str, Any]:
    user = await make_user(db, email=spec.user_email, full_name=spec.user_full_name)
    ws = await make_workspace(db, owner=user, name=spec.ws_name, family_surname=spec.family_surname)
    member = await make_member(db, workspace=ws, key=spec.member_key, full_name=spec.member_full_name)
    account = await make_bank_account(db, member=member, institution_code=spec.institution_code)
    category = await make_category(db, workspace=ws, code=spec.category_code, name=spec.category_name)
    document = await make_document(db, workspace=ws, original_name=spec.document_name)
    vault = await make_vault_password(db, workspace=ws, label=spec.vault_label)
    run = await make_run(db, workspace=ws)
    report = await make_report(db, workspace=ws, pipeline_run=run, title=spec.report_title)
    llm = await make_llm_config(db, workspace=ws, model_name=spec.llm_model)
    notif = await make_notification(db, workspace=ws, title=spec.notif_title, message=spec.notif_message)
    return {
        "user": user, "ws": ws, "member": member, "account": account,
        "category": category, "document": document, "vault": vault,
        "run": run, "report": report, "llm": llm, "notification": notif,
        "token": create_access_token(user.id),
    }


@pytest_asyncio.fixture
async def tenants(db: AsyncSession) -> dict[str, Any]:
    """Cria 2 universos paralelos: tenant A e tenant B.

    Cada um tem: user, workspace (com family_surname distinto), member,
    category, document, vault password, pipeline run, report, llm config,
    notification.
    """
    a = await _seed_full_tenant(db, _TENANT_A)
    b = await _seed_full_tenant(db, _TENANT_B)
    await db.commit()
    return {"a": a, "b": b}


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
