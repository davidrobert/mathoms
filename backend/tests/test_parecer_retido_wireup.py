"""A40.l20 PR2 · ADR-366 — o desfecho retido ganha produtor: o orquestrador o persiste."""

# Antes deste PR, `outcome == "retido"` era inalcançável em produção. A medição de
# 2026-08-07 (registrada no PR) encontrou UMA barreira real e duas contrafactuais:
#
#   0a  `if outcome.delivered:` no `_record_stage_result` — a real. O parecer é
#       `degradable`, retido devolve `success: False`, logo `StageOutcome.degraded`,
#       cujo `.delivered` é False. A chamada de persistência nunca ocorria, e todo o
#       corpo de `_should_persist_planner_review` era dead code neste caminho.
#   1   `not result.success` — barraria, se 0a fosse aberta sozinha.
#   2   `detail["status"] == "needs_review"` — idem.
#
# Duas hipóteses do briefing foram REFUTADAS aqui e não ganham teste, porque não há
# mecanismo a proteger: o ramo `_record_stage_needs_review` NÃO está no caminho (a
# linha `if result.success and _has_validation_errors(result)` curto-circuita em
# `success=False`, e o stage do parecer nunca emite bloco `validation`); e
# `"persona_hash" in detail` já não barrava — o PR1 pôs `_audit_detail` no retorno
# do retido. `persona_hash` ganha teste mesmo assim, mas como porta que tem de
# CONTINUAR fechada para a rota de exceção.

from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.models.planner_review import PlannerReview
from backend.app.tasks.pipeline_task import _should_persist_planner_review
from backend.tests.test_planner_review_persistence import _generation_result
from backend.tests.test_stage_degradation import (  # noqa: F401 — `seeded` é fixture
    _E5_KEY,
    _E5_STAGE,
    _PARECER,
    _drive,
    _reports,
    _run_row,
    _stage_status,
    seeded,
)
from pipeline.orchestrator import StageResult

_E5_PAYLOAD = {"score": {"valor": 7, "classificacao": "Bom"}, "periodo_dados": "2026-01"}
_PROSA_DE_OPERADOR = "evidencia unverified (severidade alta): risco:3"


def _detail_retido(store, reason: str | None) -> dict:
    """Detail do retido pelo PRODUTOR real — ele também grava o artifact no store."""
    from pipeline.stages.parecer_planejador import _needs_review_return

    result = _generation_result(
        status="needs_review", error_detail=_PROSA_DE_OPERADOR, retention_reason=reason
    )
    return _needs_review_return(result, "ws-test", store)


class _ParecerRetido:
    """Stage fake: E5 entrega; o parecer retém pelo caminho real do produtor."""

    def __init__(self, reason: str | None = "parecer.sigilo"):
        self._reason = reason

    def __call__(self, ctx, stage):
        if stage == _E5_STAGE:
            ctx.artifact_store.write(_E5_STAGE, _E5_KEY, dict(_E5_PAYLOAD))
            return StageResult(stage=stage, success=True, duration_ms=1.0, detail={"ok": True})
        detail = _detail_retido(ctx.artifact_store, self._reason)
        # Espelha `pipeline/orchestrator.py:270` — o `success` do StageResult é
        # derivado do detail, nunca fixado à mão: se o produtor mudar, o teste segue.
        return StageResult(
            stage=stage, success=bool(detail["success"]), duration_ms=1.0, detail=detail
        )


async def _review_row(seed) -> PlannerReview | None:
    async with seed["async_session"]() as s:
        rows = await s.execute(
            select(PlannerReview).where(PlannerReview.pipeline_run_id == seed["run_id"])
        )
        return rows.scalars().one_or_none()


# ───────────── porta 0a: o call-site, medida como a única barreira real ─────────────


@pytest.mark.asyncio
async def test_parecer_retido_vira_row_pelo_caminho_do_run(seeded):
    """Mata a mutação que re-aninha a persistência dentro de `if outcome.delivered`."""
    _drive(seeded, _ParecerRetido(), stages=[_E5_STAGE, _PARECER])

    review = await _review_row(seeded)
    assert review is not None, "sem row, a API responde 404 e a UI diz 'ainda não gerado'"
    assert review.outcome == "retido"
    assert review.retention_reason == "parecer.sigilo"
    # `status` é o eixo de PUBLICAÇÃO e não se move com o desfecho (ADR-366 §D1).
    assert review.status == "Gerado"
    assert (review.items_shown_count, review.items_dropped_count) == (0, 0)


@pytest.mark.asyncio
async def test_row_do_retido_nasce_ao_lado_do_stage_degradado_e_do_relatorio(seeded):
    """A row convive com a degradação — o desfecho do parecer é eixo próprio (ADR-357)."""
    from backend.app.models.pipeline_run import PipelineRunStatus, PipelineStageStatus

    _drive(seeded, _ParecerRetido(), stages=[_E5_STAGE, _PARECER])

    assert await _stage_status(seeded, _PARECER) is PipelineStageStatus.degraded
    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.partial_failure
    assert run.failed_at_stage is None
    assert len(await _reports(seeded)) == 1


@pytest.mark.asyncio
async def test_row_do_run_atende_a_api_sem_prosa_de_operador(seeded):
    """Fecha a cadeia: a row que o run cria é a que o leitor serve, e ela não vaza."""
    from backend.app.api.planner_review import _render_review

    _drive(seeded, _ParecerRetido(), stages=[_E5_STAGE, _PARECER])
    review = await _review_row(seeded)

    # `db=None` de propósito: no retido o `_render_review` decide ANTES de carregar
    # o artifact (ADR-366 §D5). Se algum dia carregar, este teste quebra alto em vez
    # de servir os 3 pontos fortes "placeholder" a um cliente premium.
    resposta = await _render_review(None, workspace_id=seeded["ws_id"], review=review)

    assert resposta.content is None
    assert resposta.retention.reason == "parecer.sigilo"
    corpo = resposta.model_dump_json()
    assert _PROSA_DE_OPERADOR not in corpo
    for proibido in ("error_detail", "risco:", "unverified", "needs_review", "sigilo §13"):
        assert proibido not in corpo, proibido


@pytest.mark.asyncio
async def test_indisponibilidade_tecnica_nao_vira_row_pelo_caminho_do_run(seeded):
    """Sem `retention_reason` nada foi gerado; a decisão é do domínio, não do filtro."""
    # Se o filtro do orquestrador duplicasse `_is_persistable`, esta asserção passaria
    # pelo motivo errado — ela existe para provar que a regra do domínio é ALCANÇADA.
    _drive(seeded, _ParecerRetido(reason=None), stages=[_E5_STAGE, _PARECER])

    assert await _review_row(seeded) is None


async def _codigo_de_ausencia(seed) -> str:
    from backend.app.api.planner_review import _absence_code

    async with seed["async_session"]() as s:
        return await _absence_code(s, workspace_id=seed["ws_id"], run_id=seed["run_id"])


@pytest.mark.asyncio
async def test_indisponibilidade_responde_generation_unavailable(seeded):
    """Sem row o 404 tem de dizer "tentamos e não deu", não "ainda não gerado"."""
    # O discriminador é o artifact, não `stage_logs`: o produtor grava mesmo nos 2
    # ramos de indisponibilidade, e ele sobrevive à degradação (ADR-357 §6).
    _drive(seeded, _ParecerRetido(reason=None), stages=[_E5_STAGE, _PARECER])

    assert await _review_row(seeded) is None
    assert await _codigo_de_ausencia(seeded) == "generation_unavailable"


async def _set_tier(seed, tier: str) -> None:
    """O `_seed` compartilhado não declara tier e cai no default `free` do model."""
    from sqlalchemy import update

    from backend.app.models.pipeline_run import PipelineRun

    async with seed["async_session"]() as s:
        await s.execute(
            update(PipelineRun).where(PipelineRun.id == seed["run_id"]).values(tier_at_run=tier)
        )
        await s.commit()


@pytest.mark.asyncio
async def test_run_premium_que_nao_tentou_o_parecer_segue_not_generated_yet(seeded):
    """Polaridade: sem esta, um `_absence_code` que sempre retorna o novo código passa."""
    await _set_tier(seeded, "premium")
    _drive(seeded, _ParecerRetido(), stages=[_E5_STAGE])

    assert await _codigo_de_ausencia(seeded) == "not_generated_yet"


@pytest.mark.asyncio
async def test_run_free_que_nao_tentou_o_parecer_e_tier_gated(seeded):
    """Free e premium sem artifact eram O MESMO código — a copy da A40.l22 precisa dos dois."""
    await _set_tier(seeded, "free")
    _drive(seeded, _ParecerRetido(), stages=[_E5_STAGE])

    assert await _codigo_de_ausencia(seeded) == "tier_gated"


# Um run free COM artifact tentou de fato (override, re-run pós-downgrade): dizer
# "não incluído no plano" ali mandaria comprar o que já foi executado.
@pytest.mark.asyncio
async def test_free_que_TENTOU_nao_e_tier_gated(seeded):
    """Ordem das cláusulas: o artifact vence o tier. Sem esta, inverter a ordem passa."""
    await _set_tier(seeded, "free")
    _drive(seeded, _ParecerRetido(reason=None), stages=[_E5_STAGE, _PARECER])

    assert await _codigo_de_ausencia(seeded) == "generation_unavailable"


# ───────────── portas 1 e 2: as duas condições que saíram do filtro ─────────────


def _stage_result_retido() -> StageResult:
    class _NullStore:
        def write(self, *_a, **_kw) -> None:
            return None

    detail = _detail_retido(_NullStore(), "parecer.citacao_nao_confirmada")
    return StageResult(
        stage=_PARECER, success=bool(detail["success"]), duration_ms=1.0, detail=detail
    )


def test_filtro_aceita_o_retido_apesar_de_success_false_e_needs_review():
    """As 2 asserções de fixture são o que torna a 3ª prova de mutação por-porta."""
    result = _stage_result_retido()
    # Porta 1: re-adicionar `not result.success` ao filtro deixa este teste vermelho.
    assert result.success is False
    # Porta 2: re-adicionar `status == "needs_review"` deixa este teste vermelho.
    assert result.detail["status"] == "needs_review"
    assert _should_persist_planner_review(_PARECER, result) is True


def test_filtro_segue_aceitando_o_parecer_entregue():
    """Regressão: abrir o retido não pode custar o caminho comum."""
    from backend.tests.test_planner_review_persistence import make_detail

    result = StageResult(stage=_PARECER, success=True, duration_ms=1.0, detail=make_detail())
    assert _should_persist_planner_review(_PARECER, result) is True


# ───────────── portas que têm de CONTINUAR fechadas ─────────────


@pytest.mark.parametrize("detail", [None, {"log_tail": {"events": []}}])
def test_filtro_recusa_a_rota_de_excecao(detail):
    """`persona_hash` fecha SystemExit/Exception, cujo detail não tem auditoria alguma."""
    # A persistência indexa 5 campos de auditoria em colunas NOT NULL; sem a porta,
    # a rota de exceção daria KeyError em vez de simplesmente não persistir.
    result = StageResult(stage=_PARECER, success=False, duration_ms=1.0, detail=detail)
    assert _should_persist_planner_review(_PARECER, result) is False


def test_filtro_recusa_skip_mesmo_quando_ele_ganha_campos_de_auditoria():
    """A guarda `skipped` só é provável contra o refactor que ela existe para barrar."""
    # Medido: com o skip de HOJE a guarda é indistinguível de código morto —
    # `persona_hash` já o barraria, e removê-la não deixa teste vermelho. O refactor
    # plausível é o espelho do que o PR1 fez no ramo irmão (pôs `_audit_detail` no
    # retido porque a persistência precisava): um skip que passe a ecoar tier/custo.
    # É aí que a guarda decide entre 404 honesto e row fabricada para quem não pagou.
    detail = _skip_detail_do_produtor()
    assert detail.get("skipped") is True
    assert "persona_hash" not in detail, "se isto mudar, `skipped` vira a única defesa"

    result = StageResult(
        stage=_PARECER, success=True, duration_ms=1.0, detail={**detail, **_audit_do_produtor()}
    )
    assert _should_persist_planner_review(_PARECER, result) is False


def _skip_detail_do_produtor() -> dict:
    """Skip vindo do stage real (tier free, ADR-208 §D1) — não de dict escrito à mão."""
    from types import SimpleNamespace

    from pipeline.stages.parecer_planejador import run as parecer_run

    class _StoreComE5:
        def read(self, *_a, **_kw) -> dict:
            return dict(_E5_PAYLOAD)

    ctx = SimpleNamespace(
        get_artifact_store=lambda: _StoreComE5(),
        config_overrides={"workspace_meta": {"tier": "free"}},
    )
    return parecer_run(ctx)


def _audit_do_produtor() -> dict:
    """Os 5 campos de auditoria, pelo produtor real do stage."""
    from pipeline.stages.parecer_planejador import _audit_detail

    return _audit_detail(_generation_result())


def test_filtro_recusa_stage_que_nao_e_o_parecer():
    """O filtro é a única coisa entre o hook e TODO stage do pipeline."""
    result = _stage_result_retido()
    assert _should_persist_planner_review("analyze_finances", result) is False
