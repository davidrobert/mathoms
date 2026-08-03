"""Cone Monte Carlo de IF (N3 · ADR-237) — extraído de ``if_projector.py``.

Separado por responsabilidade: ``if_projector`` resolve o prazo determinístico,
este módulo simula a dispersão em torno dele.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal

import numpy as np

_SIGMA_POR_PERFIL: dict[str, float] = {
    "conservador": 0.07,
    "moderado": 0.11,
    "agressivo": 0.15,
}

_GATE_IF_PCT_MIN = 0.15  # < 15% → não exibir cone
_GATE_P50_MAX = 35  # P50 > 35 anos → não exibir cone

# ADR-360 — seed é constante de MODELO, não parâmetro do cliente: mantém o cone
# reprodutível e monótono em patrimônio/aporte (derivar do input re-sortearia a
# cada centavo, e mais aporte poderia reportar cone pior). Valor escolhido ex
# ante — o próprio número da ADR, precedente ADR-281 — porque escolher seed
# olhando o resultado é fabricar número. Nunca configurável por workspace.
_MC_SEED = 360
_MC_N_SIMULACOES = 50_000
_MC_VERSION = "2.0"


@dataclass(frozen=True)
class IFMonteCarloConfig:
    """Parâmetros estocásticos do Monte Carlo IF (N3) — entradas em termos REAIS."""

    patrimonio_investivel: Decimal
    meta_if: Decimal
    sigma_anual: float = 0.11
    retorno_real_esperado: float = 0.05
    n_simulacoes: int = _MC_N_SIMULACOES
    horizonte_anos: int = 40
    seed: int = _MC_SEED
    ano_base: int = 2026
    aporte_mensal: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        # ADR-360: `seed=None` semeia da entropia do SO e o payload continua
        # "válido" — bug invisível em review. O guard torna a classe de bug
        # inconstruível, que é mais forte que um teste sobre a função.
        if self.seed is None:
            raise ValueError(
                "IFMonteCarloConfig.seed não pode ser None (ADR-360 — cone "
                f"reprodutível): esperado int, got {self.seed!r}"
            )


@dataclass(frozen=True)
class MonteCarloIFResult:
    """Saída de :func:`run_monte_carlo_if` — cone P10/P50/P90 para S7."""

    p10_ano_if: int | None
    p50_ano_if: int | None
    p90_ano_if: int | None
    # `None` quando a projeção determinística não produziu idade-meta: sem alvo
    # não há "probabilidade até a idade X" a medir. O cone (P10/P50/P90) não
    # depende da idade-meta e continua sendo produzido.
    prob_if_ate_idade_meta: float | None
    idade_meta_usada: int | None
    sigma_usado: float
    exibir_cone: bool
    # ADR-237 — PMT mensal real assumido na simulação (R$/mês de hoje).
    # Decimal por ADR-090; serializado como float no wire JSON pela e5_serialization.
    aporte_mensal_usado: Decimal = Decimal("0")
    motivo_sem_cone: str | None = None
    # Cone paths — list of (year, brl_value) sorted by year; empty when exibir_cone=False.
    caminho_p10: tuple[tuple[int, float], ...] = field(default_factory=tuple)
    caminho_p50: tuple[tuple[int, float], ...] = field(default_factory=tuple)
    caminho_p90: tuple[tuple[int, float], ...] = field(default_factory=tuple)
    # ADR-360 — proveniência: o artefato tem de bastar para reproduzir o cone.
    # `mc_version` é declarado (bump exige ADR sucessora, padrão score_version /
    # ADR-217); os outros dois são observados do config que rodou.
    mc_version: str = _MC_VERSION
    seed_usado: int = _MC_SEED
    n_simulacoes_usado: int = _MC_N_SIMULACOES


def _lognormal_params(r: float, sigma: float) -> tuple[float, float]:
    """Converte retorno real + sigma para parâmetros log-normais (preserva E[r])."""
    sigma_log = math.sqrt(math.log(1 + sigma**2 / (1 + r) ** 2))
    mu_log = math.log(1 + r) - 0.5 * sigma_log**2
    return mu_log, sigma_log


def _compute_patrimonios(pv: float, pmt_anual: float, log_retornos: np.ndarray) -> np.ndarray:
    # ADR-237: PMT como anuidade ordinária (fim do ano); PMT=0 cai no legado.
    if pmt_anual == 0.0:
        return pv * np.exp(np.cumsum(log_retornos, axis=1))
    n, h = log_retornos.shape
    r_factors = np.exp(log_retornos)
    patrimonios = np.empty((n, h), dtype=np.float64)
    w = np.full(n, pv, dtype=np.float64)
    for t in range(h):
        w = w * r_factors[:, t] + pmt_anual
        patrimonios[:, t] = w
    return patrimonios


def _simular_caminhos(
    pv: float,
    fv: float,
    config: IFMonteCarloConfig,
    mu_log: float,
    sigma_log: float,
) -> tuple[list[int], int, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(config.seed)
    n, h = config.n_simulacoes, config.horizonte_anos
    # ADR-360: z padrão escalado depois — location-scale explícita, então revisar
    # a premissa muda a largura do cone, não o sorteio (não depende do Generator).
    log_retornos = mu_log + sigma_log * rng.standard_normal((n, h))
    pmt_anual = float(config.aporte_mensal) * 12.0
    patrimonios = _compute_patrimonios(pv, pmt_anual, log_retornos)
    atingiu = patrimonios >= fv
    primeiro_true = np.argmax(atingiu, axis=1)
    alguma_vez = atingiu.any(axis=1)
    anos = (primeiro_true[alguma_vez] + 1).tolist()
    return anos, n, primeiro_true, alguma_vez, patrimonios


def _gate_exibicao(if_pct: float, p50_anos: int) -> tuple[bool, str | None]:
    """Retorna (exibir, motivo) conforme gates N3."""
    if if_pct < _GATE_IF_PCT_MIN:
        return False, "acumulação inicial — foco em consistência de aporte"
    if p50_anos > _GATE_P50_MAX:
        return False, "horizonte muito longo — revise aporte ou meta"
    return True, None


def _calcular_percentis(anos: list[int]) -> tuple[int, int, int]:
    """Retorna (P10, P50, P90) em anos."""
    arr = np.array(anos)
    return int(np.percentile(arr, 10)), int(np.percentile(arr, 50)), int(np.percentile(arr, 90))


def _calcular_caminhos_percentis(
    patrimonios: np.ndarray, ano_base: int
) -> tuple[
    tuple[tuple[int, float], ...], tuple[tuple[int, float], ...], tuple[tuple[int, float], ...]
]:
    """Séries P10/P50/P90 de patrimônio por ano; patrimonios shape (n, horizonte)."""
    horizonte = patrimonios.shape[1]
    p10_vals = np.percentile(patrimonios, 10, axis=0)
    p50_vals = np.percentile(patrimonios, 50, axis=0)
    p90_vals = np.percentile(patrimonios, 90, axis=0)
    anos_abs = [ano_base + t + 1 for t in range(horizonte)]
    caminho_p10 = tuple((ano, float(v)) for ano, v in zip(anos_abs, p10_vals))
    caminho_p50 = tuple((ano, float(v)) for ano, v in zip(anos_abs, p50_vals))
    caminho_p90 = tuple((ano, float(v)) for ano, v in zip(anos_abs, p90_vals))
    return caminho_p10, caminho_p50, caminho_p90


def _prob_ate_meta(
    alguma_vez: np.ndarray, primeiro_true: np.ndarray, horizonte_meta: int | None, n: int
) -> float | None:
    """Fração de simulações que atingem IF antes do horizonte-meta."""
    # Sem horizonte não há o que medir: a métrica é "probabilidade até a idade
    # X"; devolver 0.0 afirmaria "nenhuma simulação atinge".
    if horizonte_meta is None:
        return None
    n_ate = int(np.sum(alguma_vez & (primeiro_true < horizonte_meta)))
    return round(n_ate / n, 4) if n > 0 else 0.0


def _anos_if(
    percentis: tuple[int, int, int], ano_base: int, exibir: bool
) -> tuple[int | None, int | None, int | None]:
    """Aplica ano_base offset ou retorna (None, None, None) se cone não exibido."""
    if not exibir:
        return None, None, None
    p10, p50, p90 = percentis
    return ano_base + p10, ano_base + p50, ano_base + p90


def _proveniencia(config: IFMonteCarloConfig) -> dict:
    """ADR-360 — campos observados do config que rodou (não declarados)."""
    return {"seed_usado": config.seed, "n_simulacoes_usado": config.n_simulacoes}


def _resultado_sem_cone(
    motivo: str,
    idade_meta: int | None,
    config: IFMonteCarloConfig,
) -> MonteCarloIFResult:
    return MonteCarloIFResult(
        p10_ano_if=None,
        p50_ano_if=None,
        p90_ano_if=None,
        prob_if_ate_idade_meta=None if idade_meta is None else 0.0,
        idade_meta_usada=idade_meta,
        sigma_usado=config.sigma_anual,
        exibir_cone=False,
        aporte_mensal_usado=config.aporte_mensal,
        motivo_sem_cone=motivo,
        **_proveniencia(config),
    )


def _mc_core(
    pv: float,
    fv: float,
    config: IFMonteCarloConfig,
    horizonte_meta: int | None,
) -> tuple[tuple[int, int, int], bool, str | None, float | None, np.ndarray] | None:
    """Roda simulações e retorna (percentis, exibir, motivo, prob, patrimonios) ou None."""
    mu_log, sigma_log = _lognormal_params(config.retorno_real_esperado, config.sigma_anual)
    anos, n, p_true, alguma_vez, patrimonios = _simular_caminhos(pv, fv, config, mu_log, sigma_log)
    if not anos:
        return None
    percentis = _calcular_percentis(anos)
    exibir, motivo = _gate_exibicao(pv / fv, percentis[1])
    horizonte = None if horizonte_meta is None else max(0, horizonte_meta)
    prob = _prob_ate_meta(alguma_vez, p_true, horizonte, n)
    return percentis, exibir, motivo, prob, patrimonios


def _caminhos_kwargs(patrimonios: np.ndarray, ano_base: int, exibir: bool) -> dict:
    """Séries do cone como kwargs; vazio quando o gate desliga a exibição."""
    if not exibir:
        return {}
    cp = _calcular_caminhos_percentis(patrimonios, ano_base)
    return {"caminho_p10": cp[0], "caminho_p50": cp[1], "caminho_p90": cp[2]}


def _build_mc_result(
    core: tuple, config: IFMonteCarloConfig, ano_base: int, idade_meta_if: int | None
) -> MonteCarloIFResult:
    percentis, exibir, motivo, prob, patrimonios = core
    p10, p50, p90 = _anos_if(percentis, ano_base, exibir)
    return MonteCarloIFResult(
        p10_ano_if=p10,
        p50_ano_if=p50,
        p90_ano_if=p90,
        prob_if_ate_idade_meta=prob,
        idade_meta_usada=idade_meta_if,
        sigma_usado=config.sigma_anual,
        exibir_cone=exibir,
        aporte_mensal_usado=config.aporte_mensal,
        motivo_sem_cone=motivo,
        **_caminhos_kwargs(patrimonios, ano_base, exibir),
        **_proveniencia(config),
    )


def run_monte_carlo_if(
    config: IFMonteCarloConfig,
    ano_base: int,
    idade_titular_atual: int,
    idade_meta_if: int | None = 65,
) -> MonteCarloIFResult:
    """50 000 simulações log-normais → P10/P50/P90 + gate de cone; reprodutível."""
    # ADR-360: seed é constante de modelo, então o cone é função pura dos inputs
    # de domínio e monótono em patrimônio/aporte. `idade_meta_if=None`
    # (determinística sem prazo) suprime só prob/idade_meta — o cone independe.
    pv, fv = float(config.patrimonio_investivel), float(config.meta_if)
    if fv <= 0 or pv < 0:
        return _resultado_sem_cone("meta_if inválida ou patrimônio negativo", idade_meta_if, config)
    horizonte_meta = None if idade_meta_if is None else idade_meta_if - idade_titular_atual
    core = _mc_core(pv, fv, config, horizonte_meta)
    if core is None:
        return _resultado_sem_cone(
            "acumulação inicial — foco em consistência de aporte", idade_meta_if, config
        )
    return _build_mc_result(core, config, ano_base, idade_meta_if)
