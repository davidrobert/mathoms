"""Pipeline adapter — contrato ADR-075 para transição CLI → Web.

Scripts do pipeline legado (E5, E5.N, E6) leem `config/goals.json` e
`config/tarefas.md` para renderizar o relatório. Durante a transição
para DB-as-source-of-truth, este módulo expõe funções que reconstroem
esses payloads a partir do DB no formato **idêntico** ao legado —
permitindo que os scripts continuem funcionando sem conhecer o DB.

Uso típico (dentro do worker):

    from backend.app.services.pipeline_adapter import (
        build_goals_payload_sync,
        build_tasks_payload_sync,
        build_tarefas_md_sync,
    )

    goals = build_goals_payload_sync(workspace_id, db=db)
    # → dict compatível com json.load(open("config/goals.json"))

    md = build_tarefas_md_sync(workspace_id, db=db)
    # → string com o mesmo layout do config/tarefas.md atual

Contrato documentado em:
  - ADR-075 (DECISIONS.md)
  - docs/cutover_pipeline.md (F4.1 — a criar)

A ÚNICA coisa fora do DB que ainda é lida de filesystem são **seeds
de produto** (Grupo B do ADR-075): institutions.json, categorization
keywords, parametros_fiscais.json. Esses permanecem.

Versões assíncronas (`build_*`) também existem — úteis para endpoints
que exportam via HTTP (`/tasks/export.md`, futuro `/goals/export.json`).
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

from backend.app.models.goal import Goal
from backend.app.models.task import Task
from backend.app.services import task_service

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
# Goals payload (compatível com `config/goals.json`)
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


# Mapa tipo → (chave no goals.json, serializador).
# PLANNING_CONTEXT não aparece aqui — é tratado separadamente.
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
    """Genérico: para cada Goal type no DB, serializa e injeta no payload."""
    for goal_type, (key, serializer) in _GOAL_TYPE_MAP.items():
        goal = goal_getter(workspace_id, goal_type)
        if goal is not None:
            payload[key] = serializer(goal)

    # PLANNING_CONTEXT: blob genérico cujas chaves são mergidas diretamente
    ctx_goal = goal_getter(workspace_id, "PLANNING_CONTEXT")
    if ctx_goal and ctx_goal.params_json:
        ctx_data = ctx_goal.params_json.get("inputs", ctx_goal.params_json)
        for k, v in ctx_data.items():
            if k not in payload and not k.startswith("_"):
                payload[k] = v


def build_goals_payload_sync(
    workspace_id: str,
    *,
    db: SyncSession,
    legacy_extras: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Reconstrói o dict do `goals.json` a partir do DB (sync — worker).

    Prioridade: DB > legacy_extras. Seções no DB sobrescrevem as do legado.
    Se o workspace tem PLANNING_CONTEXT, suas chaves são mergidas no
    top-level (cobrindo fase_f1f2, seguros, tributario, etc.)

    Se `legacy_extras` é None e o DB está vazio, retorna dict mínimo.
    """
    payload: dict[str, Any] = dict(legacy_extras or {})

    def _getter(ws, gtype):
        return _current_goal_sync(ws, gtype, db=db)

    _merge_goals_into_payload(payload, workspace_id, _getter)
    payload["_adapter_version"] = 2
    return payload


async def _goals_by_type_async(workspace_id: str, *, db: AsyncSession) -> dict[str, Goal]:
    """Busca todos goals ativos do workspace em uma query e indexa por type."""
    stmt = select(Goal).where(
        Goal.workspace_id == workspace_id,
        Goal.effective_to.is_(None),
    )
    all_goals = list((await db.execute(stmt)).scalars().all())
    return {g.type: g for g in all_goals}


def _apply_goals_to_payload(payload: dict[str, Any], goals_by_type: dict[str, Goal]) -> None:
    """Serializa goals conhecidos + merge PLANNING_CONTEXT no payload."""
    for goal_type, (key, serializer) in _GOAL_TYPE_MAP.items():
        goal = goals_by_type.get(goal_type)
        if goal is not None:
            payload[key] = serializer(goal)
    ctx_goal = goals_by_type.get("PLANNING_CONTEXT")
    if ctx_goal and ctx_goal.params_json:
        ctx_data = ctx_goal.params_json.get("inputs", ctx_goal.params_json)
        for k, v in ctx_data.items():
            if k not in payload and not k.startswith("_"):
                payload[k] = v


async def build_goals_payload(
    workspace_id: str,
    *,
    db: AsyncSession,
    legacy_extras: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Versão async. Mesmo contrato que a versão sync."""
    payload: dict[str, Any] = dict(legacy_extras or {})
    goals_by_type = await _goals_by_type_async(workspace_id, db=db)
    _apply_goals_to_payload(payload, goals_by_type)
    payload["_adapter_version"] = 2
    return payload


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
            f"| {t.number} | {title} | {t.category} | {prazo} | " f"{status} | {t.ref or '—'} |"
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


def build_config_store(*, db: SyncSession, use_db_artifacts: bool):
    """Boundary helper (A7.1 · ADR-134): ``DBConfigStore`` quando flag on, ``FileConfigStore`` legacy senão."""
    if use_db_artifacts:
        from backend.app.services.db_config_store import DBConfigStore

        return DBConfigStore(db)
    from pipeline.adapters.file_config_store import FileConfigStore

    return FileConfigStore()


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
    """Pré-serializa configs A7.1+A7.3 do DB para ``WorkspaceContext.config_overrides``.

    A7.3 (ADR-137): ``categorization.json`` agora vem do resolver
    (template global + overrides do workspace) + auxiliary metadata
    (pj_source_mapping, internal_transfer_patterns…) do row reservado.
    ``institutions.json`` vem do ``institution_catalog`` global.
    """
    from backend.app.services.config_materializer import serialize_report_layout

    sources: dict[str, Any] = {
        "family_members.json": _family_members_override(workspace_id, db),
        "categorization.json": _categorization_override(workspace_id, db),
        "institutions.json": _institutions_override(db),
        "report_layout.yaml": serialize_report_layout(workspace_id, db),
    }
    return {k: v for k, v in sources.items() if v is not None}


def _categorization_override(
    workspace_id: str, db: SyncSession
) -> dict[str, Any] | None:
    """Resolved categories + auxiliary metadata, no formato consumido por e4_categorize."""
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
        bucket = (
            expense_keywords if cat.category_type == "expense" else income_keywords
        )
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
    return {
        "banco_canonical": {
            code: inst.name for code, inst in catalog.institutions.items()
        }
    }


__all__ = [
    # Sync (worker)
    "build_goals_payload_sync",
    "build_tasks_payload_sync",
    "build_tarefas_md_sync",
    "build_config_store",
    "build_config_overrides_from_db",
    # Async (endpoints)
    "build_goals_payload",
    "build_tasks_payload",
    "build_tarefas_md",
]
