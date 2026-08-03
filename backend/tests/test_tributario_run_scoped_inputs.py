"""Inputs run-scoped da cascata tributária (RV3-11 · A40.l9).

O agregado tributário é materializado em ``build_config_overrides_from_db`` →
``_setup_run_context`` no INÍCIO do run, e ``_latest_run_id`` resolve para o run
CORRENTE — cujo E4 ainda não existe. Todo input run-scoped sai zerado em
silêncio, e regen nunca corrige (cada run novo resolve para si mesmo de novo).

PR1 desta lane: o teste de regressão (xfail estrito até o PR2 mover a resolução
para resolver injetado) + o contador em WARNING que torna a falha visível.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from backend.app.services.tributario_input_builder import build_cascata_input_sync
from backend.tests import factories
from pipeline.domain.services.tributario.cascata_calculator import compute

_EVENT = "tributario_run_scoped_input_unavailable"


class _RecordingLogger:
    """Recorder imune a propagate=False do namespace mathoms.* (padrão de
    tests/test_llm_budget_service.py) — caplog não vê o logger em suíte cheia."""

    def __init__(self) -> None:
        self.warnings: list[tuple[str, dict]] = []

    def warning(self, msg: str, *args, extra=None, **kwargs) -> None:
        self.warnings.append((msg, extra or {}))


def _record_warnings(monkeypatch) -> _RecordingLogger:
    import backend.app.services.tributario_input_builder as mod

    recorder = _RecordingLogger()
    monkeypatch.setattr(mod, "logger", recorder)
    return recorder


# Sem chave "receita_pj": o E4 nunca emite esse agregado (ADR-330 — renda PJ é
# derivada como pro_labore + lucros). Fixture com a chave testaria mundo inexistente.
_RECEITAS_E4 = {"totais_por_categoria": {"pro_labore": 120000.0, "lucros_distribuidos": 60000.0}}
_DESPESAS_E4 = {"totais_por_categoria": {"das_simples": 14400.0, "iss": 0.0, "folha_pj": 0.0}}
_FLUXO_E4 = {"meses_ordenados": [f"2026-{m:02d}" for m in range(1, 13)]}


def _run(ws_id: str, *, started_at: datetime, status):
    from backend.app.models.pipeline_run import PipelineRun

    return PipelineRun(id=str(uuid4()), workspace_id=ws_id, status=status, started_at=started_at)


def _artifact(ws_id: str, run_id: str, key: str, content: dict):
    from backend.app.models.pipeline_artifact import PipelineArtifact

    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="categorize_transactions",
        artifact_key=key,
        content_json=content,
    )


async def _ws_with_profile(db, *, regime="simples"):
    from backend.app.models.workspace import Workspace

    ws = await factories.make_workspace(db)
    row = await db.get(Workspace, ws.id)
    row.business_profile_json = {"regime": regime, "anexo_simples": "III"}
    await db.commit()
    return ws


async def _seed_completed_run_with_e4(db, ws_id: str, *, started_at: datetime) -> str:
    from backend.app.models.pipeline_run import PipelineRunStatus

    run = _run(ws_id, started_at=started_at, status=PipelineRunStatus.completed)
    db.add(run)
    await db.flush()
    for key, content in (
        ("receitas", _RECEITAS_E4),
        ("despesas", _DESPESAS_E4),
        ("fluxo_mensal_detalhado", _FLUXO_E4),
        ("patrimonio", {"dados": {"imoveis_investimento": []}}),
    ):
        db.add(_artifact(ws_id, run.id, key, content))
    await db.commit()
    return run.id


async def _seed_current_run_without_e4(db, ws_id: str, *, started_at: datetime) -> str:
    from backend.app.models.pipeline_run import PipelineRunStatus

    run = _run(ws_id, started_at=started_at, status=PipelineRunStatus.running)
    db.add(run)
    await db.commit()
    return run.id


def _build_input_sync(ws_id: str):
    from backend.app.core.database import SyncSessionLocal

    with SyncSessionLocal() as sync_db:
        return build_cascata_input_sync(ws_id, db=sync_db)


@pytest.mark.asyncio
async def test_regressao_run_corrente_sem_e4_resolve_o_anterior_completo(db):
    """Caso 1 do critério de aceite — era xfail(strict) no PR1; verde desde o PR2."""
    t0 = datetime.now(timezone.utc)
    ws = await _ws_with_profile(db)
    await _seed_completed_run_with_e4(db, ws.id, started_at=t0 - timedelta(hours=2))
    await _seed_current_run_without_e4(db, ws.id, started_at=t0)

    inp = _build_input_sync(ws.id)

    assert inp.receita_pj_anual.amount > Decimal(
        "0"
    ), "input run-scoped zerou com run anterior completo disponível"
    assert inp.pro_labore_mensal.amount > Decimal("0")


@pytest.mark.asyncio
async def test_run_corrente_sem_e4_emite_warning_nao_silencio(db, monkeypatch):
    """Caso 2 (forma PR1): a indisponibilidade é declarada em WARNING, nunca muda."""
    ws = await _ws_with_profile(db)
    await _seed_current_run_without_e4(db, ws.id, started_at=datetime.now(timezone.utc))
    recorder = _record_warnings(monkeypatch)

    inp = _build_input_sync(ws.id)

    events = [extra for msg, extra in recorder.warnings if msg == _EVENT]
    assert events, "input zerou sem nenhum WARNING — a falha voltou a ser silenciosa"
    missing = {m for extra in events for m in extra.get("missing", [])}
    assert {"receitas", "despesas", "fluxo_mensal_detalhado"} <= missing
    # Sem NENHUM run com E4, o valor segue zero — mas declarado, não silencioso.
    assert inp.receita_pj_anual.amount == Decimal("0")
    assert inp.inputs_run_scoped_disponiveis is False


@pytest.mark.asyncio
async def test_run_com_e4_presente_nao_emite_warning(db, monkeypatch):
    """Contra-prova: com E4 no run resolvido, o contador fica mudo."""
    ws = await _ws_with_profile(db)
    await _seed_completed_run_with_e4(
        db, ws.id, started_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    recorder = _record_warnings(monkeypatch)

    inp = _build_input_sync(ws.id)

    assert not [msg for msg, _ in recorder.warnings if msg == _EVENT]
    assert inp.receita_pj_anual.amount > Decimal("0")


@pytest.mark.asyncio
async def test_perfil_incompleto_motivo_e_o_perfil_nao_o_input(db):
    """Caso 3: sem BusinessProfile, o motivo declarado é o perfil — não o input vazio."""
    ws = await factories.make_workspace(db)
    await db.commit()
    await _seed_current_run_without_e4(db, ws.id, started_at=datetime.now(timezone.utc))

    out = compute(_build_input_sync(ws.id))

    assert out.regime_nao_suportado is True
    assert out.motivo_nao_suportado == "perfil_incompleto"


@pytest.mark.asyncio
async def test_warning_nao_carrega_valor_monetario(db, monkeypatch):
    """O contador declara indisponibilidade sem ecoar valores (CLAUDE.md §Logging)."""
    import re

    ws = await _ws_with_profile(db)
    await _seed_current_run_without_e4(db, ws.id, started_at=datetime.now(timezone.utc))
    recorder = _record_warnings(monkeypatch)

    _build_input_sync(ws.id)

    money_re = re.compile(r"R\$\s?\d|\d+[.,]\d{2}\b")
    assert recorder.warnings, "sem warning, o teste não observa o caminho"
    for msg, extra in recorder.warnings:
        blob = msg + repr(extra)
        assert not money_re.search(blob), f"valor monetário no log: {blob[:160]}"


@pytest.mark.asyncio
async def test_sem_e4_algum_cascata_declara_o_sinal(db):
    """Caso 2 (forma PR2): o zero run-scoped vira sinal no output — canal CTO-05."""
    ws = await _ws_with_profile(db)
    await _seed_current_run_without_e4(db, ws.id, started_at=datetime.now(timezone.utc))

    out = compute(_build_input_sync(ws.id))

    assert "inputs_run_scoped_indisponiveis" in out.signals


@pytest.mark.asyncio
async def test_com_e4_disponivel_sem_sinal_de_ausencia(db):
    """Contra-prova do sinal: dado presente não é declarado ausente."""
    ws = await _ws_with_profile(db)
    await _seed_completed_run_with_e4(
        db, ws.id, started_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )

    out = compute(_build_input_sync(ws.id))

    assert "inputs_run_scoped_indisponiveis" not in out.signals
    assert out.receita_bruta.amount > Decimal("0")


async def _seed_running_run_with_e4(db, ws_id: str, *, started_at: datetime, receitas: dict):
    """Run corrente (running) COM E4 já escrito — o cenário de frescor do PR2."""
    from backend.app.models.pipeline_run import PipelineRunStatus

    run = _run(ws_id, started_at=started_at, status=PipelineRunStatus.running)
    db.add(run)
    await db.flush()
    for key, content in (
        ("receitas", receitas),
        ("despesas", _DESPESAS_E4),
        ("fluxo_mensal_detalhado", _FLUXO_E4),
        ("patrimonio", {"dados": {"imoveis_investimento": []}}),
    ):
        db.add(_artifact(ws_id, run.id, key, content))
    await db.commit()


@pytest.mark.asyncio
async def test_run_corrente_com_e4_escrito_e_o_resolvido(db):
    """Frescor: no meio do run (pós-E4), a resolução pega o run CORRENTE — não o
    anterior. É o que o resolver injetado do PR2 explora em E5.N."""
    t0 = datetime.now(timezone.utc)
    ws = await _ws_with_profile(db)
    await _seed_completed_run_with_e4(db, ws.id, started_at=t0 - timedelta(hours=2))
    receitas_novas = {"totais_por_categoria": {"pro_labore": 240000.0, "lucros_distribuidos": 0.0}}
    await _seed_running_run_with_e4(db, ws.id, started_at=t0, receitas=receitas_novas)

    inp = _build_input_sync(ws.id)

    # 240k/12 = 20k de pró-labore mensal ⇒ resolveu o corrente (o anterior daria 10k).
    assert inp.pro_labore_mensal.amount == Decimal("20000")


@pytest.mark.asyncio
async def test_db_resolver_entrega_secao_fresca_do_run_com_e4(db):
    """PR2: o resolver injetado devolve a seção do último run COM E4 — é ele que
    o E5.N consome no lugar do goals.json materializado em t=0."""
    from backend.app.core.database import SyncSessionLocal
    from backend.app.services.db_tributario_section_resolver import (
        DBTributarioSectionResolver,
    )

    ws = await _ws_with_profile(db)
    await _seed_completed_run_with_e4(
        db, ws.id, started_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )

    with SyncSessionLocal() as sync_db:
        section = DBTributarioSectionResolver(session=sync_db).resolve(ws.id)

    assert section is not None
    assert section["cascata"]["receita_bruta"] > 0


@pytest.mark.asyncio
async def test_db_resolver_falha_degrada_para_none(db, monkeypatch):
    """Resolver é best-effort: exceção interna vira None (caller usa o fallback)."""
    import backend.app.services.pipeline.pipeline_adapter as adapter
    from backend.app.core.database import SyncSessionLocal
    from backend.app.services.db_tributario_section_resolver import (
        DBTributarioSectionResolver,
    )

    def _boom(*a, **k):
        raise RuntimeError("db exploded")

    monkeypatch.setattr(adapter, "_build_tributario_section_sync", _boom)
    ws = await _ws_with_profile(db)

    with SyncSessionLocal() as sync_db:
        assert DBTributarioSectionResolver(session=sync_db).resolve(ws.id) is None
