"""S2 do watchdog de agendados — cabeça obsoleta do índice não acusa cron vivo (ADR-210)."""

from __future__ import annotations

from datetime import date

import pytest

from dev import check_scheduled_workflows as mod

REF = date(2026, 8, 21)
ENTRY = {"file": "auto-update-prs.yml", "max_age_days": 2}


def _pagina(*instantes: str) -> dict:
    return {"workflow_runs": [{"run_started_at": t} for t in instantes]}


# Forma medida em 2026-08-21: a réplica serve um run antigo na POSIÇÃO 0 e as
# linhas seguintes frescas — 2 leituras sujas em 130 com per_page=1, 0 em 60
# com per_page=10 + max.
CABECA_OBSOLETA = _pagina("2026-08-06T15:59:52Z", "2026-08-21T14:28:33Z", "2026-08-21T14:01:28Z")
TUDO_VELHO = _pagina("2026-08-06T15:59:52Z", "2026-08-05T14:00:00Z")


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch):
    def instalar(resposta: dict | None):
        chamadas: list[list[str]] = []

        def _fake(args: list[str]) -> dict | None:
            chamadas.append(args)
            return resposta

        monkeypatch.setattr(mod, "_gh_json", _fake)
        return chamadas

    return instalar


def test_cabeca_obsoleta_nao_acusa_cron_vivo(api) -> None:
    """O run fresco está na página; tomar o max impede que a cabeça velha vença."""
    api(CABECA_OBSOLETA)
    assert mod._check_liveness("o/r", ENTRY, REF) == []


def test_pede_pagina_e_nao_apenas_o_primeiro(api) -> None:
    """Sem `per_page` > 1 não há linha fresca para o max escolher."""
    chamadas = api(CABECA_OBSOLETA)
    mod._check_liveness("o/r", ENTRY, REF)
    (args,) = chamadas
    assert "per_page=10" in args[-1]
    assert "event=schedule" in args[-1]


def test_cron_realmente_parado_ainda_acusa(api) -> None:
    """Página inteira velha: o sinal continua reprovando — o fix não é anistia."""
    api(TUDO_VELHO)
    (violacao,) = mod._check_liveness("o/r", ENTRY, REF)
    assert violacao.signal == "S2"
    assert "14d" in violacao.detail


def test_nunca_rodou_por_schedule_ainda_acusa(api) -> None:
    api({"workflow_runs": []})
    (violacao,) = mod._check_liveness("o/r", ENTRY, REF)
    assert violacao.signal == "S2"
    assert "nunca rodou" in violacao.detail


def test_api_muda_degrada_para_sinal_proprio(api) -> None:
    """`gh` mudo não vira S2 — tem canal próprio, senão o falso vermelho volta."""
    api(None)
    assert [v.signal for v in mod._check_liveness("o/r", ENTRY, REF)] in ([], ["GH"])
