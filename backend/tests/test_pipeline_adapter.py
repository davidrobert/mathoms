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

from backend.app.services.pipeline.pipeline_adapter import (
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
    from backend.app.services.pipeline.pipeline_adapter import build_config_store

    sentinel_session = object()
    store = build_config_store(db=sentinel_session)
    assert isinstance(store, DBConfigStore)
    assert store._session is sentinel_session


def test_build_config_store_satisfies_protocol():
    """Adapter retornado implementa ``ConfigStore`` (runtime check)."""
    from backend.app.services.pipeline.pipeline_adapter import build_config_store
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
    from backend.app.services.pipeline.pipeline_adapter import build_config_overrides_from_db

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
    from backend.app.services.pipeline.pipeline_adapter import build_config_overrides_from_db

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
    from backend.app.services.pipeline.pipeline_adapter import build_config_overrides_from_db

    ws = await factories.make_workspace(db)
    await factories.make_member(
        db, workspace=ws, key="david", full_name="David", short_name="David", role="titular"
    )
    await db.commit()

    with SyncSessionLocal() as sync_db:
        overrides = build_config_overrides_from_db(ws.id, db=sync_db)
    assert "family_members.json" in overrides
    assert overrides["family_members.json"]["membros"]["david"]["nome_curto"] == "David"


# ═══════════════════════════════════════════════════════════════════════
# Tributário section — ADR-236 §D4
# ═══════════════════════════════════════════════════════════════════════


_EXPECTED_TRIBUTARIO_KEYS: set[str] = {
    "regime",
    "regime_label",
    "cascata",
    "contador_nome",
    "holding_prazo_meses",
    "_source",
}

_EXPECTED_CASCATA_KEYS: set[str] = {
    "regime",
    "regime_label",
    "regime_nao_suportado",
    "motivo_nao_suportado",
    "receita_bruta",
    "tributos_federais",
    "iss_total",
    "lucro_contabil_pj",
    "pro_labore_bruto",
    "inss_patronal",
    "inss_empregado",
    "irrf_pro_labore",
    "lucros_distribuidos",
    "renda_pf_tributavel_total",
    "carga_total_pct",
    "pgbl_base_anual",
    "pgbl_limite_anual",
    "pgbl_aplicavel",
    "pgbl_motivo_inaplicavel",
    "fator_r_pct",
    "fator_r_faixa",
    "fator_r_break_even_mensal",
    "triggers",
    # CTO-05 (emenda ADR-236) — entradas PJ detectadas + sinais de domínio.
    "receita_pj_detectada_anual",
    "signals",
    # ADR-238 plumbing E5 — snapshot informes previdência (None se ausente).
    "previdencia_snapshot",
    # ADR-238 A17 L2 P3 — snapshot informes financeiro_pj (None se ausente).
    "financeiro_pj_snapshot",
}


@pytest.mark.asyncio
async def test_tributario_section_shape_workspace_sem_perfil(db):
    """Workspace sem ``business_profile_json`` retorna seção com regime=None."""
    ws = await factories.make_workspace(db)
    await db.commit()

    payload = await build_goals_payload(ws.id, db=db)
    section = payload["tributario"]
    assert set(section.keys()) == _EXPECTED_TRIBUTARIO_KEYS
    assert section["regime"] is None
    assert section["regime_label"] == "Perfil tributário incompleto"
    assert section["_source"] == "db:business_profile_json + e3/e4/e1.6 derived"

    cascata = section["cascata"]
    assert set(cascata.keys()) == _EXPECTED_CASCATA_KEYS
    assert cascata["regime_nao_suportado"] is True
    assert cascata["motivo_nao_suportado"] == "perfil_incompleto"


async def _persist_encrypted_e4(db, ws_id: str, run_id: str, key: str, content: dict) -> None:
    """Persiste artifact E4 com content_json ENCRIPTADO (ADR-231) — espelha produção."""
    from backend.app.models.pipeline_artifact import PipelineArtifact
    from backend.app.services.security.crypto import encrypt_artifact_payload

    db.add(
        PipelineArtifact(
            workspace_id=ws_id,
            pipeline_run_id=run_id,
            stage="categorize_transactions",
            artifact_key=key,
            content_json=encrypt_artifact_payload(content),
        )
    )


async def _seed_encrypted_pj_run(db, ws_id: str) -> None:
    """Run E4 com receita PJ (lucros) + 12 meses, tudo encriptado (ADR-231)."""
    from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus

    run = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed, tier_at_run="premium")
    db.add(run)
    await db.flush()
    receitas = {"totais_por_categoria": {"lucros_distribuidos": 120000.0}}
    fluxo = {"meses_ordenados": [f"2024-{m:02d}" for m in range(1, 13)]}
    await _persist_encrypted_e4(db, ws_id, run.id, "receitas", receitas)
    await _persist_encrypted_e4(db, ws_id, run.id, "fluxo_mensal_detalhado", fluxo)


@pytest.mark.asyncio
async def test_cascata_decripta_receitas_e4_e_sinaliza_pj(db):
    """RV2-18: builder decripta content_json E4 (ADR-231). Perfil incompleto com receita
    PJ encriptada sinaliza a inconsistência em vez de zerar silenciosamente a cascata."""
    ws = await factories.make_workspace(db)  # sem business_profile → perfil_incompleto
    await _seed_encrypted_pj_run(db, ws.id)
    await db.commit()

    cascata = (await build_goals_payload(ws.id, db=db))["tributario"]["cascata"]
    assert cascata["motivo_nao_suportado"] == "perfil_incompleto"
    assert cascata["receita_pj_detectada_anual"] > 0  # cru (encriptado) daria 0
    assert "perfil_incompleto_com_receita" in cascata["signals"]


_SIMPLES_BP_FIXTURE: dict = {
    "contador": "Acme Contadores",
    "regime": "simples",
    "anexo_simples": "III",
    "iss_aliquota_pct": 2.5,
    "tipo_declaracao_ir": "completa",
    "holding_prazo_meses": 18,
}


async def _set_business_profile(db, ws, bp_json: dict) -> None:
    from backend.app.models.workspace import Workspace as WsModel

    ws_db = await db.get(WsModel, ws.id)
    ws_db.business_profile_json = bp_json
    await db.commit()


@pytest.mark.asyncio
async def test_tributario_section_shape_workspace_simples_anexo_iii(db):
    """Workspace com BP Simples Anexo III completo gera cascata calculada."""
    ws = await factories.make_workspace(db)
    await _set_business_profile(db, ws, _SIMPLES_BP_FIXTURE)
    section = (await build_goals_payload(ws.id, db=db))["tributario"]
    cascata = section["cascata"]
    assert section["regime"] == "simples"
    assert section["regime_label"] == "Simples Nacional — Anexo III"
    assert section["contador_nome"] == "Acme Contadores"
    assert section["holding_prazo_meses"] == 18
    assert cascata["regime_nao_suportado"] is False
    assert cascata["motivo_nao_suportado"] is None
    # JSON-friendly serialization (Money/Decimal → float).
    assert isinstance(cascata["carga_total_pct"], float)
    assert isinstance(cascata["receita_bruta"], float)
    assert isinstance(cascata["pgbl_limite_anual"], float)


@pytest.mark.asyncio
async def test_tributario_section_shape_lucro_real_unsupported(db):
    """Lucro Real cai em ``regime_nao_suportado`` (V2 escopo)."""
    ws = await factories.make_workspace(db)
    await _set_business_profile(db, ws, {"regime": "lucro_real"})

    payload = await build_goals_payload(ws.id, db=db)
    section = payload["tributario"]
    cascata = section["cascata"]
    assert section["regime"] == "lucro_real"
    assert cascata["regime_nao_suportado"] is True
    assert cascata["motivo_nao_suportado"] == "lucro_real"


@pytest.mark.asyncio
async def test_tributario_section_shape_simples_sem_anexo_pendente(db):
    """Simples sem ``anexo_simples`` cai em estado pendente — não inventa Anexo V."""
    ws = await factories.make_workspace(db)
    await _set_business_profile(db, ws, {"regime": "simples"})

    payload = await build_goals_payload(ws.id, db=db)
    section = payload["tributario"]
    assert section["regime"] == "simples"
    assert section["cascata"]["motivo_nao_suportado"] == "anexo_simples_pendente"


@pytest.mark.asyncio
async def test_tributario_section_always_present(db):
    """Bundle sempre tem ``tributario`` — narrator nunca quebra por KeyError."""
    ws = await factories.make_workspace(db)
    await db.commit()
    payload = await build_goals_payload(ws.id, db=db)
    assert "tributario" in payload
