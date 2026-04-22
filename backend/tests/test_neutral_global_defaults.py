"""Neutral global defaults — F6.5E.6 (systemic fix fallback-leak class).

# Por que este arquivo existe

BUG-004 fix corrigiu UM caminho de leak: CPF do founder vinha pelo fallback de
`/api/config/members` quando o tenant novo não tinha members. F6.5E.6 estende
para a CLASSE INTEIRA: nenhum campo identitário do `config/family_members.json`
global pode chegar a um tenant via fallback ou export.

# Política aplicada

- `_convert_members_json_to_schemas` (fallback de GET /config/members):
  full_name, short_name, birth_date, cpf → todos placeholders neutros
- `_export_family_members` (export para JSON pipeline-compatible):
  quando tenant tem 0 members → retorna estrutura vazia, não dump do global

# O que NÃO testamos aqui

- Categories: o fallback de categorization.json contém só labels genéricas
  ("alimentacao", "salario") — não é PII.
- Pipeline/Institutions/Layout: blobs de config técnica, não identidade.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

from backend.app.core.security import create_access_token
from backend.tests.factories import make_user, make_workspace

# Sinais identitários conhecidos do `config/family_members.json` global do projeto.
# Se algum desses aparecer em payload servido para tenant novo, é leak.
_FOUNDER_LEAK_SIGNALS = {
    "David Robert",  # nome do founder no global
    "David Robert Camargo Ferreira Campos",
    "Mariana Ferreira Campos",
    "Theo Ferreira Campos",
    "Ferreira Campos",  # familia.sobrenome
    "1981-09-05",  # data_nascimento founder
    "1986-08-30",
    "2025-07-18",
}


@pytest_asyncio.fixture
async def fresh_user_and_token(db) -> tuple[str, str, str]:
    """User novo SEM members no DB — força o caminho de fallback.

    Returns (user_id, token, workspace_id). Após F9/ADR-072, endpoints
    tenant-scoped exigem path param `{workspace_id}`.
    """
    u = await make_user(db, email="fresh@test.com", full_name="Fresh User")
    ws = await make_workspace(db, owner=u, name="Workspace Fresh")
    await db.commit()
    return u.id, create_access_token(u.id), ws.id


def _assert_no_founder_leak(payload, where: str) -> None:
    import json

    s = json.dumps(payload, ensure_ascii=False, default=str)
    leaks = {sig for sig in _FOUNDER_LEAK_SIGNALS if sig in s}
    assert not leaks, f"FOUNDER LEAK em {where}: payload contém identidade do founder: {leaks}"


# ─────────────────────────────────────────────────────────────────────
# 1. GET /config/members — fallback não vaza identidade
# ─────────────────────────────────────────────────────────────────────


class TestMembersFallbackNeutral:
    @pytest.mark.asyncio
    async def test_fallback_returns_neutral_placeholders(
        self, client: AsyncClient, fresh_user_and_token
    ):
        _, token, ws_id = fresh_user_and_token
        r = await client.get(
            f"/api/workspaces/{ws_id}/config/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        _assert_no_founder_leak(body, "GET /config/members fallback")

        # Estrutural: pelo menos 1 placeholder (titular default)
        if body["total"] > 0:
            for m in body["members"]:
                # Nomes devem ser claramente "Exemplo" — nunca founder
                assert (
                    "Exemplo" in m["full_name"]
                ), f"Esperava nome placeholder com 'Exemplo', got {m['full_name']!r}"
                assert m["cpf"] is None, "CPF não pode ser exposto via fallback"
                assert m["birth_date"] is None, "data_nascimento não pode ser exposta via fallback"


# ─────────────────────────────────────────────────────────────────────
# 2. GET /config/export — não vaza JSON global cru para tenant vazio
# ─────────────────────────────────────────────────────────────────────


class TestExportFallbackNeutral:
    @pytest.mark.asyncio
    async def test_export_for_empty_tenant_does_not_dump_global(
        self, client: AsyncClient, fresh_user_and_token
    ):
        _, token, ws_id = fresh_user_and_token
        r = await client.get(
            f"/api/workspaces/{ws_id}/config/export",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        _assert_no_founder_leak(body, "GET /config/export para tenant vazio")

        # Estrutural: family_members deve ser objeto com `membros: {}`
        fm = body.get("family_members") or {}
        assert (
            fm.get("membros", {}) == {}
        ), f"Export para tenant vazio deveria ter membros={{}}, got {fm.get('membros')!r}"


# ─────────────────────────────────────────────────────────────────────
# 3. Sanity: tenant COM members vê os SEUS dados (não regressão)
# ─────────────────────────────────────────────────────────────────────


class TestPopulatedTenantStillWorks:
    """Garante que o fix neutralizador não quebrou o caminho com dados reais."""

    @pytest.mark.asyncio
    async def test_tenant_with_members_sees_own_data(self, client, db):
        from backend.tests.factories import make_member

        u = await make_user(db, email="populated@test.com")
        ws = await make_workspace(db, owner=u, family_surname="Sobrenome Próprio")
        await make_member(db, workspace=ws, full_name="Pessoa Real Tenant", role="titular")
        await db.commit()
        token = create_access_token(u.id)

        r = await client.get(
            f"/api/workspaces/{ws.id}/config/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # Vê seus próprios dados
        assert body["total"] == 1
        assert body["members"][0]["full_name"] == "Pessoa Real Tenant"
        # NÃO vê founder
        _assert_no_founder_leak(body, "GET /config/members tenant populado")
