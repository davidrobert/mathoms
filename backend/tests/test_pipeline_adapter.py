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
async def test_goals_payload_merges_legacy_extras(db):
    """legacy_extras são preservados sem sobrescrever o que vem do DB."""
    ws = await factories.make_workspace(db)
    await factories.make_if_goal(db, workspace=ws)
    await db.commit()

    legacy = {"aportes": {"meta_aporte_mensal": 20000}, "dolarizacao": {"meta_usd": 20000}}
    payload = await build_goals_payload(ws.id, db=db, legacy_extras=legacy)
    assert "aportes" in payload
    assert "dolarizacao" in payload
    assert "independencia_financeira" in payload  # do DB


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
