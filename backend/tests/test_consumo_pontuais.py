"""Tests for ``GET /reports/consumo-pontuais`` (defesa contra falha do E4)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

from backend.app.application.report.consumo_pontuais import _resolve_period_dates
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus


def test_resolve_period_dates_3m():
    today = datetime(2026, 4, 25, tzinfo=timezone.utc).date()
    date_from, date_to = _resolve_period_dates("3m", today=today)
    assert date_to == "2026-04-25"
    assert date_from < date_to


def test_resolve_period_dates_ytd():
    today = datetime(2026, 4, 25, tzinfo=timezone.utc).date()
    date_from, date_to = _resolve_period_dates("ytd", today=today)
    assert date_from == "2026-01-01"
    assert date_to == "2026-04-25"


def test_resolve_period_dates_invalid_raises():
    with pytest.raises(ValueError):
        _resolve_period_dates("1y")


def test_resolve_period_dates_anchor_overrides_today():
    """anchor_date ancora date_to no fim do dataset (paridade PR #150)."""
    today = datetime(2026, 5, 9, tzinfo=timezone.utc).date()
    anchor = datetime(2025, 11, 30, tzinfo=timezone.utc).date()
    date_from, date_to = _resolve_period_dates("3m", today=today, anchor_date=anchor)
    assert date_to == "2025-11-30"
    assert date_from < date_to
    assert date_from.startswith("2025-")


def _despesa(
    descricao: str,
    qtd,
    *,
    categoria: str = "nao_identificado",
    data: str | None = None,
) -> dict:
    return {
        "data": data or datetime.now(timezone.utc).date().isoformat(),
        "descricao": descricao,
        "valor": qtd,
        "banco": "itau",
        "categoria": categoria,
    }


async def _seed_e4_despesas(db, workspace_id: str, despesas: list[dict]) -> None:
    """Seed E4 ``despesas`` artifact via ``db`` fixture (pytest-asyncio strict)."""
    run = PipelineRun(
        id=str(uuid4()), workspace_id=workspace_id, status=PipelineRunStatus.completed
    )
    db.add(run)
    await db.flush()
    payload_despesas = {"dados": {"nao_identificado": despesas}}
    db.add(_make_artifact(workspace_id, run.id, "despesas", payload_despesas))
    db.add(_make_artifact(workspace_id, run.id, "receitas", {"dados": {}}))
    await db.commit()


def _make_artifact(workspace_id: str, run_id: str, key: str, content: dict) -> PipelineArtifact:
    return PipelineArtifact(
        workspace_id=workspace_id,
        pipeline_run_id=run_id,
        stage="categorize_transactions",
        artifact_key=key,
        content_json=content,
    )


async def _seed_transfer_config(db, workspace_id: str) -> None:
    """Persist ``TransferConfig`` blob — pos-A7.5 substitui o fallback de disco (ADR-134)."""
    from backend.app.models.config_blob import TransferConfig

    db.add(
        TransferConfig(
            workspace_id=workspace_id,
            config_json={
                "patterns_pix": [],
                "patterns_global": [],
                "patterns_bank_specific": {},
                "recipients": ["DAVID ROBERT MARTINS", "MARIANA RIBEIRO ANDRADE"],
            },
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_consumo_pontuais_excludes_internal_transfers_to_family(auth_client: AsyncClient, db):
    """Bug fix: PIX para nome da família não pode aparecer como gasto pontual."""
    despesas = [
        _despesa(
            "Pix enviado para DAVID ROBERT MARTINS ANDRADE SILVA — TRANSF ENVIADA PIX C", 41000.0
        ),
        _despesa("RESTAURANTE FASANO", 5000.0),
    ]
    await _seed_e4_despesas(db, auth_client.ws_id, despesas)
    await _seed_transfer_config(db, auth_client.ws_id)

    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/consumo-pontuais?period=3m"
    )
    assert resp.status_code == 200, resp.text
    descricoes = [it["descricao"] for it in resp.json()["items"]]
    assert any("FASANO" in d for d in descricoes)
    assert not any("DAVID ROBERT" in d for d in descricoes)


@pytest.mark.asyncio
async def test_consumo_pontuais_filters_below_threshold(auth_client: AsyncClient, db):
    despesas = [
        _despesa("PEQUENA COMPRA", 500.0, categoria="alimentacao"),
        _despesa("GRANDE COMPRA", 3500.0, categoria="alimentacao"),
    ]
    await _seed_e4_despesas(db, auth_client.ws_id, despesas)
    await _seed_transfer_config(db, auth_client.ws_id)

    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/consumo-pontuais?period=3m"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["descricao"] == "GRANDE COMPRA"


async def _seed_old_despesa(auth_client, db) -> None:
    despesas = [_despesa("GASTO ANTIGO GRANDE", 5000.0, categoria="alimentacao", data="2025-11-15")]
    await _seed_e4_despesas(db, auth_client.ws_id, despesas)
    await _seed_transfer_config(db, auth_client.ws_id)


@pytest.mark.asyncio
async def test_consumo_pontuais_old_dataset_returns_empty_without_anchor(
    auth_client: AsyncClient, db
):
    """Sem ``anchor_date``, dados de 2025-11 caem fora da janela 3m ancorada em hoje."""
    await _seed_old_despesa(auth_client, db)
    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/consumo-pontuais?period=3m"
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_consumo_pontuais_anchor_date_unblocks_old_dataset(auth_client: AsyncClient, db):
    """Com ``anchor_date=2025-11-30`` a janela passa a cobrir o dataset (paridade PR #150)."""
    await _seed_old_despesa(auth_client, db)
    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/consumo-pontuais"
        "?period=3m&anchor_date=2025-11-30"
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 1
    assert data["date_to"] == "2025-11-30"
    assert data["items"][0]["descricao"] == "GASTO ANTIGO GRANDE"


@pytest.mark.asyncio
async def test_consumo_pontuais_invalid_period(auth_client: AsyncClient):
    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/consumo-pontuais?period=1y"
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_consumo_pontuais_unauthorized(client: AsyncClient):
    resp = await client.get(
        "/api/workspaces/00000000-0000-0000-0000-000000000000/reports/consumo-pontuais?period=3m"
    )
    assert resp.status_code in (401, 403)


# A40.l98 — o limiar era DOIS literais: este endpoint caía num
# ``Decimal("2000")`` próprio e o KPI do MESMO card lia
# ``scoring.json::thresholds_alertas.consumo_consciente_min``. Ambos valiam 2000 e
# **coincidiam por acaso** — editar o scoring os separava em silêncio, e nenhum
# teste falhava. Teste de IGUALDADE aqui seria vazio (2000 == 2000 continua
# verdade com os dois literais de volta): o gate move o scoring para 2500 e exige
# que as DUAS superfícies se movam.
_SCORING_2500 = {"thresholds_alertas": {"consumo_consciente_min": 2500}}
_E4_PAR_DE_LIMIAR = {
    "dados": {
        "alimentacao": [
            {"data": "2026-01-05", "descricao": "ENTRE OS DOIS LIMIARES", "valor": 2200.0},
            {"data": "2026-01-06", "descricao": "ACIMA DOS DOIS", "valor": 3500.0},
        ]
    }
}


def _escreve_scoring(tmp_path, monkeypatch, scoring: dict) -> None:
    from backend.app.core.config import settings

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "scoring.json").write_text(json.dumps(scoring), encoding="utf-8")
    monkeypatch.setattr(settings, "PIPELINE_ROOT", tmp_path)


async def _semeia_par_de_limiar(auth_client: AsyncClient, db) -> str:
    await _seed_e4_despesas(
        db,
        auth_client.ws_id,
        [
            _despesa("ENTRE OS DOIS LIMIARES", 2200.0, categoria="alimentacao"),
            _despesa("ACIMA DOS DOIS", 3500.0, categoria="alimentacao"),
        ],
    )
    await _seed_transfer_config(db, auth_client.ws_id)
    return f"/api/workspaces/{auth_client.ws_id}/reports/consumo-pontuais?period=3m"


@pytest.mark.asyncio
async def test_limiar_do_scoring_move_a_lista(auth_client: AsyncClient, db, tmp_path, monkeypatch):
    url = await _semeia_par_de_limiar(auth_client, db)
    antes = await auth_client.get(url)
    assert [it["descricao"] for it in antes.json()["items"]] == [
        "ACIMA DOS DOIS",
        "ENTRE OS DOIS LIMIARES",
    ], "sem o limiar de 2000 vigente, o contrafactual abaixo não discrimina nada"

    _escreve_scoring(tmp_path, monkeypatch, _SCORING_2500)
    depois = await auth_client.get(url)
    assert [it["descricao"] for it in depois.json()["items"]] == [
        "ACIMA DOS DOIS"
    ], "editar `scoring.json` não moveu a LISTA — o endpoint voltou a usar limiar próprio"


def test_limiar_do_scoring_move_o_kpi():
    """A outra metade do par: mesma edição, mesmo item, superfície do KPI."""
    from pipeline.domain.services.consumo_consciente_calculator import (
        ConsumoConscienteCalculator,
    )
    from pipeline.domain.services.gasto_pontual_policy import GastoPontualPolicy

    despesas = _E4_PAR_DE_LIMIAR
    fluxo = {"janela_12m": {"receita_recorrente_mensal": 20_000, "n_meses": 12}}

    def descricoes(scoring: dict | None) -> list[str]:
        calc = ConsumoConscienteCalculator(GastoPontualPolicy.from_scoring(scoring))
        return [i.descricao for i in calc.calculate(fluxo, despesas).itens]

    assert descricoes(None) == ["ACIMA DOS DOIS", "ENTRE OS DOIS LIMIARES"]
    assert descricoes(_SCORING_2500) == ["ACIMA DOS DOIS"]


# A40.l98 PR2 — a lista aplicava DUAS das três cláusulas de natureza. Faltavam
# `recorrentes` (o aluguel de R$ 5k entrava 12× como "gasto pontual") e
# `transferencia_patrimonial` (o aporte é poupança, [[ADR-333]]).
@pytest.mark.asyncio
async def test_lista_exclui_recorrente_e_aporte(auth_client: AsyncClient, db):
    despesas = [
        _despesa("ALUGUEL APARTAMENTO", 5000.0, categoria="moradia"),
        _despesa("APORTE CDB TESOURO", 12000.0, categoria="aporte_investimento"),
        _despesa("PIX FAMILIA MENSALIDADE", 4000.0, categoria="transferencia_familiar"),
        _despesa("RESTAURANTE FASANO", 3500.0, categoria="alimentacao"),
    ]
    await _seed_e4_despesas(db, auth_client.ws_id, despesas)
    await _seed_transfer_config(db, auth_client.ws_id)

    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/consumo-pontuais?period=3m"
    )
    assert resp.status_code == 200, resp.text
    assert [it["descricao"] for it in resp.json()["items"]] == ["RESTAURANTE FASANO"]


# A40.l98 PR3b ([[ADR-425]] §D1) — divergência DELIBERADA entre as duas
# superfícies do card: `nao_identificado` sai do KPI (é ausência de medição, e o
# parecer ancora conselho nele) e FICA na lista, que é o inventário — é aqui que
# a família vê as linhas que só ela pode classificar. Tirá-lo dos dois lados
# esconderia justamente o que precisa de ação.
@pytest.mark.asyncio
async def test_nao_identificado_fica_no_inventario(auth_client: AsyncClient, db):
    despesas = [
        _despesa("DEBITO NAO RECONHECIDO 8842", 7000.0, categoria="nao_identificado"),
        _despesa("APORTE CDB TESOURO", 12000.0, categoria="aporte_investimento"),
    ]
    await _seed_e4_despesas(db, auth_client.ws_id, despesas)
    await _seed_transfer_config(db, auth_client.ws_id)

    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/consumo-pontuais?period=3m"
    )
    assert resp.status_code == 200, resp.text
    assert [it["descricao"] for it in resp.json()["items"]] == ["DEBITO NAO RECONHECIDO 8842"]
