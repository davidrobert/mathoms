"""Testes de cone paths do Monte Carlo IF (Lane N3 PR-B) — caminho_p10/p50/p90."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.if_projector import (
    IFMonteCarloConfig,
    run_monte_carlo_if,
)


def _cfg_com_cone(pv: float = 800_000, fv: float = 2_000_000) -> IFMonteCarloConfig:
    """Config que garante exibir_cone=True (if_pct=40% > 15%)."""
    return IFMonteCarloConfig(
        patrimonio_investivel=Decimal(str(pv)),
        meta_if=Decimal(str(fv)),
        sigma_anual=0.11,
        retorno_real_esperado=0.05,
        n_simulacoes=5_000,
        horizonte_anos=40,
        seed=42,
    )


def _cfg_sem_cone() -> IFMonteCarloConfig:
    """Config que garante exibir_cone=False (if_pct=5% < 15%)."""
    return IFMonteCarloConfig(
        patrimonio_investivel=Decimal("100000"),
        meta_if=Decimal("2000000"),
        sigma_anual=0.11,
        retorno_real_esperado=0.05,
        n_simulacoes=2_000,
        horizonte_anos=40,
        seed=42,
    )


def test_caminho_paths_have_correct_shape():
    """Após run_monte_carlo_if com cone, len(caminho_p50) == config.horizonte_anos."""
    cfg = _cfg_com_cone()
    result = run_monte_carlo_if(cfg, ano_base=2026, idade_titular_atual=35)

    assert result.exibir_cone is True
    assert len(result.caminho_p50) == cfg.horizonte_anos
    assert len(result.caminho_p10) == cfg.horizonte_anos
    assert len(result.caminho_p90) == cfg.horizonte_anos


def test_caminho_paths_monotonically_plausible():
    """P90 patrimônio (percentil alto = otimista) >= P10 patrimônio (base = conservador) a cada ano."""
    cfg = _cfg_com_cone()
    result = run_monte_carlo_if(cfg, ano_base=2026, idade_titular_atual=35)

    assert result.exibir_cone is True
    for (ano_p10, v_p10), (ano_p90, v_p90) in zip(result.caminho_p10, result.caminho_p90):
        assert ano_p10 == ano_p90, "anos devem ser idênticos em p10 e p90"
        assert v_p90 >= v_p10, f"P90 deve ser >= P10 no ano {ano_p10}: {v_p90} vs {v_p10}"


def test_cone_paths_empty_when_not_exibir():
    """Quando gate suprime cone, paths são tuplas vazias."""
    cfg = _cfg_sem_cone()
    result = run_monte_carlo_if(cfg, ano_base=2026, idade_titular_atual=35)

    assert result.exibir_cone is False
    assert result.caminho_p10 == ()
    assert result.caminho_p50 == ()
    assert result.caminho_p90 == ()
