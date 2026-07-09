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
from pipeline.domain.services.snapshot_changelog.narratives import SECTION_POLARITY
from pipeline.domain.types.snapshot_changelog import (
    DEFAULT_DIRECTION_POSITIVE,
    AnalyzeFinancesSnapshot,
    SnapshotChangelogConfig,
    ThresholdRule,
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
    """5% > 0,5% → 1 item up + 1 entry up para S1 (verb asset = 'cresceu')."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=1050))
    config = SnapshotChangelogConfig(sections_to_compare=("S1",))
    result = build_comparison(prev, curr, config)
    assert result.has_previous is True
    item = result.items[0]
    assert (item.section_id, item.before, item.after) == ("S1", Decimal("1000"), Decimal("1050"))
    assert item.delta_signal == "up"
    assert item.delta_pct == Decimal("5.00")
    summary = result.entries[0].summary
    assert summary.startswith("Patrimônio líquido cresceu ")
    assert "R$ 50,00" in summary
    assert "desde o relatório anterior" in summary
    assert "(+5,0%)" in summary


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
    """-3% → 1 item down + 1 entry down (delta_brl com sinal U+2212 'minus sign')."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=970))
    config = SnapshotChangelogConfig(sections_to_compare=("S1",))
    result = build_comparison(prev, curr, config)
    assert result.items[0].delta_signal == "down"
    assert result.items[0].delta_pct == Decimal("-3")
    summary = result.entries[0].summary
    assert summary.startswith("Patrimônio líquido recuou ")
    # delta_brl em valor absoluto (verbo carrega direção); sinal só no pct.
    assert "R$ 30,00" in summary
    assert "R$ −30,00" not in summary
    assert "desde o relatório anterior" in summary
    assert "(−3,0%)" in summary


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
    assert "passou a registrar" in entry.summary
    assert "antes sem valor" in entry.summary
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
    assert "zerou neste relatório" in result.entries[0].summary


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


# ---------- Cenário 9: polaridade expense (T5) usa "subiu", não "avançou" ----------


def test_cenario_9_expense_polarity_t5_usa_subiu():
    """T5 (despesas) com delta up usa verbo neutro "subiu" — trava regressão de viés."""
    prev = _make_snapshot(
        period="202603",
        content={
            "patrimonio": {"liquido": 0, "bruto": 0},
            "fluxo_caixa": {
                "receita_total": 0,
                "despesa_total": 1000,
                "investimentos_total": 0,
            },
        },
    )
    curr = _make_snapshot(
        period="202604",
        content={
            "patrimonio": {"liquido": 0, "bruto": 0},
            "fluxo_caixa": {
                "receita_total": 0,
                "despesa_total": 1100,
                "investimentos_total": 0,
            },
        },
    )
    config = SnapshotChangelogConfig(
        sections_to_compare=("T5",),
        section_labels={"T5": "Despesas Totais"},
    )
    result = build_comparison(prev, curr, config)
    assert result.items[0].section_id == "T5"
    assert result.items[0].delta_signal == "up"
    assert result.items[0].delta_pct == Decimal("10.00")
    summary = result.entries[0].summary
    # Despesas Totais é plural → "subiram", não "subiu"; despesa não usa "cresceram".
    assert summary.startswith("Despesas totais subiram ")
    assert "cresceram" not in summary
    assert "avançaram" not in summary
    assert "R$ 100,00" in summary
    assert "(+10,0%)" in summary


# ---------- Defesa: section_id desconhecido ----------


def test_unknown_section_id_levanta_erro():
    """Fail-fast: section_id sem path em DEFAULT_SECTION_VALUE_PATHS."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=1050))
    config = SnapshotChangelogConfig(sections_to_compare=("S99",))
    with pytest.raises(UnknownSectionError, match="S99"):
        build_comparison(prev, curr, config)


# ---------- Default sections + labels ----------


def test_legacy_sections_seguem_validas_via_override():
    """Retrocompat D1: ids legados funcionam com `sections_to_compare` explícito."""
    prev = _make_snapshot(period="202603", content=_full_content(scale=1))
    curr = _make_snapshot(period="202604", content=_full_content(scale=2))
    config = SnapshotChangelogConfig(sections_to_compare=("S1", "S2", "S3", "T2", "T5"))
    result = build_comparison(prev, curr, config)
    section_ids = [item.section_id for item in result.items]
    assert section_ids == ["S1", "S2", "S3", "T2", "T5"]
    assert all(item.unit == "brl" for item in result.items)


def test_label_override_via_config():
    """`section_labels={"S1": "Riqueza Líquida"}` sobrescreve default; prosa em sentence case."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=1050))
    config = SnapshotChangelogConfig(
        sections_to_compare=("S1",),
        section_labels={"S1": "Riqueza Líquida"},
    )
    result = build_comparison(prev, curr, config)
    # Card preserva Title Case do override; prosa do callout aplica sentence case.
    assert result.items[0].section_label == "Riqueza Líquida"
    assert result.entries[0].summary.startswith("Riqueza líquida cresceu ")


# ---------- Regressões de copy (2026-05-09) ----------


def test_summary_nao_usa_no_mes_ambiguo():
    """Trava regressão da ancoragem temporal: prosa nunca usa `'no mês'` solto."""
    prev = _make_snapshot(period="202603", content=_full_content(scale=1))
    curr = _make_snapshot(period="202604", content=_full_content(scale=2))
    result = build_comparison(prev, curr, SnapshotChangelogConfig())
    for entry in result.entries:
        assert " no mês" not in entry.summary, (
            f"section={entry.section_id} summary={entry.summary!r} "
            "ambiguo — usar 'desde o relatório anterior'"
        )
        assert "desde o relatório anterior" in entry.summary or "neste relatório" in entry.summary


def _aportes_only(invest: float) -> dict[str, Any]:
    """`content_json` cobrindo só T2 (aportes), demais 0."""
    return {
        "patrimonio": {"liquido": 0, "bruto": 0},
        "fluxo_caixa": {"receita_total": 0, "despesa_total": 0, "investimentos_total": invest},
    }


def test_summary_label_unica_palavra_plural_concorda_verbo():
    """`'Aportes'` (single-token plural) → verbo plural (`'cresceram'`)."""
    prev = _make_snapshot(period="202603", content=_aportes_only(1000))
    curr = _make_snapshot(period="202604", content=_aportes_only(1500))
    result = build_comparison(prev, curr, SnapshotChangelogConfig(sections_to_compare=("T2",)))
    summary = result.entries[0].summary
    assert summary.startswith("Aportes cresceram ")
    assert "cresceu" not in summary


def test_summary_to_zero_plural_usa_zeraram():
    """Label plural em to_zero → `'zeraram'`, não `'zerou'`."""
    prev = _make_snapshot(period="202603", content=_aportes_only(1000))
    curr = _make_snapshot(period="202604", content=_aportes_only(0))
    result = build_comparison(prev, curr, SnapshotChangelogConfig(sections_to_compare=("T2",)))
    assert result.entries[0].summary == "Aportes zeraram neste relatório"


# ---------- W2 (ADR-190 D3): direção semântica por seção ----------


def _despesas_only(despesa: float) -> dict[str, Any]:
    """`content_json` cobrindo só T5 (despesas), demais 0."""
    return {
        "patrimonio": {"liquido": 0, "bruto": 0},
        "fluxo_caixa": {"receita_total": 0, "despesa_total": despesa, "investimentos_total": 0},
    }


def test_w2_t5_expense_carrega_direction_positive_down():
    """T5 subindo mantém delta_signal=up, mas direction_positive=down (UI pinta vermelho)."""
    prev = _make_snapshot(period="202603", content=_despesas_only(1000))
    curr = _make_snapshot(period="202604", content=_despesas_only(1100))
    result = build_comparison(prev, curr, SnapshotChangelogConfig(sections_to_compare=("T5",)))
    item = result.items[0]
    assert item.delta_signal == "up"
    assert item.direction_positive == "down"


def test_w2_asset_carrega_direction_positive_up():
    """S1 (asset) carrega direction_positive=up — up continua favorável."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=1050))
    result = build_comparison(prev, curr, SnapshotChangelogConfig(sections_to_compare=("S1",)))
    assert result.items[0].direction_positive == "up"


def test_w2_direction_positive_override_via_config():
    """Override explícito em config vence o default D3."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=1050))
    config = SnapshotChangelogConfig(
        sections_to_compare=("S1",),
        direction_positive={"S1": "down"},
    )
    result = build_comparison(prev, curr, config)
    assert result.items[0].direction_positive == "down"


def test_w2_default_direction_consistente_com_section_polarity():
    """Trava consistência D3: asset↔up, expense↔down entre os dois mapas."""
    assert set(DEFAULT_DIRECTION_POSITIVE) == set(SECTION_POLARITY)
    for section_id, polarity in SECTION_POLARITY.items():
        expected = "up" if polarity == "asset" else "down"
        assert DEFAULT_DIRECTION_POSITIVE[section_id] == expected, (
            f"section={section_id}: polarity={polarity!r} exige "
            f"direction_positive={expected!r}, got {DEFAULT_DIRECTION_POSITIVE[section_id]!r}"
        )


# ---------- W2 (ADR-190 D4): threshold dual pct + R$ absoluto ----------


def test_w2_dual_threshold_ambos_abaixo_e_stable():
    """Critério W2: stable somente se pct E abs ficam abaixo dos limites."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1_000_000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=1_010_000))
    config = SnapshotChangelogConfig(
        sections_to_compare=("S1",),
        thresholds={"S1": ThresholdRule(pct=Decimal("2"), abs_brl=Decimal("20000"))},
    )
    # Δ = 1% (< 2%) e R$ 10k (< 20k) → ambos abaixo → stable.
    result = build_comparison(prev, curr, config)
    assert result.items[0].delta_signal == "stable"


def test_w2_dual_threshold_abs_cruzado_sinaliza_mesmo_com_pct_abaixo():
    """Portfólio grande: 1% de PL pode ser R$ 100k — abs cruza, sinaliza."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=10_000_000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=10_100_000))
    config = SnapshotChangelogConfig(
        sections_to_compare=("S1",),
        thresholds={"S1": ThresholdRule(pct=Decimal("2"), abs_brl=Decimal("20000"))},
    )
    # Δ = 1% (< 2%) mas R$ 100k (>= 20k) → up.
    result = build_comparison(prev, curr, config)
    assert result.items[0].delta_signal == "up"


def test_w2_dual_threshold_boundary_exato_sinaliza():
    """Boundary: Δ exatamente no limite (>=) cruza — não é stable."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=1020))
    config = SnapshotChangelogConfig(
        sections_to_compare=("S1",),
        thresholds={"S1": ThresholdRule(pct=Decimal("2"))},
    )
    # Δ = 2.00% == limite → cruza (mantém semântica pré-W2 de `<` para stable).
    result = build_comparison(prev, curr, config)
    assert result.items[0].delta_signal == "up"


def test_w2_threshold_decimal_legado_segue_valendo():
    """Override `Decimal` puro (pré-W2) vira regra pct-only — compat preservada."""
    prev = _make_snapshot(period="202603", content=_content(patrimonio_liquido=1000))
    curr = _make_snapshot(period="202604", content=_content(patrimonio_liquido=1008))
    config = SnapshotChangelogConfig(
        sections_to_compare=("S1",),
        thresholds={"S1": Decimal("1")},
    )
    result = build_comparison(prev, curr, config)
    assert result.items[0].delta_signal == "stable"


def test_w2_threshold_rule_sem_limite_falha_cedo():
    """ThresholdRule() sem pct nem abs_brl → ValueError no boundary (ADR-097)."""
    with pytest.raises(ValueError, match="pct e/ou abs_brl"):
        ThresholdRule()
