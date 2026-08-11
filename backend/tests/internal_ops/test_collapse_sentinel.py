"""Sentinela pós-flip do colapso — eixo (7) do §Critério de saída da [[A40.l2]].

O eixo pede "sentinela com número e dono". O número sozinho não serve: "reservatório = 460"
não diz a ninguém se é para agir. Cada alerta abaixo tem limiar declarado, e cada limiar tem a
mutação que o derruba.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import PipelineRun, PipelineRunStatus
from backend.app.models.pipeline_run import PipelineStageLog
from backend.app.services.internal_ops.collapse_sentinel import collapse_sentinel
from backend.tests import factories

pytestmark = pytest.mark.asyncio

_LIMPO = {
    "lido": True,
    "degradado": False,
    "retencao_instavel": False,
    "retido_por_override": 0,
    "reservatorio_llm_sem_gemea": 441,
    "removals_publicadas": 453,
}
_CUTOFF = datetime.now(timezone.utc) - timedelta(days=30)


async def _runs(db, ws_id: str, *retencoes: dict | None, stage="reconcile_transactions"):
    """Semeia um E3 por retenção, do mais ANTIGO ao mais recente."""
    for i, retencao in enumerate(retencoes):
        run = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed)
        db.add(run)
        await db.flush()
        summary = None if retencao is None else {"collapse_retention": retencao}
        db.add(
            PipelineStageLog(
                pipeline_run_id=run.id,
                stage=stage,
                status="completed",
                output_summary=summary,
                started_at=datetime.now(timezone.utc) - timedelta(hours=len(retencoes) - i),
            )
        )
    await db.flush()


async def test_janela_limpa_nao_alerta(db: AsyncSession) -> None:
    ws = await factories.make_workspace(db)
    await _runs(db, ws.id, _LIMPO, _LIMPO)
    await db.commit()

    sentinela = await collapse_sentinel(db, cutoff=_CUTOFF)

    assert sentinela["alertas"] == [] and sentinela["runs"] == 2


# "0 alertas" com `runs == 0` é o zero-ambíguo que esta lane pagou quatro vezes: nada mediu.
async def test_runs_zero_e_estado_proprio__nao_janela_limpa(db: AsyncSession) -> None:
    """Mutação: tirar `runs` do payload. O dono não distingue "limpo" de "não medi"."""
    ws = await factories.make_workspace(db)
    await _runs(db, ws.id, None)
    await db.commit()

    assert (await collapse_sentinel(db, cutoff=_CUTOFF))["runs"] == 0


async def test_degradado_alerta__a_retencao_ficou_inerte(db: AsyncSession) -> None:
    ws = await factories.make_workspace(db)
    await _runs(db, ws.id, {**_LIMPO, "degradado": True})
    await db.commit()

    assert "retencao_inerte" in (await collapse_sentinel(db, cutoff=_CUTOFF))["alertas"]


async def test_instavel_alerta__override_criado_durante_o_run(db: AsyncSession) -> None:
    ws = await factories.make_workspace(db)
    await _runs(db, ws.id, {**_LIMPO, "retencao_instavel": True})
    await db.commit()

    assert "override_durante_o_run" in (await collapse_sentinel(db, cutoff=_CUTOFF))["alertas"]


# Limiar de 2 runs vem do gatilho declarado na ADR-364 §Emenda 2026-08-09. UM run com retenção
# é o usuário editando a categorização agora — uso normal, não sinal.
async def test_retencao_em_UM_run_nao_alerta(db: AsyncSession) -> None:
    ws = await factories.make_workspace(db)
    await _runs(db, ws.id, _LIMPO, {**_LIMPO, "retido_por_override": 3})
    await db.commit()

    assert "retencao_recorrente" not in (await collapse_sentinel(db, cutoff=_CUTOFF))["alertas"]


async def test_retencao_em_DOIS_runs_alerta(db: AsyncSession) -> None:
    """Mutação: baixar o limiar para 1. Alerta em todo mês que o usuário recategoriza."""
    ws = await factories.make_workspace(db)
    await _runs(
        db, ws.id, {**_LIMPO, "retido_por_override": 1}, {**_LIMPO, "retido_por_override": 2}
    )
    await db.commit()

    assert "retencao_recorrente" in (await collapse_sentinel(db, cutoff=_CUTOFF))["alertas"]


# A ADR-364 §Decisão 2 diz que "a retenção VAI crescer — a cobertura do enforce erode com o
# tempo, e o número tem de ser lido, não presumido zero".
async def test_reservatorio_crescendo_alerta(db: AsyncSession) -> None:
    ws = await factories.make_workspace(db)
    await _runs(
        db,
        ws.id,
        {**_LIMPO, "reservatorio_llm_sem_gemea": 441},
        {**_LIMPO, "reservatorio_llm_sem_gemea": 600},
    )
    await db.commit()

    assert "cobertura_erodindo" in (await collapse_sentinel(db, cutoff=_CUTOFF))["alertas"]


async def test_reservatorio_estavel_nao_alerta(db: AsyncSession) -> None:
    """Mutação: alertar em `>=` em vez de `>`. Todo par de runs iguais viraria alerta."""
    ws = await factories.make_workspace(db)
    await _runs(db, ws.id, _LIMPO, _LIMPO)
    await db.commit()

    assert "cobertura_erodindo" not in (await collapse_sentinel(db, cutoff=_CUTOFF))["alertas"]


async def test_run_unico_nao_infere_tendencia(db: AsyncSession) -> None:
    """Dois pontos são o mínimo para direção; um só não é tendência nenhuma."""
    ws = await factories.make_workspace(db)
    await _runs(db, ws.id, {**_LIMPO, "reservatorio_llm_sem_gemea": 900})
    await db.commit()

    assert (await collapse_sentinel(db, cutoff=_CUTOFF))["alertas"] == []


async def test_stage_alheio_nao_entra_na_serie(db: AsyncSession) -> None:
    """Mutação: tirar o filtro de stage. Qualquer stage com a chave entraria na série."""
    ws = await factories.make_workspace(db)
    await _runs(db, ws.id, {**_LIMPO, "degradado": True}, stage="analyze_finances")
    await db.commit()

    sentinela = await collapse_sentinel(db, cutoff=_CUTOFF)

    assert sentinela["runs"] == 0 and sentinela["alertas"] == []
