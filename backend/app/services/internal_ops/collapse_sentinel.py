"""Sentinela pós-flip do colapso cross-documento — eixo (7) do §Critério de saída [[A40.l2]].

Lê a série que o E3 publica em `pipeline_stage_logs.output_summary` (`collapse_retention`) e
emite **alertas nomeados**, não um número solto: "reservatório = 460" não diz a ninguém se é
para agir. Cada alerta tem limiar declarado e a ação que ele pede.

O dono é o **operador do console** — a série aparece em `GET /admin/metrics`, junto das outras
métricas de degradação, porque sentinela em dashboard que ninguém abre é prosa.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_run import PipelineStageLog

_STAGE = "reconcile_transactions"

# Retenção recorrente é o gatilho declarado da re-ancoragem ([[ADR-364]] §Emenda 2026-08-09:
# "`retido_por_override > 0` em qualquer workspace por 2 runs consecutivos"). Dois, não um:
# um run isolado é o usuário editando a categorização agora, o que é uso normal.
_RUNS_PARA_RECORRENCIA = 2


async def _serie(db: AsyncSession, *, cutoff: datetime) -> list[dict]:
    """`collapse_retention` de cada execução do E3 na janela, do mais recente ao mais antigo."""
    rows = await db.execute(
        select(PipelineStageLog.output_summary)
        .where(PipelineStageLog.stage == _STAGE, PipelineStageLog.started_at >= cutoff)
        .order_by(PipelineStageLog.started_at.desc())
    )
    return [
        summary["collapse_retention"]
        for (summary,) in rows.all()
        if isinstance(summary, dict) and isinstance(summary.get("collapse_retention"), dict)
    ]


def _cresceu(serie: list[dict], campo: str) -> bool:
    """Compara o run mais recente com o mais antigo da janela; `False` com um só run."""
    valores = [s.get(campo) for s in serie if isinstance(s.get(campo), int)]
    return len(valores) >= 2 and valores[0] > valores[-1]


def _alertas(serie: list[dict]) -> list[str]:
    alertas = []
    if any(s.get("degradado") is True for s in serie):
        alertas.append("retencao_inerte")
    if any(s.get("retencao_instavel") is True for s in serie):
        alertas.append("override_durante_o_run")
    retidos = sum(1 for s in serie if (s.get("retido_por_override") or 0) > 0)
    if retidos >= _RUNS_PARA_RECORRENCIA:
        alertas.append("retencao_recorrente")
    if _cresceu(serie, "reservatorio_llm_sem_gemea"):
        alertas.append("cobertura_erodindo")
    return alertas


# `runs` explícito no payload: sem ele, "0 alertas" é indistinguível de "0 runs mediram" —
# o zero-ambíguo que esta lane pagou quatro vezes.
async def collapse_sentinel(db: AsyncSession, *, cutoff: datetime) -> dict:
    """Série do colapso na janela + alertas nomeados, para `GET /admin/metrics`."""
    serie = await _serie(db, cutoff=cutoff)
    ultimo = serie[0] if serie else {}
    return {
        "runs": len(serie),
        "degradado": bool(ultimo.get("degradado")),
        "retido_por_override": ultimo.get("retido_por_override"),
        "retido_por_override_manual": ultimo.get("retido_por_override_manual"),
        "retido_por_override_rule": ultimo.get("retido_por_override_rule"),
        "reservatorio_llm_sem_gemea": ultimo.get("reservatorio_llm_sem_gemea"),
        "removals_publicadas": ultimo.get("removals_publicadas"),
        "alertas": _alertas(serie),
    }
