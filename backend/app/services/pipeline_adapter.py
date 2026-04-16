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


# ═══════════════════════════════════════════════════════════════════════
# Goals payload (compatível com `config/goals.json`)
# ═══════════════════════════════════════════════════════════════════════


def _serialize_if_goal(goal: Goal) -> dict[str, Any]:
    """Extrai o sub-dict `independencia_financeira` do formato legado.

    Campo legado (goals.json):
      "independencia_financeira": {
        "_ref": "D15",
        "if_meta": 7200000.0,
        "trs_pct": 5.0,
        "renda_passiva_meta_mensal": 30000,
        "retorno_real_anual_pct": 6.0,
        "taxa_retirada_segura_classica_pct": 4.0,
        "_nota_taxa_retirada": "..."
      }
    """
    inputs = goal.params_json.get("inputs", {})
    derived = goal.derived_json or {}
    return {
        "_ref": "D15",
        "if_meta": derived.get("if_meta_brl"),
        "trs_pct": inputs.get("trs_pct"),
        "renda_passiva_meta_mensal": inputs.get("renda_passiva_mensal_brl"),
        "retorno_real_anual_pct": inputs.get("retorno_real_anual_pct"),
        "taxa_retirada_segura_classica_pct": inputs.get(
            "taxa_retirada_conservadora_pct", 4.0
        ),
        "_nota_taxa_retirada": (
            "TRS operacional = trs_pct (5%). A 'regra dos 4%' clássica "
            "(Trinity Study) é referência acadêmica conservadora. Cálculo "
            "IF: investivel * trs_pct / 12."
        ),
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


async def build_goals_payload(
    workspace_id: str,
    *,
    db: AsyncSession,
    legacy_extras: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Versão async. Mesmo contrato que a versão sync."""
    payload: dict[str, Any] = dict(legacy_extras or {})

    async def _getter(ws, gtype):
        return await _current_goal_async(ws, gtype, db=db)

    # Precisa de adaptação: _merge_goals_into_payload é sync.
    # Para evitar refatorar para await, buscamos todos os goals de uma vez.
    from sqlalchemy import select as _sel

    all_goals_stmt = _sel(Goal).where(
        Goal.workspace_id == workspace_id,
        Goal.effective_to.is_(None),
    )
    all_goals = list((await db.execute(all_goals_stmt)).scalars().all())
    goals_by_type = {g.type: g for g in all_goals}

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

    payload["_adapter_version"] = 2
    return payload


# ═══════════════════════════════════════════════════════════════════════
# Tasks payload (compatível com E5 `tarefas[]`)
# ═══════════════════════════════════════════════════════════════════════


def _serialize_task_for_pipeline(task: Task) -> dict[str, Any]:
    """Formato esperado pelo E5 legado:
      {
        "num": 1, "tarefa": "...", "categoria": "Invest",
        "prazo": "Abr/2026", "prioridade": "S", "status": "pendente",
        "ref": "D01"
      }
    Status é traduzido de volta para o vocabulário original do MD.
    """
    status_label = {
        "pending": "pendente",
        "in_progress": "em andamento",
        "done": "feito",
        "cancelled": "cancelado",
        "blocked": "bloqueado",
    }.get(task.status, task.status)

    prazo = task.deadline_label or (
        task.deadline_date.isoformat() if task.deadline_date else "—"
    )
    return {
        "num": task.number,
        "tarefa": task.title,
        "categoria": task.category,
        "prazo": prazo,
        "prioridade": task.priority,
        "status": status_label,
        "ref": task.ref or "—",
    }


def _all_tasks_ordered_sync(
    workspace_id: str,
    *,
    db: SyncSession,
) -> list[Task]:
    stmt = (
        select(Task)
        .where(Task.workspace_id == workspace_id)
        .order_by(Task.number.asc())
    )
    return list(db.execute(stmt).scalars().all())


async def _all_tasks_ordered_async(
    workspace_id: str,
    *,
    db: AsyncSession,
) -> list[Task]:
    stmt = (
        select(Task)
        .where(Task.workspace_id == workspace_id)
        .order_by(Task.number.asc())
    )
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


def build_tarefas_md_sync(
    workspace_id: str,
    *,
    db: SyncSession,
) -> str:
    """Versão sync — gera MD diretamente no worker sem async session.
    Replica a lógica de `task_service.export_markdown` com sync queries.
    """
    tasks = _all_tasks_ordered_sync(workspace_id, db=db)

    _priority_section = {
        "S": "Essenciais (S)",
        "R": "Recomendadas (R)",
        "O": "Opcionais (O)",
    }
    _status_md = {
        "pending": "pendente",
        "in_progress": "em andamento",
        "done": "feito",
        "cancelled": "cancelado",
        "blocked": "bloqueado",
    }

    lines: list[str] = []
    lines.append("# Tarefas — Pipeline (export do DB)")
    lines.append("")
    lines.append(
        "> Gerado por `pipeline_adapter.build_tarefas_md_sync`. "
        "Fonte de verdade: tabela `tasks` (ADR-074/075)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    active = [t for t in tasks if t.status not in ("done", "cancelled")]
    done = [t for t in tasks if t.status == "done"]

    for prio in ("S", "R", "O"):
        section_tasks = [t for t in active if t.priority == prio]
        if not section_tasks:
            continue
        lines.append(f"## {_priority_section[prio]}")
        lines.append("")
        lines.append("| # | Tarefa | Categoria | Prazo | Status | Ref |")
        lines.append("|---|---|---|---|---|---|")
        for t in section_tasks:
            prazo = t.deadline_label or (
                t.deadline_date.isoformat() if t.deadline_date else "—"
            )
            ref = t.ref or "—"
            title = t.title.replace("|", "\\|")
            lines.append(
                f"| {t.number} | {title} | {t.category} | {prazo} | "
                f"{_status_md.get(t.status, t.status)} | {ref} |"
            )
        lines.append("")
        lines.append("---")
        lines.append("")

    if done:
        lines.append("## Concluídas (histórico)")
        lines.append("")
        lines.append("| # | Tarefa | Data conclusão | Detalhe |")
        lines.append("|---|---|---|---|")
        for t in done:
            completed = (
                t.completed_at.date().isoformat() if t.completed_at else "—"
            )
            title = t.title.replace("|", "\\|")
            lines.append(
                f"| {t.number} | {title} | {completed} | "
                f"{t.status_reason or '—'} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


__all__ = [
    # Sync (worker)
    "build_goals_payload_sync",
    "build_tasks_payload_sync",
    "build_tarefas_md_sync",
    # Async (endpoints)
    "build_goals_payload",
    "build_tasks_payload",
    "build_tarefas_md",
]
