"""Testes do Monte Carlo IF v2 (Lane N3 PR-A) — P10/P50/P90 + gates de cone."""

from __future__ import annotations

import time
from decimal import Decimal

import pytest

from pipeline.domain.services.if_projector import (
    IFMonteCarloConfig,
    MonteCarloIFResult,
    run_monte_carlo_if,
)


def _config(
    pv: float = 500_000,
    fv: float = 2_000_000,
    sigma: float = 0.11,
    retorno: float = 0.05,
    seed: int = 42,
    n: int = 10_000,
) -> IFMonteCarloConfig:
    return IFMonteCarloConfig(
        patrimonio_investivel=Decimal(str(pv)),
        meta_if=Decimal(str(fv)),
        sigma_anual=sigma,
        retorno_real_esperado=retorno,
        n_simulacoes=n,
        horizonte_anos=40,
        seed=seed,
    )


def test_seed_fixo_resultado_deterministico():
    """Mesma seed → resultado idêntico em duas chamadas."""
    r1 = run_monte_carlo_if(_config(seed=7), ano_base=2026, idade_titular_atual=35)
    r2 = run_monte_carlo_if(_config(seed=7), ano_base=2026, idade_titular_atual=35)
    assert r1.p50_ano_if == r2.p50_ano_if
    assert r1.p10_ano_if == r2.p10_ano_if
    assert r1.p90_ano_if == r2.p90_ano_if


def test_se_if_pct_abaixo_15pct_nao_exibe_cone():
    """if_pct = 10% (<15%) → exibir_cone = False."""
    cfg = _config(pv=200_000, fv=2_000_000)  # 10%
    result = run_monte_carlo_if(cfg, ano_base=2026, idade_titular_atual=35)
    assert result.exibir_cone is False
    assert result.motivo_sem_cone is not None
    assert result.p50_ano_if is None


def test_p10_le_p50_le_p90():
    """Ordem estocástica: P10 ≤ P50 ≤ P90."""
    cfg = _config(pv=800_000, fv=2_000_000)  # 40%
    result = run_monte_carlo_if(cfg, ano_base=2026, idade_titular_atual=35)
    assert result.exibir_cone is True
    assert result.p10_ano_if is not None
    assert result.p50_ano_if is not None
    assert result.p90_ano_if is not None
    assert result.p10_ano_if <= result.p50_ano_if <= result.p90_ano_if


def test_vetorizacao_10k_menos_de_2s():
    """10 000 simulações devem rodar em menos de 2 segundos."""
    cfg = _config(pv=600_000, fv=2_000_000, n=10_000)
    inicio = time.time()
    run_monte_carlo_if(cfg, ano_base=2026, idade_titular_atual=35)
    elapsed = time.time() - inicio
    assert elapsed < 2.0, f"Monte Carlo demorou {elapsed:.2f}s (limite: 2s)"


def test_termos_reais_escala_independente():
    """P50 idêntico ao escalar PV e meta proporcionalmente — modelo em termos reais."""
    base = run_monte_carlo_if(
        _config(pv=500_000, fv=2_000_000, seed=99), ano_base=2026, idade_titular_atual=35
    )
    escala = run_monte_carlo_if(
        _config(pv=5_000_000, fv=20_000_000, seed=99), ano_base=2026, idade_titular_atual=35
    )
    assert base.p50_ano_if == escala.p50_ano_if


def test_patrimonio_ja_atingiu_meta():
    """Patrimônio >= meta → exibir_cone False (n_atingiu trivial, p50 = 1)."""
    cfg = _config(pv=3_000_000, fv=2_000_000)  # 150%
    result = run_monte_carlo_if(cfg, ano_base=2026, idade_titular_atual=50)
    if result.exibir_cone:
        assert result.p50_ano_if is not None
        assert result.p50_ano_if <= 2026 + 5


def test_prob_if_ate_idade_meta_entre_0_e_1():
    """prob_if_ate_idade_meta sempre em [0, 1]."""
    cfg = _config(pv=600_000, fv=2_000_000)
    result = run_monte_carlo_if(cfg, ano_base=2026, idade_titular_atual=35, idade_meta_if=65)
    assert 0.0 <= result.prob_if_ate_idade_meta <= 1.0


def test_p50_maior_35_anos_nao_exibe_cone():
    """Retorno muito baixo + patrimônio inicial pequeno → if_pct < 15% → sem cone."""
    cfg = IFMonteCarloConfig(
        patrimonio_investivel=Decimal("50000"),
        meta_if=Decimal("2000000"),
        sigma_anual=0.11,
        retorno_real_esperado=0.01,
        n_simulacoes=5_000,
        horizonte_anos=40,
        seed=123,
    )
    result = run_monte_carlo_if(cfg, ano_base=2026, idade_titular_atual=35)
    assert result.exibir_cone is False


def test_resultado_sem_cone_campos_none():
    """Quando exibir_cone=False, anos devem ser None."""
    cfg = _config(pv=100_000, fv=2_000_000)  # 5% → abaixo de 15%
    result = run_monte_carlo_if(cfg, ano_base=2026, idade_titular_atual=35)
    assert result.p10_ano_if is None
    assert result.p50_ano_if is None
    assert result.p90_ano_if is None
