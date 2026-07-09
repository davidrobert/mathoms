"""Métricas canônicas v3 do ``SnapshotChangelogBuilder`` (ADR-190 §Emenda 2026-07-09)."""

from __future__ import annotations

from typing import Any

from pipeline.domain.services.snapshot_changelog import (
    DEFAULT_SECTION_LABELS,
    build_comparison,
)
from pipeline.domain.types.snapshot_changelog import SnapshotChangelogConfig
from tests.test_snapshot_changelog import _make_snapshot


def _canonical_content(scale: int) -> dict[str, Any]:
    """`content_json` cobrindo as 4 métricas canônicas v3 (campos E5 reais)."""
    return {
        "patrimonio": {"liquido": 100000 * scale, "bruto": 200000 * scale},
        "ratios": {"taxa_poupanca_recorrente_pct": 10.0 * scale},
        "reserva": {"cobertura_meses": 6.0 * scale},
        "goals": {"alocacao_alvo": {"derived": {"desvio_max_pct": 4.0 * scale}}},
    }


def test_default_sections_sao_metricas_canonicas_v3():
    """Default v3 (ADR-190 §Emenda 2026-07-09): 4 métricas canônicas sobre
    campos E5 reais; métrica com fonte ausente é suprimida individualmente."""
    prev = _make_snapshot(period="202603", content=_canonical_content(scale=1))
    curr = _make_snapshot(period="202604", content=_canonical_content(scale=2))
    result = build_comparison(prev, curr, SnapshotChangelogConfig())
    section_ids = [item.section_id for item in result.items]
    assert section_ids == ["M_PL", "M_TAXA_POUPANCA", "M_RESERVA_MESES", "M_AUVP_DESVIO"]
    units = {item.section_id: item.unit for item in result.items}
    assert units == {
        "M_PL": "brl",
        "M_TAXA_POUPANCA": "pp",
        "M_RESERVA_MESES": "meses",
        "M_AUVP_DESVIO": "pp",
    }
    labels = {item.section_id: item.section_label for item in result.items}
    for sid in section_ids:
        assert labels[sid] == DEFAULT_SECTION_LABELS[sid]


def test_metrica_sem_fonte_e_suprimida_individualmente():
    """M_* com path ausente em qualquer lado some da lista — nunca zero falso."""
    content_sem_desvio = _canonical_content(scale=1)
    del content_sem_desvio["goals"]
    prev = _make_snapshot(period="202603", content=content_sem_desvio)
    curr = _make_snapshot(period="202604", content=_canonical_content(scale=2))
    result = build_comparison(prev, curr, SnapshotChangelogConfig())
    section_ids = [item.section_id for item in result.items]
    assert "M_AUVP_DESVIO" not in section_ids
    assert section_ids == ["M_PL", "M_TAXA_POUPANCA", "M_RESERVA_MESES"]


def _poupanca_signal_for_delta(delta_pp: float) -> str:
    base = _canonical_content(scale=1)
    curr = _canonical_content(scale=1)
    curr["ratios"]["taxa_poupanca_recorrente_pct"] += delta_pp
    prev = _make_snapshot(period="202603", content=base)
    result = build_comparison(
        prev, _make_snapshot(period="202604", content=curr), SnapshotChangelogConfig()
    )
    return {i.section_id: i for i in result.items}["M_TAXA_POUPANCA"].delta_signal


def test_threshold_default_por_metrica_pp():
    """Threshold absoluto na unidade da métrica: poupança Δ2,9pp = stable; Δ3pp sinaliza."""
    assert _poupanca_signal_for_delta(2.9) == "stable"
    assert _poupanca_signal_for_delta(3.0) == "up"
