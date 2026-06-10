"""Integration tests for Phase 3B: Config CRUD APIs, import/export, fallback defaults."""

import pytest
import pytest_asyncio
from httpx import AsyncClient

# =============================================================================
# Family Members — CRUD
# =============================================================================


class TestMembersAPI:
    @pytest.mark.asyncio
    async def test_list_members_fallback(self, auth_client: AsyncClient):
        """Pos-A7.5 (ADR-134): ``config/family_members.json`` não existe mais —
        endpoint legacy retorna lista vazia para workspaces sem rows. Fallback
        de disco morreu junto com o cutover; defaults agora vêm do DB seed."""
        resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/members")
        assert resp.status_code == 200
        data = resp.json()
        # Sem rows no DB e sem fallback de disco: lista vazia.
        assert data["total"] == 0
        assert data["members"] == []

    @pytest.mark.asyncio
    async def test_create_member(self, auth_client: AsyncClient):
        # CPF gerado por tests/utils/cpf.py seed=42  # noqa: PII-ok
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members",
            json={
                "key": "david",
                "full_name": "David Robert Camargo",
                "short_name": "David",
                "cpf": "910.428.398-01",  # noqa: PII-ok
                "birth_date": "1981-09-05",
                "role": "titular",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["key"] == "david"
        assert data["full_name"] == "David Robert Camargo"
        assert data["cpf"] == "910.428.398-01"  # noqa: PII-ok (gerado por tests/utils/cpf.py seed=42)
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_create_member_duplicate_key(self, auth_client: AsyncClient):
        await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members",
            json={
                "key": "dup",
                "full_name": "Test",
                "short_name": "T",
                "role": "titular",
            },
        )
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members",
            json={
                "key": "dup",
                "full_name": "Test2",
                "short_name": "T2",
                "role": "titular",
            },
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_member_auto_key_from_full_name(self, auth_client: AsyncClient):
        """Sem `key` no JSON — backend gera slug único a partir do nome."""
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members",
            json={
                "full_name": "Maria Silva Costa",
                "short_name": "Maria",
                "role": "titular",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["key"] == "maria_silva_costa"
        assert data["full_name"] == "Maria Silva Costa"

    @pytest.mark.asyncio
    async def test_create_member_auto_key_collision_suffix(self, auth_client: AsyncClient):
        await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members",
            json={
                "full_name": "João Teste",
                "short_name": "J",
                "role": "titular",
            },
        )
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members",
            json={
                "full_name": "João Teste",
                "short_name": "J2",
                "role": "conjuge",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["key"] == "joao_teste_1"

    @pytest.mark.asyncio
    async def test_create_member_birth_name_persists(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members",
            json={
                "key": "bn",
                "full_name": "Test Birth",
                "short_name": "T",
                "role": "titular",
                "birth_name": "Nome Antigo de Solteira",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["birth_name"] == "Nome Antigo de Solteira"
        mid = resp.json()["id"]
        get_one = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/members")
        keys = {m["key"]: m for m in get_one.json()["members"]}
        assert keys["bn"]["birth_name"] == "Nome Antigo de Solteira"
        upd = await auth_client.put(
            f"/api/workspaces/{auth_client.ws_id}/config/members/{mid}", json={"birth_name": ""}
        )
        assert upd.status_code == 200
        assert upd.json().get("birth_name") in (None, "")

    @pytest.mark.asyncio
    async def test_list_members_from_db(self, auth_client: AsyncClient):
        """After creating a member, list returns from DB (not fallback)."""
        await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members",
            json={
                "key": "test_list",
                "full_name": "Test",
                "short_name": "T",
                "role": "titular",
            },
        )
        resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/members")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["members"][0]["key"] == "test_list"

    @pytest.mark.asyncio
    async def test_update_member(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members",
            json={
                "key": "upd",
                "full_name": "Before",
                "short_name": "B",
                "role": "titular",
            },
        )
        member_id = create_resp.json()["id"]
        resp = await auth_client.put(
            f"/api/workspaces/{auth_client.ws_id}/config/members/{member_id}",
            json={
                "full_name": "After",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "After"
        assert resp.json()["key"] == "upd"

    @pytest.mark.asyncio
    async def test_delete_member(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members",
            json={
                "key": "del",
                "full_name": "Delete Me",
                "short_name": "D",
                "role": "titular",
            },
        )
        member_id = create_resp.json()["id"]
        resp = await auth_client.delete(
            f"/api/workspaces/{auth_client.ws_id}/config/members/{member_id}"
        )
        assert resp.status_code == 204

        resp = await auth_client.delete(
            f"/api/workspaces/{auth_client.ws_id}/config/members/{member_id}"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_member_invalid_cpf(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members",
            json={
                "key": "bad",
                "full_name": "Bad CPF",
                "short_name": "B",
                "role": "titular",
                "cpf": "123",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_member_invalid_role(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members",
            json={
                "key": "bad",
                "full_name": "Bad Role",
                "short_name": "B",
                "role": "ceo",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_members_unauthorized(self, client: AsyncClient):
        resp = await client.get(
            "/api/workspaces/00000000-0000-0000-0000-000000000000/config/members"
        )
        assert resp.status_code in (401, 403)


# =============================================================================
# Bank Accounts — nested CRUD
# =============================================================================


class TestAccountsAPI:
    @pytest.mark.asyncio
    async def test_account_lifecycle(self, auth_client: AsyncClient):
        m_resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members",
            json={
                "key": "acc_test",
                "full_name": "Acc",
                "short_name": "A",
                "role": "titular",
            },
        )
        member_id = m_resp.json()["id"]

        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/members/{member_id}/accounts",
            json={
                "institution_code": "itau",
                "account_type": "extratoconta",
                "agency": "001",
            },
        )
        assert resp.status_code == 201
        acc_id = resp.json()["id"]

        resp = await auth_client.get(
            f"/api/workspaces/{auth_client.ws_id}/config/members/{member_id}/accounts"
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        resp = await auth_client.put(
            f"/api/workspaces/{auth_client.ws_id}/config/members/{member_id}/accounts/{acc_id}",
            json={
                "institution_code": "bradesco",
                "account_type": "extratopoupanca",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["institution_code"] == "bradesco"

        resp = await auth_client.delete(
            f"/api/workspaces/{auth_client.ws_id}/config/members/{member_id}/accounts/{acc_id}"
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_account_member_not_found(self, auth_client: AsyncClient):
        resp = await auth_client.get(
            f"/api/workspaces/{auth_client.ws_id}/config/members/nonexistent/accounts"
        )
        assert resp.status_code == 404


# =============================================================================
# Categories — CRUD legado removido em A12.cat-legacy-sunset (ADR-283 §B).
# Caminho moderno coberto em test_category_overrides_api.py.
# =============================================================================


class TestCategoriesLegacyEndpointGone:
    @pytest.mark.asyncio
    async def test_legacy_categories_endpoint_returns_404(self, auth_client: AsyncClient):
        resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/categories")
        assert resp.status_code == 404


# =============================================================================
# Pipeline Config — GET/PUT
# =============================================================================


class TestPipelineConfigAPI:
    @pytest.mark.asyncio
    async def test_get_fallback(self, auth_client: AsyncClient):
        resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/pipeline")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("llm") is not None or data.get("qa_thresholds") is not None

    @pytest.mark.asyncio
    async def test_put_partial_merge(self, auth_client: AsyncClient):
        resp = await auth_client.put(
            f"/api/workspaces/{auth_client.ws_id}/config/pipeline",
            json={
                "llm": {"model": "gpt-4o", "max_tokens": 2000, "confidence_threshold": 0.9},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm"]["model"] == "gpt-4o"
        assert data["llm"]["max_tokens"] == 2000

    @pytest.mark.asyncio
    async def test_put_preserves_unset_fields(self, auth_client: AsyncClient):
        await auth_client.put(
            f"/api/workspaces/{auth_client.ws_id}/config/pipeline",
            json={
                "llm": {"model": "gpt-4o", "max_tokens": 2000, "confidence_threshold": 0.9},
            },
        )
        resp = await auth_client.put(
            f"/api/workspaces/{auth_client.ws_id}/config/pipeline",
            json={
                "qa_thresholds": {"score_diff_max": 2.0},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["qa_thresholds"]["score_diff_max"] == 2.0


# =============================================================================
# Institution Config — GET/PUT
# =============================================================================


class TestInstitutionConfigAPI:
    @pytest.mark.asyncio
    async def test_get_fallback(self, auth_client: AsyncClient):
        """Pos-A7.5: ``config/institutions.json`` deletado — endpoint legacy
        retorna ``config_json={}`` para workspaces sem rows. ``institution_catalog``
        global (A7.3) cobre o caso novo via ``/category-overrides/resolved``."""
        resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/institutions")
        assert resp.status_code == 200
        data = resp.json()
        assert "config_json" in data
        # Sem fallback de disco e sem row: blob vazio.
        assert data["config_json"] == {}

    @pytest.mark.asyncio
    async def test_put_and_get(self, auth_client: AsyncClient):
        payload = {
            "config_json": {"banco_canonical": {"nubank": "Nubank"}, "institution_patterns": []}
        }
        resp = await auth_client.put(
            f"/api/workspaces/{auth_client.ws_id}/config/institutions", json=payload
        )
        assert resp.status_code == 200

        resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/institutions")
        assert resp.json()["config_json"]["banco_canonical"]["nubank"] == "Nubank"


# =============================================================================
# Report Layout — GET/PUT
# =============================================================================


class TestReportLayoutAPI:
    @pytest.mark.asyncio
    async def test_get_fallback(self, auth_client: AsyncClient):
        resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/report-layout")
        assert resp.status_code == 200
        data = resp.json()
        assert "config_json" in data

    @pytest.mark.asyncio
    async def test_put_and_get(self, auth_client: AsyncClient):
        payload = {"config_json": {"version": "2.0", "estrategico": {"sections": []}}}
        resp = await auth_client.put(
            f"/api/workspaces/{auth_client.ws_id}/config/report-layout", json=payload
        )
        assert resp.status_code == 200

        resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/report-layout")
        assert resp.json()["config_json"]["version"] == "2.0"


# =============================================================================
# Import / Export
# =============================================================================


class TestImportExport:
    @pytest.mark.asyncio
    async def test_import_family_members(self, auth_client: AsyncClient):
        payload = {
            "family_members": {
                "membros": {
                    "alice": {
                        "nome_completo": "Alice Test",
                        "nome_curto": "Alice",
                        "papel": "titular",
                    },
                    "bob": {"nome_completo": "Bob Test", "nome_curto": "Bob", "papel": "conjuge"},
                },
                "banco_membro": {"itau": "alice", "bradesco": "bob"},
            }
        }
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/import", json=payload
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == ["family_members"]

        resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/members")
        assert resp.json()["total"] == 2
        keys = {m["key"] for m in resp.json()["members"]}
        assert keys == {"alice", "bob"}

    @pytest.mark.asyncio
    async def test_import_categorization(self, auth_client: AsyncClient):
        payload = {
            "categorization": {
                "expense_keywords": {"moradia": ["ENEL", "SABESP"]},
                "income_keywords": {"receita_pj": ["ARVO"]},
            }
        }
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/import", json=payload
        )
        assert resp.status_code == 200
        assert "categorization" in resp.json()["imported"]

        # CRUD legado /config/categories removido (A12.cat-legacy-sunset);
        # round-trip verificado via /config/export, que lê a mesma tabela.
        resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/export")
        categorization = resp.json()["categorization"]
        assert "moradia" in categorization["expense_keywords"]
        assert "receita_pj" in categorization["income_keywords"]

    @pytest.mark.asyncio
    async def test_import_pipeline_blob(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/import",
            json={
                "pipeline": {"llm": {"model": "imported-model"}},
            },
        )
        assert resp.status_code == 200
        resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/pipeline")
        assert resp.json()["llm"]["model"] == "imported-model"

    @pytest.mark.asyncio
    async def test_export_defaults(self, auth_client: AsyncClient):
        """Export with empty DB → returns global defaults."""
        resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/export")
        assert resp.status_code == 200
        data = resp.json()
        assert "family_members" in data
        assert "categorization" in data
        assert "pipeline" in data
        assert "institutions" in data
        assert "report_layout" in data

    @pytest.mark.asyncio
    async def test_import_export_roundtrip(self, auth_client: AsyncClient):
        """Import → export → data matches."""
        import_payload = {
            "family_members": {
                "membros": {
                    "rt_user": {
                        "nome_completo": "Roundtrip User",
                        "nome_curto": "RT",
                        "papel": "titular",
                    },
                },
            },
            "categorization": {
                "expense_keywords": {"rt_cat": ["KEYWORD"]},
                "income_keywords": {},
            },
            "pipeline": {"llm": {"model": "rt-model"}},
            "institutions": {"banco_canonical": {"rt_bank": "RT Bank"}},
            "report_layout": {"version": "rt"},
        }
        await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/import", json=import_payload
        )

        export_resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/export")
        data = export_resp.json()

        assert "rt_user" in data["family_members"]["membros"]
        assert data["family_members"]["membros"]["rt_user"]["nome_completo"] == "Roundtrip User"
        assert "rt_cat" in data["categorization"]["expense_keywords"]
        assert data["pipeline"]["llm"]["model"] == "rt-model"
        assert data["institutions"]["banco_canonical"]["rt_bank"] == "RT Bank"
        assert data["report_layout"]["version"] == "rt"

    @pytest.mark.asyncio
    async def test_import_partial(self, auth_client: AsyncClient):
        """Import only some configs — others remain unaffected."""
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/config/import",
            json={
                "pipeline": {"test": True},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == ["pipeline"]
        assert resp.json()["total"] == 1
