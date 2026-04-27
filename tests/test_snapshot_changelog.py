"""Goldens do ``SnapshotChangelogBuilder`` — 8 cenários + defesas (v2.D.1 · ADR-148)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

import pytest

from pipeline.domain.services.snapshot_changelog import (
    DEFAULT_SECTION_LABELS,
    build_comparison,
)
from pipeline.domain.types.snapshot_changelog import (
    AnalyzeFinancesSnapshot,
    SnapshotChangelogConfig,
    UnknownSectionError,
)


def _make_snapshot(
    *,
    workspace_id: str = "ws-test",
    period: str = "202604",
    content: Mapping[str, Any],
) -> AnalyzeFinancesSnapshot:
    """Fixture nomeado para snapshots — sem MagicMock (CLAUDE.md §Testes)."""
    return AnalyzeFinancesSnapshot(
        workspace_id=workspace_id,
        period_yyyymm=period,
        analysis_hash="hash-" + period,
        content_json=content,
        created_at=datetime(2026, int(period[4:6]), 15, tzinfo=timezone.utc),
    )


def _content(*, patrimonio_liquido: float = 0, receita: float = 0) -> dict[str, Any]:
    """Constrói `content_json` mínimo focado em S1 + S2."""
    return {
        "patrimonio": {"liquido": patrimonio_liquido, "bruto": 0},
        "fluxo_caixa": {"receita_total": receita, "despesa_total": 0, "investimentos_total": 0},
    }


def _full_content(scale: int) -> dict[str, Any]:
    """`content_json` cobrindo S1/S2/S3/T2/T5; `scale` multiplica todos os valores."""
    return {
        "patrimonio": {"liquido": 100 * scale, "bruto": 200 * scale},
        "fluxo_caixa": {
            "receita_total": 80 * scale,
            "despesa_total": 50 * scale,
            "investimentos_total": 20 * scale,
        },
    }


# ---------- Cenário 1: primeiro relatório ----------


def test_cenario_1_primeiro_relatorio_sem_prev():
    """`prev=None` → has_previous=False, items vazio, entries vazio."""
    curr = _make_snapshot(content=_content(patrimonio_liquido=1000, receita=8000))
    result = build_comparison(None, curr, SnapshotChangelogConfig())
    assert result.has_previous is False
    assert result.items == ()
    assert result.entries == ()


# ---------- Cenário 2: delta acima do threshold (5%) ----------


def test_cenario_2_delta_acima_threshold():
    """5% > 0,5% → 1 item up + 1 entry up para S1."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=1050))
    config = SnapshotChangelogConfig(sections_to_compare=("S1",))
    result = build_comparison(prev, curr, config)
    assert result.has_previous is True
    assert len(result.items) == 1
    item = result.items[0]
    assert item.section_id == "S1"
    assert item.before == Decimal("1000")
    assert item.after == Decimal("1050")
    assert item.delta_signal == "up"
    assert item.delta_pct == Decimal("5.00")
    assert len(result.entries) == 1
    assert result.entries[0].section_id == "S1"
    assert "cresceu" in result.entries[0].summary
    assert "5,0%" in result.entries[0].summary


# ---------- Cenário 3: delta abaixo do threshold ----------


def test_cenario_3_delta_abaixo_threshold():
    """0,3% < 0,5% → 1 item stable, 0 entries."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=1003))
    config = SnapshotChangelogConfig(sections_to_compare=("S1",))
    result = build_comparison(prev, curr, config)
    assert len(result.items) == 1
    assert result.items[0].delta_signal == "stable"
    assert result.entries == ()


# ---------- Cenário 4: delta negativo ----------


def test_cenario_4_delta_negativo():
    """-3% → 1 item down + 1 entry down."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=970))
    config = SnapshotChangelogConfig(sections_to_compare=("S1",))
    result = build_comparison(prev, curr, config)
    assert result.items[0].delta_signal == "down"
    assert result.items[0].delta_pct == Decimal("-3")
    assert "caiu" in result.entries[0].summary
    assert "3,0%" in result.entries[0].summary


# ---------- Cenário 5: override por seção (thresholds=) ----------


def test_cenario_5_override_threshold_por_secao():
    """`thresholds={"S1": Decimal("1")}` → 0,8% fica abaixo do override."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=1008))
    config = SnapshotChangelogConfig(
        sections_to_compare=("S1",),
        thresholds={"S1": Decimal("1")},
    )
    result = build_comparison(prev, curr, config)
    assert result.items[0].delta_signal == "stable"
    assert result.entries == ()
    # Sem override, default 0,5% → seria up
    config_default = SnapshotChangelogConfig(sections_to_compare=("S1",))
    result_default = build_comparison(prev, curr, config_default)
    assert result_default.items[0].delta_signal == "up"


# ---------- Cenário 6: before=0, after>0 → from_zero ----------


def test_cenario_6_from_zero():
    """`before=0, after=2500` → up, delta_pct=None, narrativa from_zero."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=0))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=2500))
    config = SnapshotChangelogConfig(sections_to_compare=("S1",))
    result = build_comparison(prev, curr, config)
    item = result.items[0]
    assert item.delta_signal == "up"
    assert item.delta_pct is None
    entry = result.entries[0]
    assert "passou a registrar valor" in entry.summary
    assert "antes zero" in entry.summary
    assert "R$ 2.500,00" in entry.summary


# ---------- Cenário 7: before>0, after=0 → to_zero ----------


def test_cenario_7_to_zero():
    """`before=1000, after=0` → down, delta_pct=None, narrativa to_zero."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=0))
    config = SnapshotChangelogConfig(sections_to_compare=("S1",))
    result = build_comparison(prev, curr, config)
    item = result.items[0]
    assert item.delta_signal == "down"
    assert item.delta_pct is None
    assert "zerou desde o relatório anterior" in result.entries[0].summary


# ---------- Cenário 8: both zero → stable, delta_pct=0 ----------


def test_cenario_8_both_zero():
    """`before=0, after=0` → stable, delta_pct=0, sem entry (filtrado por threshold)."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=0))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=0))
    config = SnapshotChangelogConfig(sections_to_compare=("S1",))
    result = build_comparison(prev, curr, config)
    item = result.items[0]
    assert item.delta_signal == "stable"
    assert item.delta_pct == Decimal("0")
    assert result.entries == ()


# ---------- Defesa: section_id desconhecido ----------


def test_unknown_section_id_levanta_erro():
    """Fail-fast: section_id sem path em DEFAULT_SECTION_VALUE_PATHS."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=1050))
    config = SnapshotChangelogConfig(sections_to_compare=("S99",))
    with pytest.raises(UnknownSectionError, match="S99"):
        build_comparison(prev, curr, config)


# ---------- Default sections + labels ----------


def test_default_sections_compare_5_secoes():
    """Default `sections_to_compare` = S1/S2/S3/T2/T5; labels resolvidos pelo default."""
    prev = _make_snapshot(period="202603", content=_full_content(scale=1))
    curr = _make_snapshot(period="202604", content=_full_content(scale=2))
    result = build_comparison(prev, curr, SnapshotChangelogConfig())
    section_ids = [item.section_id for item in result.items]
    assert section_ids == ["S1", "S2", "S3", "T2", "T5"]
    labels = {item.section_id: item.section_label for item in result.items}
    for sid in ("S1", "S2", "S3", "T2", "T5"):
        assert labels[sid] == DEFAULT_SECTION_LABELS[sid]


def test_label_override_via_config():
    """`section_labels={"S1": "Patrimônio"}` sobrescreve default."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=1050))
    config = SnapshotChangelogConfig(
        sections_to_compare=("S1",),
        section_labels={"S1": "Riqueza Líquida"},
    )
    result = build_comparison(prev, curr, config)
    assert result.items[0].section_label == "Riqueza Líquida"
    assert "Riqueza Líquida" in result.entries[0].summary
