"""``FinancialScoreCalculator`` — score financeiro composto 0-10 (A6d.3.3 — ADR-100).

Substitui ``scripts/e5_analyze.calculate_score`` por serviço puro.

**Componentes** (configuráveis via ``config/scoring.json`` → ``score_componentes``):

1. ``taxa_poupanca_recorrente`` — % de sobra mensal recorrente.
2. ``cobertura_despesas`` — meses cobertos pela reserva líquida.
3. ``taxa_endividamento`` — % dívidas/patrimônio (**invertido**: maior = pior).
4. ``progresso_if`` — % da meta de independência financeira.
5. ``diversificacao`` — número de categorias com valor > 0 na composição.

Cada componente é interpolado linearmente em [range_min, range_max] → [0, 10].
A média ponderada pelos pesos produz o score final (arredondado a 1 casa).

**Classificação** por bandas em ``score_classificacao``, com fallback legado
(Crítico/Atenção/Regular/Bom/Excelente a cada 2 pontos).
"""

from __future__ import annotations

from dataclasses import dataclass

from pipeline.domain.services.patrimonio_types import safe_float


# =============================================================================
# Utilities
# =============================================================================


def linear_interpolate(val: float, min_val: float, max_val: float) -> float:
    """Mapeia ``val`` ∈ [min_val, max_val] para [0, 10] (clamped)."""
    if max_val == min_val:
        return 0.0
    score = (val - min_val) / (max_val - min_val) * 10.0
    return max(0.0, min(10.0, score))


# =============================================================================
# Config value objects
# =============================================================================


@dataclass(frozen=True)
class ScoreComponent:
    """Definição de um componente do score."""

    key: str
    range_min: float
    range_max: float
    peso: float
    nome_display: str
    invertido: bool = False
    """Quando ``True``, valores altos produzem notas baixas (swap min/max)."""


@dataclass(frozen=True)
class ScoreClassificacao:
    """Faixa de classificação (min ≤ score < max)."""

    min: float
    max: float
    label: str


# Componentes default — paridade com o legado (scoring.json quando ausente)
_DEFAULT_COMPONENTS: tuple[ScoreComponent, ...] = (
    ScoreComponent(
        key="taxa_poupanca_recorrente",
        range_min=0, range_max=50, peso=2.0,
        nome_display="taxa_poupanca_recorrente",
    ),
    ScoreComponent(
        key="cobertura_despesas",
        range_min=3, range_max=24, peso=1.5,
        nome_display="cobertura_despesas",
    ),
    ScoreComponent(
        key="taxa_endividamento",
        range_min=5, range_max=50, peso=1.5,
        nome_display="taxa_endividamento", invertido=False,
    ),
    ScoreComponent(
        key="progresso_if",
        range_min=5, range_max=80, peso=2.0,
        nome_display="progresso_if",
    ),
    ScoreComponent(
        key="diversificacao",
        range_min=1, range_max=6, peso=1.0,
        nome_display="diversificacao",
    ),
)


@dataclass(frozen=True)
class FinancialScoreConfig:
    """Config completa do :class:`FinancialScoreCalculator`."""

    taxa_poupanca: ScoreComponent
    cobertura: ScoreComponent
    endividamento: ScoreComponent
    progresso_if: ScoreComponent
    diversificacao: ScoreComponent
    classificacao: tuple[ScoreClassificacao, ...] = ()

    @classmethod
    def default(cls) -> "FinancialScoreConfig":
        """Config com os defaults do legado."""
        return cls(
            taxa_poupanca=_DEFAULT_COMPONENTS[0],
            cobertura=_DEFAULT_COMPONENTS[1],
            endividamento=_DEFAULT_COMPONENTS[2],
            progresso_if=_DEFAULT_COMPONENTS[3],
            diversificacao=_DEFAULT_COMPONENTS[4],
            classificacao=(),
        )

    @classmethod
    def from_scoring_json(cls, scoring: dict) -> "FinancialScoreConfig":
        """Constrói config a partir de ``config/scoring.json``.

        Aceita ``score_componentes`` com override parcial (merge sobre defaults)
        e ``score_classificacao`` como lista de bandas.
        """
        cfg = scoring.get("score_componentes", {}) or {}

        def _component(default: ScoreComponent) -> ScoreComponent:
            overrides = cfg.get(default.key, {}) or {}
            return ScoreComponent(
                key=default.key,
                range_min=safe_float(overrides.get("range_min", default.range_min)),
                range_max=safe_float(overrides.get("range_max", default.range_max)),
                peso=safe_float(overrides.get("peso", default.peso)),
                nome_display=str(overrides.get("nome_display", default.nome_display)),
                invertido=bool(overrides.get("invertido", default.invertido)),
            )

        classif_raw = scoring.get("score_classificacao", []) or []
        classif = tuple(
            ScoreClassificacao(
                min=safe_float(f.get("min", 0)),
                max=safe_float(f.get("max", 10)),
                label=str(f.get("label", "")),
            )
            for f in classif_raw
        )

        return cls(
            taxa_poupanca=_component(_DEFAULT_COMPONENTS[0]),
            cobertura=_component(_DEFAULT_COMPONENTS[1]),
            endividamento=_component(_DEFAULT_COMPONENTS[2]),
            progresso_if=_component(_DEFAULT_COMPONENTS[3]),
            diversificacao=_component(_DEFAULT_COMPONENTS[4]),
            classificacao=classif,
        )


# =============================================================================
# Calculator
# =============================================================================


class FinancialScoreCalculator:
    """Score financeiro 0-10 composto de 5 componentes ponderados.

    Uso::

        config = FinancialScoreConfig.from_scoring_json(scoring)
        calc = FinancialScoreCalculator(config)
        report = calc.calculate(ratios=..., patrimonio=..., goals=..., fluxo=...)
    """

    def __init__(self, config: FinancialScoreConfig) -> None:
        self._config = config

    def calculate(
        self,
        *,
        ratios: dict,
        patrimonio: dict,
        goals: dict,
        fluxo: dict | None = None,  # kept for signature parity; not used
    ) -> dict:
        """Produz dict paridade com ``calculate_score`` legado.

        ``fluxo`` permanece na assinatura por compat com o legado mas não é
        consumido — o score depende só de ``ratios`` + ``goals`` + ``patrimonio``.
        """
        del fluxo  # parity-only
        cfg = self._config

        taxa_poup = safe_float(ratios.get("taxa_poupanca_recorrente_pct", 0))
        cobertura = safe_float(ratios.get("cobertura_despesas_meses", 0))
        endiv = safe_float(ratios.get("taxa_endividamento_pct", 0))
        if_pct = safe_float(goals.get("if_pct", 0))

        composicao = patrimonio.get("composicao", []) or []
        num_cats = sum(1 for c in composicao if safe_float(c.get("valor", 0)) > 0)

        score_poup = linear_interpolate(
            taxa_poup, cfg.taxa_poupanca.range_min, cfg.taxa_poupanca.range_max
        )
        score_cobertura = linear_interpolate(
            cobertura, cfg.cobertura.range_min, cfg.cobertura.range_max
        )
        score_endiv = self._interpolate_with_inversion(endiv, cfg.endividamento)
        score_if = linear_interpolate(
            if_pct, cfg.progresso_if.range_min, cfg.progresso_if.range_max
        )
        score_diversif = linear_interpolate(
            num_cats, cfg.diversificacao.range_min, cfg.diversificacao.range_max
        )

        componentes = [
            self._componente_dict(cfg.taxa_poupanca, taxa_poup, score_poup),
            self._componente_dict(cfg.cobertura, cobertura, score_cobertura),
            self._componente_dict(cfg.endividamento, endiv, score_endiv),
            self._componente_dict(cfg.progresso_if, if_pct, score_if),
            self._componente_dict(cfg.diversificacao, num_cats, score_diversif),
        ]

        total_peso = sum(c["peso"] for c in componentes)
        valor_score = (
            sum(c["nota"] * c["peso"] for c in componentes) / total_peso
            if total_peso > 0
            else 0.0
        )
        valor_score = round(valor_score, 1)

        return {
            "valor": valor_score,
            "max": 10,
            "classificacao": self._classify(valor_score),
            "componentes": componentes,
        }

    # -------------------------------------------------------------------------

    @staticmethod
    def _interpolate_with_inversion(val: float, comp: ScoreComponent) -> float:
        """Interpola respeitando ``invertido`` — swap de min/max."""
        if comp.invertido:
            return linear_interpolate(val, comp.range_max, comp.range_min)
        return linear_interpolate(val, comp.range_min, comp.range_max)

    @staticmethod
    def _componente_dict(comp: ScoreComponent, valor: float, nota: float) -> dict:
        return {
            "nome": comp.nome_display,
            "valor": round(valor, 2),
            "peso": comp.peso,
            "nota": round(nota, 1),
        }

    def _classify(self, valor_score: float) -> str:
        """Classifica via bandas configuradas ou fallback legado."""
        # Edge: score == 10 → última banda
        if valor_score >= 10 and self._config.classificacao:
            return self._config.classificacao[-1].label

        for faixa in self._config.classificacao:
            if faixa.min <= valor_score < faixa.max:
                return faixa.label

        # Fallback legado (sem bandas configuradas ou nenhuma casou)
        return self._fallback_label(valor_score)

    @staticmethod
    def _fallback_label(valor_score: float) -> str:
        if valor_score < 2:
            return "Crítico"
        if valor_score < 4:
            return "Atenção"
        if valor_score < 6:
            return "Regular"
        if valor_score < 8:
            return "Bom"
        return "Excelente"
