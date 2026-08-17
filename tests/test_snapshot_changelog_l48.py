"""A40.l48 — polaridade da reserva deriva do alvo, não da constante."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pipeline.domain.services.snapshot_changelog import build_comparison
from pipeline.domain.types.snapshot_changelog import (
    DEFAULT_DIRECTION_POSITIVE,
    AnalyzeFinancesSnapshot,
    SnapshotChangelogConfig,
)

_CFG = SnapshotChangelogConfig(sections_to_compare=("M_RESERVA_MESES",))


def _snap(period: str, content: dict[str, Any]) -> AnalyzeFinancesSnapshot:
    return AnalyzeFinancesSnapshot(
        workspace_id="ws-test",
        period_yyyymm=period,
        analysis_hash="hash-" + period,
        content_json=content,
        created_at=datetime(2026, int(period[4:6]), 15, tzinfo=timezone.utc),
    )


def _reserva(meses: float, alvo: int | None = 6) -> dict[str, Any]:
    bloco: dict[str, Any] = {"cobertura_meses": meses}
    if alvo is not None:
        bloco["meses_alvo"] = alvo
    return {
        "patrimonio": {"liquido": 0, "bruto": 0},
        "fluxo_caixa": {"receita_total": 0, "despesa_total": 0, "investimentos_total": 0},
        "reserva_emergencia": bloco,
    }


def _item(before: float, after: float, alvo: int | None = 6):
    prev = _snap("202603", _reserva(before, alvo))
    curr = _snap("202604", _reserva(after, alvo))
    return build_comparison(prev, curr, _CFG).items[0]


def test_reserva_abaixo_do_alvo_subir_e_positivo():
    item = _item(3.0, 5.0, alvo=6)
    assert item.delta_signal == "up"
    assert item.direction_positive == "up"


def test_reserva_acima_do_alvo_subir_e_negativo():
    item = _item(8.0, 12.0, alvo=6)
    assert item.delta_signal == "up"
    assert item.direction_positive == "down"


def test_reserva_cruza_alvo_para_cima_inverte_polaridade():
    assert _item(4.0, 10.0, alvo=6).direction_positive == "down"


def test_reserva_cruza_alvo_para_baixo_inverte_polaridade():
    item = _item(10.0, 4.0, alvo=6)
    assert item.delta_signal == "down"
    assert item.direction_positive == "up"


def test_reserva_sem_alvo_cai_no_default_monotonico():
    assert _item(8.0, 12.0, alvo=None).direction_positive == "up"


def test_mutacao_polaridade_constante_acima_do_alvo_falha():
    """Voltar a DEFAULT_DIRECTION_POSITIVE sem olhar o alvo deixa este teste vermelho."""
    assert (
        _item(8.0, 12.0, alvo=6).direction_positive != DEFAULT_DIRECTION_POSITIVE["M_RESERVA_MESES"]
    )


def test_l48_nao_muda_polaridade_de_metricas_monotonicas():
    prev = _snap("202603", {"patrimonio": {"liquido": 1000, "bruto": 0}})
    curr = _snap("202604", {"patrimonio": {"liquido": 1050, "bruto": 0}})
    cfg = SnapshotChangelogConfig(sections_to_compare=("S1",))
    assert build_comparison(prev, curr, cfg).items[0].direction_positive == "up"
