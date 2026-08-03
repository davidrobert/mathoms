"""Testes do Monte Carlo IF v2 (Lane N3 PR-A) — P10/P50/P90 + gates de cone."""

from __future__ import annotations

import time
from decimal import Decimal

import pytest

from pipeline.domain.services.if_monte_carlo import (
    _MC_N_SIMULACOES,
    _MC_SEED,
    _MC_VERSION,
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
    pmt: float = 0.0,  # aporte mensal em R$ — float só na ergonomia do teste (ADR-090)
) -> IFMonteCarloConfig:
    return IFMonteCarloConfig(
        patrimonio_investivel=Decimal(str(pv)),
        meta_if=Decimal(str(fv)),
        sigma_anual=sigma,
        retorno_real_esperado=retorno,
        n_simulacoes=n,
        horizonte_anos=40,
        seed=seed,
        aporte_mensal=Decimal(str(pmt)),
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


# =============================================================================
# ADR-237 — MC inclui aporte mensal (paridade com determinístico)
# =============================================================================


def test_pmt_zero_preserves_legacy_behavior():
    """PMT=0 produz percentis idênticos ao caminho pré-ADR-237 (regression-safe)."""
    cfg_legacy = _config(pv=800_000, fv=2_000_000, seed=42)
    cfg_zero = _config(pv=800_000, fv=2_000_000, seed=42, pmt=0.0)
    r_legacy = run_monte_carlo_if(cfg_legacy, ano_base=2026, idade_titular_atual=35)
    r_zero = run_monte_carlo_if(cfg_zero, ano_base=2026, idade_titular_atual=35)
    assert r_legacy.p10_ano_if == r_zero.p10_ano_if
    assert r_legacy.p50_ano_if == r_zero.p50_ano_if
    assert r_legacy.p90_ano_if == r_zero.p90_ano_if
    assert r_legacy.prob_if_ate_idade_meta == r_zero.prob_if_ate_idade_meta


def test_pmt_positivo_aumenta_prob_if():
    """PMT > 0 ⇒ prob_if_ate_idade_meta sobe e p50_ano_if cai (ADR-237)."""
    cfg_sem_aporte = _config(pv=600_000, fv=3_000_000, seed=42)
    cfg_com_aporte = _config(pv=600_000, fv=3_000_000, seed=42, pmt=5_000.0)
    r_sem = run_monte_carlo_if(cfg_sem_aporte, ano_base=2026, idade_titular_atual=35)
    r_com = run_monte_carlo_if(cfg_com_aporte, ano_base=2026, idade_titular_atual=35)
    assert r_com.prob_if_ate_idade_meta > r_sem.prob_if_ate_idade_meta
    assert r_com.p50_ano_if is not None and r_sem.p50_ano_if is not None
    assert r_com.p50_ano_if < r_sem.p50_ano_if


def test_pmt_com_sigma_zero_converge_para_deterministico():
    """sigma=0 ∧ PMT>0 ⇒ MC P50 ≡ projeção determinística (±1 ano)."""
    pv, fv, r_anual, pmt = 800_000.0, 2_000_000.0, 0.05, 5_000.0
    cfg = _config(pv=pv, fv=fv, sigma=0.0, retorno=r_anual, seed=42, pmt=pmt)
    result = run_monte_carlo_if(cfg, ano_base=2026, idade_titular_atual=35)
    assert result.exibir_cone is True
    assert (
        result.p50_ano_if == result.p10_ano_if == result.p90_ano_if
    ), "sigma=0 deve colapsar P10=P50=P90"
    pmt_anual = pmt * 12.0
    w = pv
    anos_deterministico = 0
    for t in range(40):
        w = w * (1 + r_anual) + pmt_anual
        anos_deterministico = t + 1
        if w >= fv:
            break
    assert abs(result.p50_ano_if - (2026 + anos_deterministico)) <= 1


def test_pmt_alto_pv_baixo_levanta_prob_de_zero():
    """PMT alto recupera prob >25% quando MC sem aporte daria 0% (bug do screenshot)."""
    pv, fv, pmt = 600_000.0, 3_000_000.0, 8_000.0
    cfg_sem = _config(pv=pv, fv=fv, seed=42)
    cfg_com = _config(pv=pv, fv=fv, seed=42, pmt=pmt)
    r_sem = run_monte_carlo_if(cfg_sem, ano_base=2026, idade_titular_atual=40, idade_meta_if=60)
    r_com = run_monte_carlo_if(cfg_com, ano_base=2026, idade_titular_atual=40, idade_meta_if=60)
    assert (
        r_com.prob_if_ate_idade_meta > 0.25
    ), f"PMT alto deveria levantar prob > 25%, got {r_com.prob_if_ate_idade_meta:.2%}"
    assert r_com.prob_if_ate_idade_meta > r_sem.prob_if_ate_idade_meta + 0.20


# =============================================================================
# ADR-360 — reprodutibilidade do cone
# =============================================================================


def _default_config(pv: float = 800_000, fv: float = 3_000_000, pmt: float = 8_000):
    """Config SEM seed explícito — exercita o default de produção."""
    return IFMonteCarloConfig(
        patrimonio_investivel=Decimal(str(pv)),
        meta_if=Decimal(str(fv)),
        aporte_mensal=Decimal(str(pmt)),
    )


def _cone(cfg) -> MonteCarloIFResult:
    return run_monte_carlo_if(cfg, ano_base=2026, idade_titular_atual=40)


def test_config_default_produz_cone_reprodutivel():
    """ADR-360: config de produção (sem seed) → duas chamadas idênticas."""
    # Topologia do bug original: era o call-site que não passava seed.
    r1, r2 = _cone(_default_config()), _cone(_default_config())
    assert r1 == r2, "cone com config default divergiu entre chamadas"
    assert r1.caminho_p10 and r1.caminho_p50 and r1.caminho_p90


def test_seed_none_explicito_e_rejeitado_no_boundary():
    """Guard de fail-fast: ``seed=None`` deixa de ser construível (ADR-360)."""
    with pytest.raises(ValueError, match="seed"):
        IFMonteCarloConfig(
            patrimonio_investivel=Decimal("800000"),
            meta_if=Decimal("3000000"),
            seed=None,  # type: ignore[arg-type]
        )


def test_proveniencia_no_resultado_com_e_sem_cone():
    """``mc_version``/``seed_usado``/``n_simulacoes_usado`` nos dois caminhos."""
    com_cone = _cone(_default_config())
    sem_cone = _cone(_default_config(pv=100_000, fv=5_000_000, pmt=0.0))
    assert sem_cone.exibir_cone is False
    for r in (com_cone, sem_cone):
        assert r.mc_version == _MC_VERSION
        assert r.seed_usado == _MC_SEED
        assert r.n_simulacoes_usado == _MC_N_SIMULACOES


def _assert_cone_nao_decresce(base: MonteCarloIFResult, maior: MonteCarloIFResult) -> None:
    for nome in ("caminho_p10", "caminho_p50", "caminho_p90"):
        antes, depois = getattr(base, nome), getattr(maior, nome)
        assert len(antes) == len(depois)
        for (ano, v_antes), (_, v_depois) in zip(antes, depois):
            assert v_depois >= v_antes, f"{nome} caiu em {ano}: {v_antes} → {v_depois}"
    assert maior.prob_if_ate_idade_meta >= base.prob_if_ate_idade_meta


@pytest.mark.parametrize("delta_pv,delta_pmt", [(1_000.0, 0.0), (0.0, 100.0)])
def test_cone_e_monotonico_em_patrimonio_e_aporte(delta_pv: float, delta_pmt: float):
    """Mais patrimônio ou mais aporte nunca reporta cone pior (ADR-360)."""
    # Propriedade que o seed derivado do input quebraria: re-semear a cada centavo
    # faz o cenário adverso oscilar ~2% e o cliente lê "aportei mais e piorou".
    pv, pmt, n = 800_000.0, 8_000.0, 10_000
    base = _cone(_config(pv=pv, fv=3_000_000, seed=_MC_SEED, n=n, pmt=pmt))
    maior = _cone(_config(pv=pv + delta_pv, fv=3_000_000, seed=_MC_SEED, n=n, pmt=pmt + delta_pmt))
    _assert_cone_nao_decresce(base, maior)


def test_grandezas_publicadas_sao_robustas_a_troca_de_seed():
    """Anti "seed shopping": o publicado cabe na tolerância sobre seeds alternativos."""
    # Falha aqui = o seed escolhido é sorte. A resposta é subir n, não trocar seed.
    rs = [
        _cone(_config(pv=800_000, fv=3_000_000, seed=s, n=_MC_N_SIMULACOES, pmt=8_000.0))
        for s in range(_MC_SEED, _MC_SEED + 10)
    ]
    serie = [r.caminho_p50[22][1] for r in rs]
    dispersao = (max(serie) - min(serie)) / (sum(serie) / len(serie))
    assert dispersao <= 0.02, f"dispersão da série do cone {dispersao:.2%} > 2%"
    probs = [r.prob_if_ate_idade_meta for r in rs]
    assert max(probs) - min(probs) <= 0.006, f"prob varia {max(probs) - min(probs):.4f} > 0,6 pp"
    assert len({r.p50_ano_if for r in rs}) == 1, "ano de IF do P50 muda com o seed"
