"""Testes do `pipeline_adapter` (ADR-075 §F8.4).

Valida que os payloads gerados pelo adapter são compatíveis com o formato
esperado pelo pipeline legado:
- `goals.json` → `independencia_financeira.{if_meta, trs_pct, ...}`
- E5 tasks → `tarefas[{num, tarefa, categoria, prazo, prioridade, status, ref}]`
- `tarefas.md` → markdown com seções S/R/O e Concluídas
"""

from __future__ import annotations

from datetime import date

import pytest

from backend.app.services.pipeline_adapter import (
    build_goals_payload,
    build_tarefas_md,
    build_tasks_payload,
)
from backend.tests import factories

# ═══════════════════════════════════════════════════════════════════════
# Goals payload
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_goals_payload_contains_if_from_db(db):
    """Adapter devolve `independencia_financeira` no formato do goals.json."""
    ws = await factories.make_workspace(db)
    await factories.make_if_goal(
        db,
        workspace=ws,
        renda_passiva_mensal_brl=30000,
        trs_pct=5.0,
    )
    await db.commit()

    payload = await build_goals_payload(ws.id, db=db)
    section = payload["independencia_financeira"]
    assert section["if_meta"] == 7_200_000.0
    assert section["trs_pct"] == 5.0
    assert section["renda_passiva_meta_mensal"] == 30000
    assert section["_ref"] == "D15"  # preserva ref legada


@pytest.mark.asyncio
async def test_goals_payload_without_if_returns_empty_section(db):
    """Se workspace não tem Goal IF, seção não existe no payload."""
    ws = await factories.make_workspace(db)
    payload = await build_goals_payload(ws.id, db=db)
    assert "independencia_financeira" not in payload
    # Adapter sempre emite v2 após refactor do build_goals_payload; payload
    # mínimo só contém _adapter_version = 2.
    assert payload["_adapter_version"] == 2


@pytest.mark.asyncio
async def test_goals_payload_only_db_sourced(db):
    """ADR-180 (A10.6): bundle só contém o que está no DB; sem legacy_extras."""
    ws = await factories.make_workspace(db)
    await factories.make_if_goal(db, workspace=ws)
    await db.commit()

    payload = await build_goals_payload(ws.id, db=db)
    assert "independencia_financeira" in payload  # do DB
    # Workspace sem APORTE/DOLAR Goal → seções ausentes (não vem de legacy).
    assert "aportes" not in payload
    assert "dolarizacao" not in payload


@pytest.mark.asyncio
async def test_goals_payload_isolated_between_workspaces(db):
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    await factories.make_if_goal(db, workspace=ws_a, renda_passiva_mensal_brl=10000)
    await db.commit()

    payload_a = await build_goals_payload(ws_a.id, db=db)
    payload_b = await build_goals_payload(ws_b.id, db=db)
    assert "independencia_financeira" in payload_a
    assert "independencia_financeira" not in payload_b


# ═══════════════════════════════════════════════════════════════════════
# Tasks payload
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_tasks_payload_format_matches_legacy(db):
    """Cada tarefa tem: num, tarefa, categoria, prazo, prioridade, status, ref."""
    ws = await factories.make_workspace(db)
    await factories.make_task(
        db,
        workspace=ws,
        number=5,
        title="Configurar aporte R$20k/mês",
        category="Invest",
        priority="S",
        ref="D02",
        deadline_label="Abr/2026",
    )
    await db.commit()

    payload = await build_tasks_payload(ws.id, db=db)
    assert payload["_adapter_version"] == 1
    assert len(payload["tarefas"]) == 1
    t = payload["tarefas"][0]
    assert t["num"] == 5
    assert t["tarefa"] == "Configurar aporte R$20k/mês"
    assert t["categoria"] == "Invest"
    assert t["prioridade"] == "S"
    assert t["status"] == "pendente"
    assert t["ref"] == "D02"
    assert t["prazo"] == "Abr/2026"


@pytest.mark.asyncio
async def test_tasks_payload_translates_status_to_portuguese(db):
    ws = await factories.make_workspace(db)
    await factories.make_task(db, workspace=ws, status="done")
    await factories.make_task(db, workspace=ws, status="cancelled")
    await db.commit()

    payload = await build_tasks_payload(ws.id, db=db)
    statuses = {t["status"] for t in payload["tarefas"]}
    assert statuses == {"feito", "cancelado"}


@pytest.mark.asyncio
async def test_tasks_payload_suggestions_empty(db):
    """tarefas_sugeridas é sempre [] — sugestões vivem em TaskSuggestion."""
    ws = await factories.make_workspace(db)
    payload = await build_tasks_payload(ws.id, db=db)
    assert payload["tarefas_sugeridas"] == []


# ═══════════════════════════════════════════════════════════════════════
# Tarefas.md export
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_tarefas_md_has_sections(db):
    ws = await factories.make_workspace(db)
    await factories.make_task(db, workspace=ws, priority="S", title="Essencial1")
    await factories.make_task(db, workspace=ws, priority="R", title="Recomendada1")
    await factories.make_task(db, workspace=ws, priority="S", status="done", title="Feita1")
    await db.commit()

    md = await build_tarefas_md(ws.id, db=db)
    assert "Essenciais (S)" in md
    assert "Recomendadas (R)" in md
    assert "Concluídas" in md
    assert "Essencial1" in md
    assert "Feita1" in md


@pytest.mark.asyncio
async def test_tarefas_md_header_marks_adapter(db):
    ws = await factories.make_workspace(db)
    md = await build_tarefas_md(ws.id, db=db)
    assert "Fonte de verdade: tabela `tasks`" in md


# ═══════════════════════════════════════════════════════════════════════
# build_config_store (ADR-134, post-A7.5) — boundary helper sempre DB-first
# ═══════════════════════════════════════════════════════════════════════


def test_build_config_store_returns_db_adapter():
    """Sempre ``DBConfigStore`` ligado à sessão fornecida (post-A7.5)."""
    from backend.app.services.db_config_store import DBConfigStore
    from backend.app.services.pipeline_adapter import build_config_store

    sentinel_session = object()
    store = build_config_store(db=sentinel_session)
    assert isinstance(store, DBConfigStore)
    assert store._session is sentinel_session


def test_build_config_store_satisfies_protocol():
    """Adapter retornado implementa ``ConfigStore`` (runtime check)."""
    from backend.app.services.pipeline_adapter import build_config_store
    from pipeline.ports import ConfigStore

    store = build_config_store(db=object())
    assert isinstance(store, ConfigStore)


# ═══════════════════════════════════════════════════════════════════════
# build_config_overrides_from_db (A7.1 · ADR-134) — DB → ctx.config_overrides
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_build_config_overrides_includes_categorization(db):
    """Workspace com Category rows → categorization.json no overrides."""
    from backend.app.core.database import SyncSessionLocal
    from backend.app.services.pipeline_adapter import build_config_overrides_from_db

    ws = await factories.make_workspace(db)
    await factories.make_category(
        db, workspace=ws, code="alimentacao", category_type="expense", keywords=["mercado"]
    )
    await db.commit()

    with SyncSessionLocal() as sync_db:
        overrides = build_config_overrides_from_db(ws.id, db=sync_db)

    assert "categorization.json" in overrides
    assert overrides["categorization.json"]["expense_keywords"] == {"alimentacao": ["mercado"]}


@pytest.mark.asyncio
async def test_build_config_overrides_skips_empty_workspace(db):
    """Workspace sem nenhum config row → overrides só com ``goals.json`` mínimo (ADR-180)."""
    from backend.app.core.database import SyncSessionLocal
    from backend.app.services.pipeline_adapter import build_config_overrides_from_db

    ws = await factories.make_workspace(db)
    await db.commit()

    with SyncSessionLocal() as sync_db:
        overrides = build_config_overrides_from_db(ws.id, db=sync_db)
    # ADR-180 (A10.6): ``goals.json`` sempre presente como ``GoalsBundle`` mínimo.
    assert set(overrides.keys()) == {"goals.json"}
    assert overrides["goals.json"]["_adapter_version"] == 2


@pytest.mark.asyncio
async def test_build_config_overrides_includes_family_members(db):
    """Workspace com FamilyMember row → family_members.json no overrides."""
    from backend.app.core.database import SyncSessionLocal
    from backend.app.services.pipeline_adapter import build_config_overrides_from_db

    ws = await factories.make_workspace(db)
    await factories.make_member(
        db, workspace=ws, key="david", full_name="David", short_name="David", role="titular"
    )
    await db.commit()

    with SyncSessionLocal() as sync_db:
        overrides = build_config_overrides_from_db(ws.id, db=sync_db)
    assert "family_members.json" in overrides
    assert overrides["family_members.json"]["membros"]["david"]["nome_curto"] == "David"
