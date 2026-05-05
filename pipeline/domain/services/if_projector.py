"""IFProjector — projeção de Independência Financeira (Sessão A5a · Fase 8).

Extrai ``analyze_goals`` (e5_analyze.py:971) + helpers
``extract_if_target_from_life_plan``, ``extract_if_trs``,
``extract_renda_passiva_from_life_plan``, ``calculate_edad`` em um domain
service puro.

Recebe :class:`IFProjectorConfig` (R9/ISP) com todos os parâmetros de
projeção (TRS, retorno real anual, taxa de retirada, aporte mensal, DOBs).
Sem I/O — a leitura de ``goals.json`` / ``life_plan_goals.md`` continua no
shell que constrói a config.

Retorna :class:`IFProjection` frozen com campos:
- ``if_meta`` — R$ alvo
- ``if_trs`` — % TRS
- ``if_trs_monthly_value`` — R$ alvo × TRS mensal (renda passiva esperada)
- ``if_pct`` — progresso (%)
- ``if_gap`` — R$ faltante
- ``prazo_anos_realista`` — math de juros compostos (PV+PMT)
- ``idade_titular_if`` / ``idade_conjuge_if`` / ``ano_if``
- ``renda_passiva_estimada_4pct`` — ``investivel × 4% / 12``
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import numpy as np

_TODAY_FALLBACK = date(2026, 4, 19)


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.replace(".", "").replace(",", "."))
        except ValueError:
            return 0.0
    return 0.0


def _calculate_age(dob: date, reference_date: date) -> int:
    """Idade em anos (calendar-accurate) — paridade com ``calculate_edad``."""
    age = reference_date.year - dob.year
    if (reference_date.month, reference_date.day) < (dob.month, dob.day):
        age -= 1
    return age


# =============================================================================
# Config
# =============================================================================


@dataclass(frozen=True)
class IFProjectorConfig:
    """Parâmetros da projeção IF (R9/ISP).

    Sources no legado:
    - ``if_meta`` ← ``goals.json::independencia_financeira.if_meta``
      (fallback: regex em ``life_plan_goals.md``).
    - ``if_trs_pct`` ← ``goals.json::independencia_financeira.trs_pct``
      (fallback: regex em ``life_plan_goals.md``).
    - ``taxa_retirada_segura_pct`` ← ``goals.json::independencia_financeira.taxa_retirada_segura_pct`` (default 4%).
    - ``retorno_real_anual_pct`` ← ``goals.json::independencia_financeira.retorno_real_anual_pct`` (default 6%).
    - ``aporte_mensal`` ← ``goals.json::aportes.meta_aporte_mensal``.
    - ``titular_dob`` / ``conjuge_dob`` ← ``family_members.json::membros[...].data_nascimento``.
    - ``reference_date`` ← ``datetime.now().date()`` no legado (injetável para testes).
    - ``titular_key`` ← ``family_members.json::titular`` (default ``"david"``).
    - ``conjuge_key`` ← membro com ``papel == "conjuge"`` em ``family_members.json`` (vazio se não houver).
    """

    if_meta: float
    if_trs_pct: float
    titular_dob: date
    taxa_retirada_segura_pct: float = 4.0
    retorno_real_anual_pct: float = 6.0
    aporte_mensal: float = 0.0
    conjuge_dob: date | None = None
    reference_date: date = _TODAY_FALLBACK
    titular_key: str = "david"
    conjuge_key: str = ""

    @classmethod
    def from_configs(
        cls,
        *,
        goals: dict | None = None,
        titular_dob: date,
        conjuge_dob: date | None = None,
        reference_date: date | None = None,
        titular_key: str = "david",
        conjuge_key: str = "",
    ) -> "IFProjectorConfig":
        """Constrói a config a partir do dict ``goals.json``.

        ``if_meta`` / ``if_trs_pct`` devem estar presentes ou em
        ``independencia_financeira``; do contrário levanta ``ValueError``
        (paridade com ``extract_if_target_from_life_plan`` / ``extract_if_trs``).
        """
        goals_cfg = (goals or {}).get("independencia_financeira", {}) or {}
        aportes_cfg = (goals or {}).get("aportes", {}) or {}

        if_meta = goals_cfg.get("if_meta")
        if if_meta is None:
            raise ValueError("IF meta não encontrada em goals.independencia_financeira.if_meta")
        if_trs = goals_cfg.get("trs_pct")
        if if_trs is None:
            raise ValueError("TRS não encontrado em goals.independencia_financeira.trs_pct")

        return cls(
            if_meta=_safe_float(if_meta),
            if_trs_pct=_safe_float(if_trs),
            titular_dob=titular_dob,
            taxa_retirada_segura_pct=_safe_float(goals_cfg.get("taxa_retirada_segura_pct", 4.0)),
            retorno_real_anual_pct=_safe_float(goals_cfg.get("retorno_real_anual_pct", 6.0)),
            aporte_mensal=_safe_float(aportes_cfg.get("meta_aporte_mensal", 0)),
            conjuge_dob=conjuge_dob,
            reference_date=reference_date or _TODAY_FALLBACK,
            titular_key=titular_key,
            conjuge_key=conjuge_key,
        )


# =============================================================================
# Helpers puros — extratores de life_plan_goals.md
# =============================================================================


def extract_if_meta_from_text(content: str) -> float | None:
    """Regex para ``**R$ ...`` em ``life_plan_goals.md``."""
    m = re.search(r"\*\*R\$\s*([\d.,]+)", content)
    if m:
        return _safe_float(m.group(1))
    return None


def extract_if_trs_from_text(content: str) -> float | None:
    """Regex para ``TRS ... ##%`` em ``life_plan_goals.md``."""
    m = re.search(r"TRS.*?(\d+(?:[.,]\d+)?)\s*%", content, re.IGNORECASE)
    if m:
        return _safe_float(m.group(1))
    return None


def extract_renda_passiva_from_text(content: str) -> float:
    """Regex para ``Renda passiva atual: R$ ...`` em ``life_plan_goals.md``."""
    m = re.search(
        r"Renda passiva atual:\s*R\$\s*([\d.,]+)",
        content,
        re.IGNORECASE,
    )
    if m:
        return _safe_float(m.group(1))
    return 0.0


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class IFProjection:
    """Saída de ``IFProjector.project``. Compatível com o output de
    ``analyze_goals`` do legado via :meth:`to_legacy_dict`.
    """

    if_meta: float
    if_trs: float
    if_trs_monthly_value: float
    if_pct: float
    if_gap: float
    prazo_anos_realista: float
    idade_titular_if: int
    ano_if: int
    renda_passiva_estimada_4pct: float
    idade_conjuge_if: int | None = None
    titular_key: str = "david"
    conjuge_key: str = ""

    def to_legacy_dict(self) -> dict:
        out: dict = {
            "if_meta": round(self.if_meta, 2),
            "if_trs": round(self.if_trs, 2),
            "if_trs_monthly_value": round(self.if_trs_monthly_value, 2),
            "if_pct": round(self.if_pct, 2),
            "if_gap": round(self.if_gap, 2),
            "prazo_anos_realista": round(self.prazo_anos_realista, 1),
            f"idade_{self.titular_key}_if": self.idade_titular_if,
            "david_idade_if": self.idade_titular_if,
            "ano_if": self.ano_if,
            "renda_passiva_estimada_4pct": round(self.renda_passiva_estimada_4pct, 2),
        }
        if self.idade_conjuge_if is not None and self.conjuge_key:
            out[f"idade_{self.conjuge_key}_if"] = self.idade_conjuge_if
        return out


# =============================================================================
# Service
# =============================================================================


class IFProjector:
    """Projeta prazo e progresso para atingir Independência Financeira.

    Função pura — recebe ``investivel`` (R$) e retorna :class:`IFProjection`.
    Cálculo do prazo realista usa math de juros compostos sobre PV+PMT:

        FV = PV · (1+r)^n + PMT · ((1+r)^n − 1) / r

    Resolvendo para n:

        n = log((FV + PMT/r) / (PV + PMT/r)) / log(1+r)

    Quando ``aporte_mensal == 0`` ou ``retorno_real_anual_pct == 0`` e
    ``investivel < if_meta``, retorna ``prazo_anos_realista = 999`` (paridade
    com legado — sinaliza "infinito/inviável").
    """

    def __init__(self, config: IFProjectorConfig) -> None:
        self._config = config

    def project(self, investivel: float) -> IFProjection:
        cfg = self._config
        if_trs_monthly = (cfg.if_trs_pct / 100.0) / 12.0
        if_trs_value = cfg.if_meta * if_trs_monthly

        if_pct = (investivel / cfg.if_meta * 100) if cfg.if_meta > 0 else 0.0
        if_gap = cfg.if_meta - investivel

        # Taxa mensal equivalente da anual composta.
        retorno_anual = cfg.retorno_real_anual_pct / 100.0
        r = (1 + retorno_anual) ** (1 / 12) - 1 if retorno_anual > 0 else 0.0

        prazo_anos = self._solve_prazo(
            investivel=investivel,
            if_meta=cfg.if_meta,
            r=r,
            aporte_mensal=cfg.aporte_mensal,
        )

        anos_restantes = int(prazo_anos)
        idade_titular_if = _calculate_age(cfg.titular_dob, cfg.reference_date) + anos_restantes
        idade_conjuge_if: int | None = None
        if cfg.conjuge_dob is not None:
            idade_conjuge_if = _calculate_age(cfg.conjuge_dob, cfg.reference_date) + anos_restantes
        ano_if = cfg.reference_date.year + anos_restantes

        taxa = cfg.taxa_retirada_segura_pct / 100.0
        renda_passiva_current = investivel * taxa / 12

        return IFProjection(
            if_meta=cfg.if_meta,
            if_trs=cfg.if_trs_pct,
            if_trs_monthly_value=if_trs_value,
            if_pct=if_pct,
            if_gap=if_gap,
            prazo_anos_realista=prazo_anos,
            idade_titular_if=idade_titular_if,
            idade_conjuge_if=idade_conjuge_if,
            ano_if=ano_if,
            renda_passiva_estimada_4pct=renda_passiva_current,
            titular_key=cfg.titular_key,
            conjuge_key=cfg.conjuge_key,
        )

    @staticmethod
    def _solve_prazo(
        *,
        investivel: float,
        if_meta: float,
        r: float,
        aporte_mensal: float,
    ) -> float:
        """Resolve n (meses) em PV*(1+r)^n + PMT*((1+r)^n - 1)/r = FV."""
        if investivel >= if_meta:
            return 0.0
        if r > 0 and aporte_mensal > 0:
            numerator = if_meta + aporte_mensal / r
            denominator = investivel + aporte_mensal / r
            if denominator > 0 and numerator / denominator > 0:
                n_meses = math.log(numerator / denominator) / math.log(1 + r)
                return max(0.0, n_meses / 12)
        return 999.0


# =============================================================================
# Monte Carlo v2 (Lane N3)
# =============================================================================

_SIGMA_POR_PERFIL: dict[str, float] = {
    "conservador": 0.07,
    "moderado": 0.11,
    "agressivo": 0.15,
}

_GATE_IF_PCT_MIN = 0.15  # < 15% → não exibir cone
_GATE_P50_MAX = 35  # P50 > 35 anos → não exibir cone


@dataclass(frozen=True)
class IFMonteCarloConfig:
    """Parâmetros estocásticos do Monte Carlo IF (N3) — entradas em termos REAIS."""

    patrimonio_investivel: Decimal
    meta_if: Decimal
    sigma_anual: float = 0.11
    retorno_real_esperado: float = 0.05
    n_simulacoes: int = 10_000
    horizonte_anos: int = 40
    seed: int | None = None


@dataclass(frozen=True)
class MonteCarloIFResult:
    """Saída de :func:`run_monte_carlo_if` — cone P10/P50/P90 para S7."""

    p10_ano_if: int | None
    p50_ano_if: int | None
    p90_ano_if: int | None
    prob_if_ate_idade_meta: float
    idade_meta_usada: int
    sigma_usado: float
    exibir_cone: bool
    motivo_sem_cone: str | None = None


def _lognormal_params(r: float, sigma: float) -> tuple[float, float]:
    """Converte retorno real + sigma para parâmetros log-normais (preserva E[r])."""
    sigma_log = math.sqrt(math.log(1 + sigma**2 / (1 + r) ** 2))
    mu_log = math.log(1 + r) - 0.5 * sigma_log**2
    return mu_log, sigma_log


def _simular_caminhos(
    pv: float,
    fv: float,
    config: IFMonteCarloConfig,
    mu_log: float,
    sigma_log: float,
) -> tuple[list[int], int, np.ndarray, np.ndarray]:
    """Roda simulações vetorizadas; retorna (anos_atingiu, n_total, argmax, mask)."""
    rng = np.random.default_rng(config.seed)
    n, h = config.n_simulacoes, config.horizonte_anos
    log_retornos = rng.normal(mu_log, sigma_log, (n, h))
    patrimonios = pv * np.exp(np.cumsum(log_retornos, axis=1))
    atingiu = patrimonios >= fv
    primeiro_true = np.argmax(atingiu, axis=1)
    alguma_vez = atingiu.any(axis=1)
    anos = (primeiro_true[alguma_vez] + 1).tolist()
    return anos, n, primeiro_true, alguma_vez


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


def _prob_ate_meta(
    alguma_vez: np.ndarray, primeiro_true: np.ndarray, horizonte_meta: int, n: int
) -> float:
    """Fração de simulações que atingem IF antes do horizonte-meta."""
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


def _resultado_sem_cone(
    motivo: str,
    idade_meta: int,
    config: IFMonteCarloConfig,
) -> MonteCarloIFResult:
    return MonteCarloIFResult(
        p10_ano_if=None,
        p50_ano_if=None,
        p90_ano_if=None,
        prob_if_ate_idade_meta=0.0,
        idade_meta_usada=idade_meta,
        sigma_usado=config.sigma_anual,
        exibir_cone=False,
        motivo_sem_cone=motivo,
    )


def _mc_core(
    pv: float,
    fv: float,
    config: IFMonteCarloConfig,
    horizonte_meta: int,
) -> tuple[tuple[int, int, int], bool, str | None, float] | None:
    """Roda simulações e retorna (percentis, exibir, motivo, prob) ou None."""
    mu_log, sigma_log = _lognormal_params(config.retorno_real_esperado, config.sigma_anual)
    anos, n, p_true, alguma_vez = _simular_caminhos(pv, fv, config, mu_log, sigma_log)
    if not anos:
        return None
    percentis = _calcular_percentis(anos)
    exibir, motivo = _gate_exibicao(pv / fv, percentis[1])
    prob = _prob_ate_meta(alguma_vez, p_true, max(0, horizonte_meta), n)
    return percentis, exibir, motivo, prob


def _build_mc_result(
    core: tuple, config: IFMonteCarloConfig, ano_base: int, idade_meta_if: int
) -> MonteCarloIFResult:
    percentis, exibir, motivo, prob = core
    p10, p50, p90 = _anos_if(percentis, ano_base, exibir)
    return MonteCarloIFResult(
        p10_ano_if=p10,
        p50_ano_if=p50,
        p90_ano_if=p90,
        prob_if_ate_idade_meta=prob,
        idade_meta_usada=idade_meta_if,
        sigma_usado=config.sigma_anual,
        exibir_cone=exibir,
        motivo_sem_cone=motivo,
    )


def run_monte_carlo_if(
    config: IFMonteCarloConfig,
    ano_base: int,
    idade_titular_atual: int,
    idade_meta_if: int = 65,
) -> MonteCarloIFResult:
    """10 000 simulações log-normais vetorizadas → P10/P50/P90 + gate de cone."""
    pv, fv = float(config.patrimonio_investivel), float(config.meta_if)
    if fv <= 0 or pv < 0:
        return _resultado_sem_cone("meta_if inválida ou patrimônio negativo", idade_meta_if, config)
    core = _mc_core(pv, fv, config, idade_meta_if - idade_titular_atual)
    if core is None:
        return _resultado_sem_cone(
            "acumulação inicial — foco em consistência de aporte", idade_meta_if, config
        )
    return _build_mc_result(core, config, ano_base, idade_meta_if)
