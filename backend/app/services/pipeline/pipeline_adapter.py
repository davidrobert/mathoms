"""Pipeline adapter — contrato ADR-075/ADR-180 para transição CLI → Web.

Scripts do pipeline legado (E5, E5.N) consomem o `goals.json` via
``ctx.load_config("goals.json")`` (resolvido contra ``config_overrides``,
populados por ``build_config_overrides_from_db``). ADR-180 (Sprint A10.6):
``build_goals_payload_sync`` retorna ``GoalsBundle`` tipado; o arquivo
``goals.json`` físico nunca mais é escrito em filesystem.

Uso típico (dentro do worker):

    from backend.app.services.pipeline.pipeline_adapter import (
        build_goals_payload_sync,
        build_tasks_payload_sync,
        build_tarefas_md_sync,
    )

    bundle = build_goals_payload_sync(workspace_id, db=db)
    # → GoalsBundle (TypedDict) — dict-shaped, mesmas keys do legado.

    md = build_tarefas_md_sync(workspace_id, db=db)
    # → string com o mesmo layout do config/tarefas.md atual.

Versões assíncronas (`build_*`) também existem — úteis para endpoints
que exportam via HTTP (`/tasks/export.md`, futuro `/goals/export.json`).
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

from backend.app.models.decision import Decision
from backend.app.models.goal import Goal
from backend.app.models.risk import Risk
from backend.app.models.task import Task
from backend.app.models.workspace import Workspace
from backend.app.schemas.business_profile import BusinessProfile
from backend.app.services import task_service
from backend.app.services.tributario_input_builder import build_cascata_input_sync
from backend.app.services.tributario_telemetry import (
    compute_profile_completeness,
    emit_telemetry_for_section,
)
from pipeline.domain.goals_bundle import GoalsBundle, TributarioBundleSection
from pipeline.domain.services.tributario.cascata_calculator import compute as cascata_compute
from pipeline.domain.services.tributario.cascata_serialization import cascata_to_dict

# Status traduzido do vocabulário interno para o usado pelo E5 legado (MD).
_TASK_STATUS_LEGACY_LABEL: dict[str, str] = {
    "pending": "pendente",
    "in_progress": "em andamento",
    "done": "feito",
    "cancelled": "cancelado",
    "blocked": "bloqueado",
}

# Nota acadêmica sobre taxa de retirada — parte do payload `independencia_financeira`.
# Extraída do serializador para manter função curta (ADR-097 + CLAUDE.md §Code style).
_IF_GOAL_TAXA_RETIRADA_NOTA = (
    "TRS operacional = trs_pct (5%). A 'regra dos 4%' clássica "
    "(Trinity Study) é referência acadêmica conservadora. Cálculo "
    "IF: investivel * trs_pct / 12."
)


# ═══════════════════════════════════════════════════════════════════════
# Projeções para o relatório (Sprint A10.5)
# ═══════════════════════════════════════════════════════════════════════
# Card S10 ("Top 5 Decisões de Impacto") e bubble chart S9 ("Riscos
# Prioritários") deixam de ler strings hardcoded da bag PLANNING_CONTEXT
# e passam a consumir projeções do `Decision` (ADR-179) e `Risk`
# (ADR-178) aggregates. Pipeline boundary preservado: SQLAlchemy mora
# aqui (backend.services.*); narradores em `pipeline/**` consomem listas
# já materializadas via `goals_payload`. A10.6 troca dict legacy por
# `GoalsBundle` tipado e remove a bag inteira (ADR-180).


class DecisionTop5Item(TypedDict):
    """Projeção de `Decision` para o card S10. ``impact_1y_brl_cents`` em cents (ADR-090)."""

    title: str
    rationale: Optional[str]
    impact_1y_brl_cents: Optional[int]
    horizon: str
    status: str


class RiskBubbleItem(TypedDict):
    """Projeção de `Risk` para o bubble chart S9 (8 entradas máx)."""

    name: str
    code: str
    probability: Optional[str]
    impact_level: str
    impact_brl_cents: Optional[int]


# ADR-178 §RiskRepository — mesmas tabelas de rank usadas no listing
# canônico (ascendente: 0 = mais grave). Projeção do bubble usa essas
# tabelas para reproduzir a ordenação editorial.
_RISK_IMPACT_RANK = {"crítico": 0, "alto": 1, "médio": 2, "baixo": 3}
_RISK_PROBABILITY_RANK = {"alta": 0, "média": 1, "baixa": 2}

# ADR-179 — top 5 lê apenas Decisions decididas/pendentes que importam
# para o ciclo de execução curto (6-12m). Outras horizons aparecem em
# tela `/plano`, não no relatório S10.
_TOP5_DECISION_HORIZON: str = "short_6_12m"
_TOP5_DECISION_STATUSES: tuple[str, ...] = ("Decidido", "Pendente")
_TOP5_DECISION_LIMIT: int = 5
_RISK_BUBBLE_LIMIT: int = 8


def _decision_to_top5_item(decision: Decision) -> DecisionTop5Item:
    return {
        "title": decision.title,
        "rationale": decision.rationale,
        "impact_1y_brl_cents": decision.impact_1y_brl_cents,
        "horizon": decision.horizon,
        "status": decision.status,
    }


def _risk_to_bubble_item(risk: Risk) -> RiskBubbleItem:
    return {
        "name": risk.name,
        "code": risk.code,
        "probability": risk.probability,
        "impact_level": risk.impact_level,
        "impact_brl_cents": risk.impact_brl_cents,
    }


def _top5_decisions_stmt(workspace_id: str):
    """Statement compartilhado entre as vias sync/async (ADR-179 ordering)."""
    return (
        select(Decision)
        .where(
            Decision.workspace_id == workspace_id,
            Decision.horizon == _TOP5_DECISION_HORIZON,
            Decision.status.in_(_TOP5_DECISION_STATUSES),
        )
        .order_by(
            Decision.priority.is_(None).asc(),
            Decision.priority.asc(),
            Decision.impact_1y_brl_cents.is_(None).asc(),
            Decision.impact_1y_brl_cents.desc(),
            Decision.code.asc(),
        )
        .limit(_TOP5_DECISION_LIMIT)
    )


def _risks_bubble_stmt(workspace_id: str):
    """Statement compartilhado (espelha RiskRepository, ADR-178)."""
    impact_order = case(_RISK_IMPACT_RANK, value=Risk.impact_level, else_=99)
    prob_order = case(_RISK_PROBABILITY_RANK, value=Risk.probability, else_=99)
    return (
        select(Risk)
        .where(Risk.workspace_id == workspace_id)
        .order_by(impact_order.asc(), prob_order.asc(), Risk.code.asc())
        .limit(_RISK_BUBBLE_LIMIT)
    )


def _project_top5_decisions_sync(workspace_id: str, *, db: SyncSession) -> list[DecisionTop5Item]:
    """Sync — card S10."""
    decisions = list(db.execute(_top5_decisions_stmt(workspace_id)).scalars().all())
    return [_decision_to_top5_item(d) for d in decisions]


def _project_risks_bubble_sync(workspace_id: str, *, db: SyncSession) -> list[RiskBubbleItem]:
    """Sync — bubble chart S9."""
    risks = list(db.execute(_risks_bubble_stmt(workspace_id)).scalars().all())
    return [_risk_to_bubble_item(r) for r in risks]


async def _project_top5_decisions_async(
    workspace_id: str, *, db: AsyncSession
) -> list[DecisionTop5Item]:
    """Async — card S10."""
    result = await db.execute(_top5_decisions_stmt(workspace_id))
    return [_decision_to_top5_item(d) for d in result.scalars().all()]


async def _project_risks_bubble_async(
    workspace_id: str, *, db: AsyncSession
) -> list[RiskBubbleItem]:
    """Async — bubble chart S9."""
    result = await db.execute(_risks_bubble_stmt(workspace_id))
    return [_risk_to_bubble_item(r) for r in result.scalars().all()]


# ═══════════════════════════════════════════════════════════════════════
# Goals payload — ``GoalsBundle`` (TypedDict) consumido por E5/E5.N (ADR-180)
# ═══════════════════════════════════════════════════════════════════════


def _serialize_if_goal(goal: Goal) -> dict[str, Any]:
    """Extrai o sub-dict `independencia_financeira` do formato legado (D15)."""
    inputs = goal.params_json.get("inputs", {})
    derived = goal.derived_json or {}
    return {
        "_ref": "D15",
        "if_meta": derived.get("if_meta_brl"),
        "trs_pct": inputs.get("trs_pct"),
        "renda_passiva_meta_mensal": inputs.get("renda_passiva_mensal_brl"),
        "retorno_real_anual_pct": inputs.get("retorno_real_anual_pct"),
        "taxa_retirada_segura_classica_pct": inputs.get("taxa_retirada_conservadora_pct", 4.0),
        "_nota_taxa_retirada": _IF_GOAL_TAXA_RETIRADA_NOTA,
        "_source": "db:goals (ADR-075 adapter)",
    }


def _current_goal_sync(
    workspace_id: str,
    goal_type: str,
    *,
    db: SyncSession,
) -> Optional[Goal]:
    stmt = select(Goal).where(
        Goal.workspace_id == workspace_id,
        Goal.type == goal_type,
        Goal.effective_to.is_(None),
    )
    return db.execute(stmt).scalar_one_or_none()


async def _current_goal_async(
    workspace_id: str,
    goal_type: str,
    *,
    db: AsyncSession,
) -> Optional[Goal]:
    stmt = select(Goal).where(
        Goal.workspace_id == workspace_id,
        Goal.type == goal_type,
        Goal.effective_to.is_(None),
    )
    return (await db.execute(stmt)).scalar_one_or_none()


def _serialize_aporte_goal(goal: Goal) -> dict[str, Any]:
    inputs = goal.params_json.get("inputs", {})
    return {
        "_ref": "D02",
        "meta_aporte_mensal": inputs.get("meta_aporte_mensal_brl"),
        "dia_aporte": inputs.get("dia_aporte"),
        "periodo_inicio": inputs.get("periodo_inicio", "Imediato"),
        "distribuicao": inputs.get("distribuicao", {}),
        "_source": "db:goals",
    }


def _serialize_dolarizacao_goal(goal: Goal) -> dict[str, Any]:
    inputs = goal.params_json.get("inputs", {})
    return {
        "_ref": "D09",
        "meta_usd": inputs.get("meta_usd"),
        "aporte_mensal_brl": inputs.get("aporte_mensal_brl"),
        "_source": "db:goals",
    }


def _serialize_alocacao_goal(goal: Goal) -> dict[str, Any]:
    inputs = goal.params_json.get("inputs", {})
    return {
        "renda_fixa_pct": inputs.get("renda_fixa_pct"),
        "acoes_pct": inputs.get("acoes_pct"),
        "imoveis_reits_pct": inputs.get("imoveis_reits_pct"),
        "liquidez_usd_pct": inputs.get("liquidez_usd_pct"),
        "instrumentos_rf": inputs.get("instrumentos_rf", ""),
        "instrumentos_rv": inputs.get("instrumentos_rv", ""),
        "rebalanceamento": inputs.get("rebalanceamento", "anual"),
        "_source": "db:goals",
    }


# ═══════════════════════════════════════════════════════════════════════
# Tributário — bundle["tributario"] (ADR-236 §D4)
# ═══════════════════════════════════════════════════════════════════════

_REGIME_LABELS: dict[str, str] = {
    "mei": "MEI",
    "simples": "Simples Nacional",
    "lucro_presumido": "Lucro Presumido",
    "lucro_real": "Lucro Real",
}


def _regime_to_label(regime: Optional[str] = None, anexo: Optional[str] = None) -> str:
    # ``regime``/``anexo`` Optional: workspace incompleto degrada para
    # "Perfil tributário incompleto" sem branch separada upstream.
    if regime is None:
        return "Perfil tributário incompleto"
    base = _REGIME_LABELS.get(regime, regime)
    if regime == "simples" and anexo:
        return f"{base} — Anexo {anexo}"
    return base


_EMPTY_BP_SUMMARY: dict[str, Any] = {
    "contador": None,
    "holding_prazo_meses": None,
    "anexo": None,
}


def _business_profile_summary(
    ws: Optional[Workspace] = None,
) -> tuple[Optional[BusinessProfile], dict[str, Any]]:
    # ``ws`` Optional: ``db.get`` retorna None p/ workspace inexistente — degrada
    # para summary vazio (workspace deletado durante request, edge case).
    if ws is None or not ws.business_profile_json:
        return None, _EMPTY_BP_SUMMARY
    try:
        bp = BusinessProfile(**ws.business_profile_json)
    except (ValueError, TypeError):
        return None, _EMPTY_BP_SUMMARY
    return bp, {
        "contador": bp.contador,
        "holding_prazo_meses": bp.holding_prazo_meses,
        "anexo": bp.anexo_simples,
    }


def _assemble_tributario_section(
    bp_summary: dict[str, Any],
    cascata_output_dict: dict[str, Any],
    regime: Optional[str] = None,
) -> TributarioBundleSection:
    # ``regime`` Optional: bundle["tributario"] sempre presente; None vira
    # estado "perfil pendente" no narrator (ADR-236 §D5).
    return {
        "regime": regime,
        "regime_label": _regime_to_label(regime, bp_summary["anexo"]),
        "cascata": cascata_output_dict,
        "contador_nome": bp_summary["contador"],
        "holding_prazo_meses": bp_summary["holding_prazo_meses"],
        "_source": "db:business_profile_json + e3/e4/e1.6 derived",
    }


def _trigger_codes_from_cascata(cascata_output_dict: dict[str, Any]) -> list[str]:
    return [
        t.get("code", "")
        for t in (cascata_output_dict.get("triggers") or [])
        if isinstance(t, dict)
    ]


def _emit_tributario_telemetry(
    bp: Optional[BusinessProfile] = None, cascata_output_dict: Optional[dict[str, Any]] = None
) -> None:
    """ADR-236 §D6 + P6 — 3 eventos LGPD-safe (regime + códigos T1-T5)."""
    regime = bp.regime if bp else None
    is_complete, missing_fields = compute_profile_completeness(
        regime=regime,
        anexo_simples=bp.anexo_simples if bp else None,
        tipo_declaracao_ir=bp.tipo_declaracao_ir if bp else None,
    )
    emit_telemetry_for_section(
        regime=regime,
        has_complete_profile=is_complete,
        missing_fields=missing_fields,
        trigger_codes=_trigger_codes_from_cascata(cascata_output_dict or {}),
    )


def _build_tributario_section_sync(
    workspace_id: str, *, db: SyncSession
) -> TributarioBundleSection:
    """ADR-236 §D4: lê BP + agrega derived inputs + compute → seção do bundle."""
    ws = db.get(Workspace, workspace_id)
    bp, bp_summary = _business_profile_summary(ws)
    cascata_input = build_cascata_input_sync(workspace_id, db=db)
    cascata_output = cascata_compute(cascata_input)
    cascata_dict = cascata_to_dict(cascata_output)
    _emit_tributario_telemetry(bp, cascata_dict)
    return _assemble_tributario_section(
        bp_summary,
        cascata_dict,
        regime=bp.regime if bp else None,
    )


async def _build_tributario_section_async(
    workspace_id: str, *, db: AsyncSession
) -> TributarioBundleSection:
    """ADR-236 §D4 — versão async; delega `build_cascata_input_sync` via run_sync."""
    ws = await db.get(Workspace, workspace_id)
    bp, bp_summary = _business_profile_summary(ws)
    cascata_input = await db.run_sync(
        lambda sync_db: build_cascata_input_sync(workspace_id, db=sync_db)
    )
    cascata_output = cascata_compute(cascata_input)
    cascata_dict = cascata_to_dict(cascata_output)
    _emit_tributario_telemetry(bp, cascata_dict)
    return _assemble_tributario_section(
        bp_summary,
        cascata_dict,
        regime=bp.regime if bp else None,
    )


# Mapa tipo → (chave no GoalsBundle, serializador).
_GOAL_TYPE_MAP: dict[str, tuple[str, Any]] = {
    "INDEPENDENCIA_FINANCEIRA": ("independencia_financeira", _serialize_if_goal),
    "APORTE_MENSAL": ("aportes", _serialize_aporte_goal),
    "DOLARIZACAO": ("dolarizacao", _serialize_dolarizacao_goal),
    "ALOCACAO_ALVO": ("alocacao_alvo", _serialize_alocacao_goal),
}


def _merge_goals_into_payload(
    payload: dict[str, Any],
    workspace_id: str,
    goal_getter,
) -> None:
    """Para cada Goal type conhecido no DB, serializa e injeta no payload (ADR-180)."""
    for goal_type, (key, serializer) in _GOAL_TYPE_MAP.items():
        goal = goal_getter(workspace_id, goal_type)
        if goal is not None:
            payload[key] = serializer(goal)


def build_goals_payload_sync(
    workspace_id: str,
    *,
    db: SyncSession,
) -> GoalsBundle:
    """Reconstrói o ``GoalsBundle`` do workspace a partir do DB (sync — worker, ADR-180)."""
    payload: dict[str, Any] = {}
    _merge_goals_into_payload(payload, workspace_id, lambda ws, g: _current_goal_sync(ws, g, db=db))
    payload["tributario"] = _build_tributario_section_sync(workspace_id, db=db)
    _apply_projections_sync(payload, workspace_id, db=db)
    payload["_adapter_version"] = 2
    return payload  # type: ignore[return-value]


def _apply_projections_sync(payload: dict[str, Any], workspace_id: str, *, db: SyncSession) -> None:
    # ADR-178/179 — projeções S10/S9 sempre presentes (lista vazia se DB vazio).
    payload["top5_decisoes_projection"] = _project_top5_decisions_sync(workspace_id, db=db)
    payload["risks_projection"] = _project_risks_bubble_sync(workspace_id, db=db)


async def _goals_by_type_async(workspace_id: str, *, db: AsyncSession) -> dict[str, Goal]:
    """Busca todos goals ativos do workspace em uma query e indexa por type."""
    stmt = select(Goal).where(
        Goal.workspace_id == workspace_id,
        Goal.effective_to.is_(None),
    )
    all_goals = list((await db.execute(stmt)).scalars().all())
    return {g.type: g for g in all_goals}


def _apply_goals_to_payload(payload: dict[str, Any], goals_by_type: dict[str, Goal]) -> None:
    """Serializa goals conhecidos no payload (ADR-180)."""
    for goal_type, (key, serializer) in _GOAL_TYPE_MAP.items():
        goal = goals_by_type.get(goal_type)
        if goal is not None:
            payload[key] = serializer(goal)


async def build_goals_payload(
    workspace_id: str,
    *,
    db: AsyncSession,
) -> GoalsBundle:
    """Versão async. Mesmo contrato que a versão sync (ADR-180)."""
    payload: dict[str, Any] = {}
    goals_by_type = await _goals_by_type_async(workspace_id, db=db)
    _apply_goals_to_payload(payload, goals_by_type)
    payload["tributario"] = await _build_tributario_section_async(workspace_id, db=db)
    # ADR-178/179 (Sprint A10.5) — projeções via mesmas queries da via sync.
    payload["top5_decisoes_projection"] = await _project_top5_decisions_async(workspace_id, db=db)
    payload["risks_projection"] = await _project_risks_bubble_async(workspace_id, db=db)
    payload["_adapter_version"] = 2
    return payload  # type: ignore[return-value]


# ═══════════════════════════════════════════════════════════════════════
# Tasks payload (compatível com E5 `tarefas[]`)
# ═══════════════════════════════════════════════════════════════════════


def _serialize_task_for_pipeline(task: Task) -> dict[str, Any]:
    """Formato esperado pelo E5 legado. Status traduzido para vocabulário MD."""
    prazo = task.deadline_label or (task.deadline_date.isoformat() if task.deadline_date else "—")
    return {
        "num": task.number,
        "tarefa": task.title,
        "categoria": task.category,
        "prazo": prazo,
        "prioridade": task.priority,
        "status": _TASK_STATUS_LEGACY_LABEL.get(task.status, task.status),
        "ref": task.ref or "—",
    }


def _all_tasks_ordered_sync(
    workspace_id: str,
    *,
    db: SyncSession,
) -> list[Task]:
    stmt = select(Task).where(Task.workspace_id == workspace_id).order_by(Task.number.asc())
    return list(db.execute(stmt).scalars().all())


async def _all_tasks_ordered_async(
    workspace_id: str,
    *,
    db: AsyncSession,
) -> list[Task]:
    stmt = select(Task).where(Task.workspace_id == workspace_id).order_by(Task.number.asc())
    return list((await db.execute(stmt)).scalars().all())


def build_tasks_payload_sync(
    workspace_id: str,
    *,
    db: SyncSession,
) -> dict[str, Any]:
    """Reconstrói o bloco `tarefas` esperado pelo E5 legado:

    {
      "tarefas": [{num, tarefa, categoria, prazo, prioridade, status, ref}, ...],
      "tarefas_sugeridas": [] — vazio, sugestões vivem em TaskSuggestion agora
    }
    """
    tasks = _all_tasks_ordered_sync(workspace_id, db=db)
    return {
        "tarefas": [_serialize_task_for_pipeline(t) for t in tasks],
        "tarefas_sugeridas": [],  # F8.2+: sugestões vivem em TaskSuggestion
        "_adapter_version": 1,
    }


async def build_tasks_payload(
    workspace_id: str,
    *,
    db: AsyncSession,
) -> dict[str, Any]:
    tasks = await _all_tasks_ordered_async(workspace_id, db=db)
    return {
        "tarefas": [_serialize_task_for_pipeline(t) for t in tasks],
        "tarefas_sugeridas": [],
        "_adapter_version": 1,
    }


# ═══════════════════════════════════════════════════════════════════════
# Tarefas.md export (compatível com `config/tarefas.md`)
# ═══════════════════════════════════════════════════════════════════════


async def build_tarefas_md(
    workspace_id: str,
    *,
    db: AsyncSession,
) -> str:
    """Wrapper async que delega ao `task_service.export_markdown` já
    existente. Incluído aqui para manter o contrato do adapter coeso
    (caller importa tudo de `pipeline_adapter`)."""
    return await task_service.export_markdown(workspace_id, db=db)


_PRIORITY_SECTION_TITLE: dict[str, str] = {
    "S": "Essenciais (S)",
    "R": "Recomendadas (R)",
    "O": "Opcionais (O)",
}


def _md_header_lines() -> list[str]:
    return [
        "# Tarefas — Pipeline (export do DB)",
        "",
        "> Gerado por `pipeline_adapter.build_tarefas_md_sync`. "
        "Fonte de verdade: tabela `tasks` (ADR-074/075).",
        "",
        "---",
        "",
    ]


def _md_priority_section_lines(priority: str, tasks: list[Task]) -> list[str]:
    """Bloco MD de uma seção de prioridade (S/R/O). Vazio se não há tasks."""
    if not tasks:
        return []
    lines = [
        f"## {_PRIORITY_SECTION_TITLE[priority]}",
        "",
        "| # | Tarefa | Categoria | Prazo | Status | Ref |",
        "|---|---|---|---|---|---|",
    ]
    for t in tasks:
        prazo = t.deadline_label or (t.deadline_date.isoformat() if t.deadline_date else "—")
        status = _TASK_STATUS_LEGACY_LABEL.get(t.status, t.status)
        title = t.title.replace("|", "\\|")
        lines.append(
            f"| {t.number} | {title} | {t.category} | {prazo} | {status} | {t.ref or '—'} |"
        )
    lines.extend(["", "---", ""])
    return lines


def _md_done_section_lines(done_tasks: list[Task]) -> list[str]:
    """Bloco MD do histórico de concluídas. Vazio se não há."""
    if not done_tasks:
        return []
    lines = [
        "## Concluídas (histórico)",
        "",
        "| # | Tarefa | Data conclusão | Detalhe |",
        "|---|---|---|---|",
    ]
    for t in done_tasks:
        completed = t.completed_at.date().isoformat() if t.completed_at else "—"
        title = t.title.replace("|", "\\|")
        lines.append(f"| {t.number} | {title} | {completed} | {t.status_reason or '—'} |")
    lines.append("")
    return lines


def build_tarefas_md_sync(
    workspace_id: str,
    *,
    db: SyncSession,
) -> str:
    """Versão sync — gera MD diretamente no worker sem async session.
    Replica a lógica de `task_service.export_markdown` com sync queries.
    """
    tasks = _all_tasks_ordered_sync(workspace_id, db=db)
    active = [t for t in tasks if t.status not in ("done", "cancelled")]
    done = [t for t in tasks if t.status == "done"]

    lines: list[str] = _md_header_lines()
    for prio in ("S", "R", "O"):
        section_tasks = [t for t in active if t.priority == prio]
        lines.extend(_md_priority_section_lines(prio, section_tasks))
    lines.extend(_md_done_section_lines(done))

    return "\n".join(lines) + "\n"


def build_config_store(*, db: SyncSession):
    """Boundary helper (ADR-134, post-A7.5): always returns ``DBConfigStore``."""
    from backend.app.services.db_config_store import DBConfigStore

    return DBConfigStore(db)


# A7.1 — keys que cobrimos pela via DB-first; out-of-scope (goals/scoring/
# fiscal/taxas/pipeline/llm) seguem materialização normal por enquanto.
_A7_1_OVERRIDE_KEYS: tuple[str, ...] = (
    "categorization.json",
    "family_members.json",
    "institutions.json",
    "report_layout.yaml",
)


def _family_members_override(workspace_id: str, db: SyncSession) -> dict[str, Any] | None:
    """Funde ``family_members`` + ``transferencias_internas`` (ADR-133) em um blob."""
    from backend.app.services.config_materializer import (
        serialize_family_members,
        serialize_transfer_config,
    )

    family = serialize_family_members(workspace_id, db)
    transfer = serialize_transfer_config(workspace_id, db)
    if not family and transfer is None:
        return None
    merged = dict(family or {})
    if transfer is not None:
        merged["transferencias_internas"] = transfer
    return merged or None


def build_config_overrides_from_db(workspace_id: str, *, db: SyncSession) -> dict[str, Any]:
    """Pré-serializa configs do DB para ``WorkspaceContext.config_overrides`` (ADR-134/137/180/211)."""
    from backend.app.services.config_materializer import (
        serialize_llm_config,
        serialize_report_layout,
    )

    sources: dict[str, Any] = {
        "family_members.json": _family_members_override(workspace_id, db),
        "categorization.json": _categorization_override(workspace_id, db),
        "institutions.json": _institutions_override(db),
        "report_layout.yaml": serialize_report_layout(workspace_id, db),
        "goals.json": dict(build_goals_payload_sync(workspace_id, db=db)),
        "llm_config.json": serialize_llm_config(workspace_id, db),
    }
    return {k: v for k, v in sources.items() if v is not None}


def _categorization_override(workspace_id: str, db: SyncSession) -> dict[str, Any] | None:
    """Resolved categories + auxiliary metadata, no formato consumido por categorize_transactions."""
    from backend.app.services.category_resolver import (
        get_categorization_metadata,
        resolve_categories,
    )
    from backend.app.services.config_materializer import serialize_categorization

    try:
        resolved = resolve_categories(workspace_id, db)
        metadata = get_categorization_metadata(db)
    except Exception:
        return serialize_categorization(workspace_id, db)
    if not resolved:
        return serialize_categorization(workspace_id, db)
    expense_keywords: dict[str, list[str]] = {}
    income_keywords: dict[str, list[str]] = {}
    for cat in resolved:
        bucket = expense_keywords if cat.category_type == "expense" else income_keywords
        bucket[cat.key] = list(cat.keywords)
    payload: dict[str, Any] = {
        "expense_keywords": expense_keywords,
        "income_keywords": income_keywords,
    }
    payload.update(metadata)
    return payload


def _institutions_override(db: SyncSession) -> dict[str, Any] | None:
    """Catálogo global → formato ``institutions.json`` (banco_canonical)."""
    from backend.app.services.institution_resolver import resolve_institutions

    catalog = resolve_institutions(db)
    if not catalog.institutions:
        return None
    return {"banco_canonical": {code: inst.name for code, inst in catalog.institutions.items()}}


# ADR-192 — build_protection_bundle* vive em protection_bundle_adapter (SRP).
from backend.app.services.protection_bundle_adapter import (  # noqa: E402
    build_protection_bundle,
    build_protection_bundle_sync,
)

__all__ = [
    # Sync (worker)
    "build_goals_payload_sync",
    "build_tasks_payload_sync",
    "build_tarefas_md_sync",
    "build_config_store",
    "build_config_overrides_from_db",
    "build_protection_bundle_sync",
    # Async (endpoints)
    "build_goals_payload",
    "build_tasks_payload",
    "build_tarefas_md",
    "build_protection_bundle",
]
