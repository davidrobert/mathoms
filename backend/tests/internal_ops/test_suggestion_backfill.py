"""Testes do backfill heurístico de Suggestions pré-ADR-290 (F4 — PLAN-suggestion-lifecycle)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend.app.models.suggestion import Suggestion
from backend.app.services.internal_ops.suggestion_backfill import (
    backfill_supersede_pending_suggestions,
)
from backend.tests.factories import make_workspace

pytestmark = pytest.mark.asyncio

_OLD = datetime.now(timezone.utc) - timedelta(days=7)


async def _seed(db, ws_id: str, *, title: str, section: str = "S3", **overrides) -> Suggestion:
    defaults = {
        "workspace_id": ws_id,
        "section_id": section,
        "kind": "parecer_planejador",
        "origin": "llm",
        "severity": "warning",
        "title": title,
        "rationale": "r",
        "dedup_key": f"{abs(hash((ws_id, title, section, str(overrides)))):064d}"[:64],
        "status": "Pendente",
        "created_at": _OLD,
        "updated_at": _OLD,
    }
    s = Suggestion(**{**defaults, **overrides})
    db.add(s)
    await db.flush()
    return s


async def _statuses(db, ws_id: str) -> dict[str, str]:
    rows = (
        (await db.execute(select(Suggestion).where(Suggestion.workspace_id == ws_id)))
        .scalars()
        .all()
    )
    return {s.id: s.status for s in rows}


async def test_workspace_obrigatorio_inexistente_falha(db):
    result = await backfill_supersede_pending_suggestions(
        db, workspace_id="nao-existe", actor="test", apply=False
    )
    assert result.ok is False
    assert result.error == "workspace_not_found"


async def test_dry_run_default_nao_muta_e_emite_relatorio(db):
    ws = await make_workspace(db)
    a = await _seed(db, ws.id, title="Aumentar reserva de emergência")
    b = await _seed(
        db, ws.id, title="aumentar  reserva de emergência", created_at=_OLD - timedelta(days=1)
    )
    result = await backfill_supersede_pending_suggestions(
        db, workspace_id=ws.id, actor="test", apply=False
    )
    assert result.ok and result.details["dry_run"] is True
    assert result.details["superseded_planned"] == 1
    grupo = result.details["report"][0]
    assert grupo["mantem"]["id"] == a.id
    assert grupo["supersede_ids"] == [b.id]
    statuses = await _statuses(db, ws.id)
    assert set(statuses.values()) == {"Pendente"}


async def test_apply_mantem_mais_recente_e_supersede_resto(db):
    ws = await make_workspace(db)
    recente = await _seed(db, ws.id, title="Rever alocação internacional")
    antiga1 = await _seed(
        db, ws.id, title="REVER alocação   internacional", created_at=_OLD - timedelta(days=2)
    )
    antiga2 = await _seed(
        db, ws.id, title="rever alocação internacional", created_at=_OLD - timedelta(days=5)
    )
    outra_secao = await _seed(db, ws.id, title="Rever alocação internacional", section="S7")

    result = await backfill_supersede_pending_suggestions(
        db, workspace_id=ws.id, actor="test", apply=True
    )
    assert result.ok and result.details["superseded"] == 2
    statuses = await _statuses(db, ws.id)
    assert statuses[recente.id] == "Pendente"
    assert statuses[antiga1.id] == "Superseded"
    assert statuses[antiga2.id] == "Superseded"
    assert statuses[outra_secao.id] == "Pendente"  # grupo é (section, título)


async def _seed_intocaveis(db, ws_id: str, outra_id: str) -> dict[str, str]:
    """Seeds que o backfill NUNCA pode tocar; retorna {id: status esperado}."""
    aceita = await _seed(db, ws_id, title="Tese aceita", status="Aceita")
    descartada = await _seed(db, ws_id, title="Tese descartada", status="Descartada")
    det = await _seed(
        db, ws_id, title="Tese determinística", origin="deterministic", kind="reserva_insuficiente"
    )
    de_fora = await _seed(db, outra_id, title="Tese de outro workspace")
    dup_de_fora = await _seed(
        db, outra_id, title="tese de outro workspace", created_at=_OLD - timedelta(days=1)
    )
    return {
        aceita.id: "Aceita",
        descartada.id: "Descartada",
        det.id: "Pendente",
        de_fora.id: "Pendente",
        dup_de_fora.id: "Pendente",
    }


async def test_nao_toca_aceitas_descartadas_deterministicas_nem_outro_workspace(db):
    ws = await make_workspace(db)
    outra = await make_workspace(db)
    esperado = await _seed_intocaveis(db, ws.id, outra.id)
    result = await backfill_supersede_pending_suggestions(
        db, workspace_id=ws.id, actor="test", apply=True
    )
    assert result.ok and result.details["superseded"] == 0
    statuses = {**(await _statuses(db, ws.id)), **(await _statuses(db, outra.id))}
    assert {k: statuses[k] for k in esperado} == esperado


async def test_mode_invalido_falha(db):
    ws = await make_workspace(db)
    result = await backfill_supersede_pending_suggestions(
        db, workspace_id=ws.id, actor="test", apply=False, mode="semantic"
    )
    assert result.ok is False
    assert result.error == "invalid_mode"


async def _seed_two_batches(db, ws_id: str) -> tuple[list[str], list[str]]:
    """(ids antigas, ids do burst recente) — burst = janela de 1h do mais novo."""
    velha1 = await _seed(db, ws_id, title="Run antigo A", created_at=_OLD - timedelta(days=10))
    velha2 = await _seed(db, ws_id, title="Run antigo B", created_at=_OLD - timedelta(days=3))
    nova1 = await _seed(db, ws_id, title="Run novo A", created_at=_OLD)
    nova2 = await _seed(db, ws_id, title="Run novo B", created_at=_OLD - timedelta(minutes=30))
    return [velha1.id, velha2.id], [nova1.id, nova2.id]


async def test_latest_batch_dry_run_lista_kept_e_nao_muta(db):
    ws = await make_workspace(db)
    _velhas, novas = await _seed_two_batches(db, ws.id)
    dry = await backfill_supersede_pending_suggestions(
        db, workspace_id=ws.id, actor="test", apply=False, mode="latest_batch"
    )
    assert dry.ok and dry.details["superseded_planned"] == 2
    assert set(dry.details["kept_ids"]) == set(novas)
    assert set((await _statuses(db, ws.id)).values()) == {"Pendente"}


async def test_latest_batch_apply_supersede_anteriores_ao_burst(db):
    """Modo 'último parecer vence': lote mais recente (janela 1h) fica; resto Superseded."""
    ws = await make_workspace(db)
    velhas, novas = await _seed_two_batches(db, ws.id)
    result = await backfill_supersede_pending_suggestions(
        db, workspace_id=ws.id, actor="test", apply=True, mode="latest_batch"
    )
    assert result.ok and result.details["superseded"] == 2
    statuses = await _statuses(db, ws.id)
    assert all(statuses[i] == "Pendente" for i in novas)
    assert all(statuses[i] == "Superseded" for i in velhas)


async def test_concorrencia_ignora_criadas_apos_inicio(db):
    """Pendente criada depois do início do backfill (pipeline ativo) fica fora."""
    ws = await make_workspace(db)
    futuro = datetime.now(timezone.utc) + timedelta(minutes=5)
    futura = await _seed(db, ws.id, title="Criada durante o backfill", created_at=futuro)
    dup = await _seed(db, ws.id, title="criada durante o backfill", created_at=futuro)
    result = await backfill_supersede_pending_suggestions(
        db, workspace_id=ws.id, actor="test", apply=True
    )
    assert result.ok and result.details["superseded"] == 0
    statuses = await _statuses(db, ws.id)
    assert statuses[futura.id] == "Pendente"
    assert statuses[dup.id] == "Pendente"
