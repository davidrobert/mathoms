"""Cone Monte Carlo de IF (N3 · ADR-237) — ``if_projector`` resolve o prazo
determinístico, este módulo simula a dispersão em torno dele.
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

# ADR-361 — um percentil de tempo-até-o-evento só é publicável como ano se a
# taxa de sucesso no horizonte o define: P(atingir até o ano rotulado Pk) tem de
# ser k%. A folga de 5 pp sobre o piso evita publicar o ano dos últimos caminhos
# a cruzar, que é instável ao horizonte e ao seed.
_PISO_P10, _PISO_P50, _PISO_P90 = 0.10, 0.50, 0.90
_FOLGA_PUBLICACAO = 0.05

# ADR-360 — seed é constante de MODELO, não parâmetro do cliente: mantém o cone
# reprodutível e monótono em patrimônio/aporte (derivar do input re-sortearia a
# cada centavo, e mais aporte poderia reportar cone pior). Valor escolhido ex
# ante — o próprio número da ADR, precedente ADR-281 — porque escolher seed
# olhando o resultado é fabricar número. Nunca configurável por workspace.
_MC_SEED = 360
_MC_N_SIMULACOES = 50_000
# Versão do CONTRATO publicado do cone, não do RNG (padrão score_version /
# ADR-217 §D3): ausente = v1 (não-seedado, n=10k, percentil dos sobreviventes) ·
# "2.0" = seedado, percentil dos sobreviventes · "3.0" = seedado, percentil
# censurado na base cheia (ADR-361). O mesmo `p50_ano_if` significa números
# não-comparáveis entre 2.0 e 3.0 — é o que o carimbo existe para separar.
_MC_VERSION = "3.0"


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
    horizonte_anos: int = 40
    # ADR-361 — taxa de sucesso no horizonte simulado, base cheia (`n`). É o
    # denominador que decide a censura: substitui o ano quando ele não existe.
    prob_if_ate_horizonte: float = 0.0
    # Por-percentil e explícito porque o consumidor que NÃO pode inferir é o
    # parecer, que lê o bloco cru sem o schema: `null` sozinho significaria tanto
    # "cone não simulado" quanto "não atinge no horizonte". Só é significativo
    # com `exibir_cone=True`; derivados de um único predicado sobre
    # `prob_if_ate_horizonte`, logo monótonos (P50 censurado ⇒ P90 censurado).
    p10_censurado: bool = False
    p50_censurado: bool = False
    p90_censurado: bool = False


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


def _gate_exibicao(if_pct: float) -> tuple[bool, str | None]:
    """Retorna (exibir, motivo). Suprime o cone só por insuficiência de DADO."""
    # ADR-361: o gate antigo também suprimia quando `P50 > 35 anos` — lendo o P50
    # enviesado, e portanto escondendo o cone justamente nos planos que mais
    # precisavam do diagnóstico, num rodapé cinza. Má notícia agora é dita pela
    # copy, não pela ausência do bloco.
    if if_pct < _GATE_IF_PCT_MIN:
        return False, "acumulação inicial — foco em consistência de aporte"
    return True, None


def _quantil_censurado(
    primeiro_true: np.ndarray, alguma_vez: np.ndarray, k: float, prob_sucesso: float
) -> int | None:
    """Quantil ``k`` do ano de chegada na base cheia; ``None`` se censurado."""
    # `inverted_cdf` é o quantil empírico exato — min{t : F(t) >= k} — sobre anos
    # inteiros, então não há interpolação para `int()` truncar (o antigo
    # `int(np.percentile(...))` enviesava ~meio ano para baixo).
    if prob_sucesso < k + _FOLGA_PUBLICACAO:
        return None
    tempos = np.where(alguma_vez, primeiro_true + 1, np.inf)
    return int(np.quantile(tempos, k, method="inverted_cdf"))


def _percentis_publicaveis(
    primeiro_true: np.ndarray, alguma_vez: np.ndarray, prob_sucesso: float
) -> tuple[tuple[int | None, int | None, int | None], tuple[bool, bool, bool]]:
    """(P10, P50, P90) em anos relativos + flags de censura."""
    p10, p50, p90 = (
        _quantil_censurado(primeiro_true, alguma_vez, piso, prob_sucesso)
        for piso in (_PISO_P10, _PISO_P50, _PISO_P90)
    )
    if p50 is None:
        # Guarda de assimetria: a censura morde primeiro a perna adversa, então
        # publicar só a favorável trocaria o viés otimista por um pior — sobraria
        # apenas a boa notícia. Cenário favorável não sai sem o central.
        p10 = None
    return (p10, p50, p90), (p10 is None, p50 is None, p90 is None)


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
    percentis: tuple[int | None, int | None, int | None], ano_base: int, exibir: bool
) -> tuple[int | None, int | None, int | None]:
    """Aplica ano_base offset; (None, None, None) se cone não exibido."""
    # Percentil já censurado entra `None` e sai `None` — offset não inventa ano.
    if not exibir:
        return None, None, None
    p10, p50, p90 = percentis
    return tuple(None if p is None else ano_base + p for p in (p10, p50, p90))  # type: ignore[return-value]


def _proveniencia(config: IFMonteCarloConfig) -> dict:
    """ADR-360/361 — campos observados do config que rodou (não declarados)."""
    return {
        "seed_usado": config.seed,
        "n_simulacoes_usado": config.n_simulacoes,
        "horizonte_anos": config.horizonte_anos,
    }


def _campos_comuns(config: IFMonteCarloConfig, idade_meta: int | None) -> dict:
    """Campos que não dependem do resultado da simulação."""
    return {
        "idade_meta_usada": idade_meta,
        "sigma_usado": config.sigma_anual,
        "aporte_mensal_usado": config.aporte_mensal,
        **_proveniencia(config),
    }


def _resultado_sem_cone(
    motivo: str,
    idade_meta: int | None,
    config: IFMonteCarloConfig,
    *,
    prob_if_ate_idade_meta: float | None = 0.0,
    prob_if_ate_horizonte: float = 0.0,
) -> MonteCarloIFResult:
    return MonteCarloIFResult(
        p10_ano_if=None,
        p50_ano_if=None,
        p90_ano_if=None,
        # #1158: sem idade-meta não há horizonte, então a probabilidade é
        # ausência — 0,0 afirmaria "nenhuma simulação atinge".
        prob_if_ate_idade_meta=(None if idade_meta is None else prob_if_ate_idade_meta),
        exibir_cone=False,
        motivo_sem_cone=motivo,
        prob_if_ate_horizonte=prob_if_ate_horizonte,
        **_campos_comuns(config, idade_meta),
    )


def _resultado_meta_atingida(
    idade_meta: int | None, config: IFMonteCarloConfig
) -> MonteCarloIFResult:
    """Patrimônio >= meta: não há pergunta "em que ano" (ADR-361)."""
    # O caminho antigo caía no horizonte-meta degenerado (`prazo=0` →
    # `primeiro_true < 0` nunca verdadeiro) e publicava "0% de chance de atingir
    # IF" para a família que já é independente.
    return _resultado_sem_cone(
        "meta já atingida",
        idade_meta,
        config,
        prob_if_ate_idade_meta=1.0,
        prob_if_ate_horizonte=1.0,
    )


@dataclass(frozen=True)
class _NucleoMC:
    """Saída bruta da simulação, antes do offset de ``ano_base``."""

    percentis: tuple[int | None, int | None, int | None]
    censurados: tuple[bool, bool, bool]
    exibir: bool
    motivo: str | None
    prob_if_ate_idade_meta: float | None
    prob_if_ate_horizonte: float
    patrimonios: np.ndarray


def _mc_core(
    pv: float, fv: float, config: IFMonteCarloConfig, horizonte_meta: int | None
) -> _NucleoMC | None:
    """Roda as simulações e resolve percentis + gate, ou None se nenhuma atinge."""
    mu_log, sigma_log = _lognormal_params(config.retorno_real_esperado, config.sigma_anual)
    anos, n, p_true, alguma_vez, patrimonios = _simular_caminhos(pv, fv, config, mu_log, sigma_log)
    if not anos:
        return None
    prob_horizonte = round(float(alguma_vez.mean()), 4)
    percentis, censurados = _percentis_publicaveis(p_true, alguma_vez, prob_horizonte)
    exibir, motivo = _gate_exibicao(pv / fv)
    horizonte = None if horizonte_meta is None else max(0, horizonte_meta)
    prob_meta = _prob_ate_meta(alguma_vez, p_true, horizonte, n)
    args = (percentis, censurados, exibir, motivo, prob_meta, prob_horizonte)
    return _NucleoMC(*args, patrimonios)


def _caminhos_kwargs(patrimonios: np.ndarray, ano_base: int, exibir: bool) -> dict:
    """Séries do cone como kwargs; vazio quando o gate desliga a exibição."""
    if not exibir:
        return {}
    cp = _calcular_caminhos_percentis(patrimonios, ano_base)
    return {"caminho_p10": cp[0], "caminho_p50": cp[1], "caminho_p90": cp[2]}


def _censura_kwargs(core: _NucleoMC) -> dict:
    """Flags de censura; falsas sem cone, senão o consumidor leria censura onde
    não houve simulação."""
    c10, c50, c90 = core.censurados if core.exibir else (False, False, False)
    return {"p10_censurado": c10, "p50_censurado": c50, "p90_censurado": c90}


def _build_mc_result(
    core: _NucleoMC, config: IFMonteCarloConfig, ano_base: int, idade_meta_if: int | None
) -> MonteCarloIFResult:
    p10, p50, p90 = _anos_if(core.percentis, ano_base, core.exibir)
    return MonteCarloIFResult(
        p10_ano_if=p10,
        p50_ano_if=p50,
        p90_ano_if=p90,
        prob_if_ate_idade_meta=core.prob_if_ate_idade_meta,
        exibir_cone=core.exibir,
        motivo_sem_cone=core.motivo,
        prob_if_ate_horizonte=core.prob_if_ate_horizonte,
        **_censura_kwargs(core),
        **_caminhos_kwargs(core.patrimonios, ano_base, core.exibir),
        **_campos_comuns(config, idade_meta_if),
    )


def _resultado_degenerado(
    pv: float, fv: float, idade_meta: int | None, config: IFMonteCarloConfig
) -> MonteCarloIFResult | None:
    """Casos em que simular não responde nada; ``None`` = simular normalmente."""
    if fv <= 0 or pv < 0:
        return _resultado_sem_cone("meta_if inválida ou patrimônio negativo", idade_meta, config)
    if pv >= fv:
        return _resultado_meta_atingida(idade_meta, config)
    return None


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
    degenerado = _resultado_degenerado(pv, fv, idade_meta_if, config)
    if degenerado is not None:
        return degenerado
    horizonte = None if idade_meta_if is None else idade_meta_if - idade_titular_atual
    core = _mc_core(pv, fv, config, horizonte)
    if core is None:
        motivo = "acumulação inicial — foco em consistência de aporte"
        return _resultado_sem_cone(motivo, idade_meta_if, config)
    return _build_mc_result(core, config, ano_base, idade_meta_if)
