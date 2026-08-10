"""Write-path do enforce ([[ADR-364]] §Emenda 2026-08-10 · [[A40.l2]] §3e).

O gate morde aqui, no ato do operador, e nunca dentro do pipeline: `liberado` é
workspace-global e o dano é por-chave. O preflight prova que o operador olhou e que ligar
vai fazer alguma coisa — não é a prova de segurança, que vem da retenção por-run.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import PipelineRun, PipelineRunStatus
from backend.app.models.pipeline_run import PipelineStageLog
from backend.app.services import feature_flags_service
from backend.app.services.internal_ops.set_collapse_enforce import (
    FLAG_ENFORCE,
    FLAG_MEASURE,
    set_collapse_enforce,
)
from backend.tests import factories

pytestmark = pytest.mark.asyncio

_LIMPO = {
    "collapse_retention": {"lido": True, "degradado": False, "retencao_instavel": False},
    "collapse_precondition": {"sem_snapshot": 0, "tx_data_nao_iso": 0, "liberado": False},
}


async def _com_medicao(
    db,
    ws_id: str,
    summary: dict | None,
    *,
    idade=timedelta(hours=1),
    stage="reconcile_transactions",
):
    run = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed)
    db.add(run)
    await db.flush()
    db.add(_stage_log(run.id, summary, idade=idade, stage=stage))
    await db.flush()
    return run.id


def _stage_log(run_id: str, summary, *, idade, stage) -> PipelineStageLog:
    return PipelineStageLog(
        pipeline_run_id=run_id,
        stage=stage,
        status="completed",
        output_summary=summary,
        started_at=datetime.now(timezone.utc) - idade,
    )


async def _flags(db, ws_id: str) -> dict:
    return {
        flag: await feature_flags_service.is_enabled(ws_id, flag, db=db)
        for flag in (FLAG_ENFORCE, FLAG_MEASURE)
    }


async def test_liga_quando_o_mecanismo_esta_intacto(db: AsyncSession) -> None:
    ws = await factories.make_workspace(db)
    await _com_medicao(db, ws.id, _LIMPO)
    await db.commit()

    result = await set_collapse_enforce(db, ws.id, enabled=True, actor="op")
    await db.commit()

    assert result.ok, result.error
    assert await _flags(db, ws.id) == {FLAG_ENFORCE: True, FLAG_MEASURE: True}


# `liberado=False` no summary de propósito: é exatamente o estado do dogfood hoje
# (reprovado só por `vivacidade`), e ligar assim é a decisão da §Emenda 2026-08-10.
async def test_liberado_False_NAO_bloqueia__mas_e_registrado(db: AsyncSession) -> None:
    """Mutação: voltar a exigir `liberado is True`. O flip fica inalcançável no dogfood."""
    ws = await factories.make_workspace(db)
    await _com_medicao(db, ws.id, _LIMPO)
    await db.commit()

    result = await set_collapse_enforce(db, ws.id, enabled=True, actor="op")

    assert result.ok
    assert result.details["liberado"] is False


@pytest.mark.parametrize(
    ("mutacao", "esperado"),
    [
        (
            {"collapse_retention": {"lido": False, "degradado": False, "retencao_instavel": False}},
            "lido",
        ),
        (
            {"collapse_retention": {"lido": True, "degradado": True, "retencao_instavel": False}},
            "degradado",
        ),
        (
            {"collapse_retention": {"lido": True, "degradado": False, "retencao_instavel": True}},
            "retencao_instavel",
        ),
        ({"collapse_precondition": {"sem_snapshot": 1, "tx_data_nao_iso": 0}}, "sem_snapshot"),
        ({"collapse_precondition": {"sem_snapshot": 0, "tx_data_nao_iso": 2}}, "tx_data_nao_iso"),
    ],
    ids=["lido", "degradado", "instavel", "sem_snapshot", "tx_data_nao_iso"],
)
async def test_cada_clausula_do_mecanismo_reprova_sozinha(
    db: AsyncSession, mutacao, esperado
) -> None:
    ws = await factories.make_workspace(db)
    await _com_medicao(db, ws.id, {**_LIMPO, **mutacao})
    await db.commit()

    result = await set_collapse_enforce(db, ws.id, enabled=True, actor="op")

    assert not result.ok and result.error == "preflight_reprovado"
    assert any(esperado in c for c in result.details["clausulas"])


# Chave ausente é a mutação real de um refactor que renomeia o campo: com `.get(k, default)`
# ela leria como cláusula satisfeita, que é o fail-open que `_alvos` pagou para fechar.
async def test_chave_ausente_reprova__nao_e_lida_como_satisfeita(db: AsyncSession) -> None:
    ws = await factories.make_workspace(db)
    await _com_medicao(
        db, ws.id, {"collapse_retention": {"lido": True}, "collapse_precondition": {}}
    )
    await db.commit()

    result = await set_collapse_enforce(db, ws.id, enabled=True, actor="op")

    assert not result.ok
    assert any("ausente" in c for c in result.details["clausulas"])


async def test_sem_medicao_nao_liga(db: AsyncSession) -> None:
    """Summary sem `collapse_retention` não é run de referência — a ausência não autoriza."""
    ws = await factories.make_workspace(db)
    await _com_medicao(db, ws.id, {"outra_coisa": 1})
    await db.commit()

    result = await set_collapse_enforce(db, ws.id, enabled=True, actor="op")

    assert not result.ok and result.error == "medicao_ausente"


async def test_medicao_de_outro_stage_nao_serve(db: AsyncSession) -> None:
    """Mutação: tirar o filtro `stage == "reconcile_transactions"` do seletor."""
    ws = await factories.make_workspace(db)
    await _com_medicao(db, ws.id, _LIMPO, stage="analyze_finances")
    await db.commit()

    result = await set_collapse_enforce(db, ws.id, enabled=True, actor="op")

    assert not result.ok and result.error == "medicao_ausente"


async def test_medicao_velha_nao_liga(db: AsyncSession) -> None:
    """ "Vazio" é propriedade do corpus E do tempo — override nasce continuamente."""
    ws = await factories.make_workspace(db)
    await _com_medicao(db, ws.id, _LIMPO, idade=timedelta(hours=80))
    await db.commit()

    result = await set_collapse_enforce(db, ws.id, enabled=True, actor="op")

    assert not result.ok and result.error == "medicao_velha"


# Kill-switch com gate é kill-switch quebrado.
async def test_desligar_NAO_passa_por_preflight(db: AsyncSession) -> None:
    """Mutação: gatear também o `enabled=False`. Sem medição, o operador fica sem undo."""
    ws = await factories.make_workspace(db)
    await db.commit()

    result = await set_collapse_enforce(db, ws.id, enabled=False, actor="op")
    await db.commit()

    assert result.ok
    assert (await _flags(db, ws.id))[FLAG_ENFORCE] is False


async def test_ligar_escreve_TAMBEM_a_flag_de_medicao(db: AsyncSession) -> None:
    """Enforce sem measure é inerte: `_e3_build_collapser` devolve `None` e o adapter exige
    as duas. Escrever só a de enforce criaria estado silenciosamente morto."""
    ws = await factories.make_workspace(db)
    await _com_medicao(db, ws.id, _LIMPO)
    await feature_flags_service.set_flag(ws.id, FLAG_MEASURE, False, db=db)
    await db.commit()

    await set_collapse_enforce(db, ws.id, enabled=True, actor="op")
    await db.commit()

    assert (await _flags(db, ws.id))[FLAG_MEASURE] is True


async def test_a_flag_de_enforce_nasce_desligada_e_e_operator_only() -> None:
    """Sem `OPERATOR_ONLY`, a própria família liga o enforce pelo endpoint normal."""
    assert feature_flags_service.DEFAULTS[FLAG_ENFORCE] is False
    assert FLAG_ENFORCE in feature_flags_service.OPERATOR_ONLY
