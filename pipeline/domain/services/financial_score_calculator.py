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

# ADR-217 D3: score_version trava a fórmula no payload. Bump exige ADR sucessora.
# "1.0-legacy" = composição A6d.3.3 / scoring.json (5 componentes Cerbasi/Perini).
# Wave 1 (ADR-218 implementada) → "2.0" com reserva_emergencia.meses_cobertos_essencial.
SCORE_VERSION = "1.0-legacy"

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
        range_min=0,
        range_max=50,
        peso=2.0,
        nome_display="taxa_poupanca_recorrente",
    ),
    ScoreComponent(
        key="cobertura_despesas",
        range_min=3,
        range_max=24,
        peso=1.5,
        nome_display="cobertura_despesas",
    ),
    ScoreComponent(
        key="taxa_endividamento",
        range_min=5,
        range_max=50,
        peso=1.5,
        nome_display="taxa_endividamento",
        invertido=False,
    ),
    ScoreComponent(
        key="progresso_if",
        range_min=5,
        range_max=80,
        peso=2.0,
        nome_display="progresso_if",
    ),
    ScoreComponent(
        key="diversificacao",
        range_min=1,
        range_max=6,
        peso=1.0,
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
        componentes = self._build_componentes(ratios=ratios, patrimonio=patrimonio, goals=goals)
        total_peso = sum(c["peso"] for c in componentes)
        valor_score = (
            sum(c["nota"] * c["peso"] for c in componentes) / total_peso if total_peso > 0 else 0.0
        )
        valor_score = round(valor_score, 1)
        classificacao = self._classify(valor_score)

        breakdown = self._build_breakdown(componentes, weight_sum=total_peso)
        formula = self._build_formula(componentes)
        context = self._build_context(score=valor_score, classificacao=classificacao)
        conclusion = self._build_conclusion(classificacao, breakdown)

        return {
            "valor": valor_score,
            "max": 10,
            "classificacao": classificacao,
            "score_version": SCORE_VERSION,
            "componentes": componentes,
            "breakdown": breakdown,
            "formula": formula,
            "context": context,
            "conclusion": conclusion,
        }

    # -------------------------------------------------------------------------

    def _build_componentes(self, *, ratios: dict, patrimonio: dict, goals: dict) -> list[dict]:
        observed = self._observed_values(ratios=ratios, patrimonio=patrimonio, goals=goals)
        cfg = self._config
        return [
            self._grade(cfg.taxa_poupanca, observed["taxa_poup"]),
            self._grade(cfg.cobertura, observed["cobertura"]),
            self._grade(cfg.endividamento, observed["endiv"]),
            self._grade(cfg.progresso_if, observed["if_pct"]),
            self._grade(cfg.diversificacao, observed["num_cats"]),
        ]

    @staticmethod
    def _observed_values(*, ratios: dict, patrimonio: dict, goals: dict) -> dict[str, float]:
        composicao = patrimonio.get("composicao", []) or []
        return {
            "taxa_poup": safe_float(ratios.get("taxa_poupanca_recorrente_pct", 0)),
            "cobertura": safe_float(ratios.get("cobertura_despesas_meses", 0)),
            "endiv": safe_float(ratios.get("taxa_endividamento_pct", 0)),
            "if_pct": safe_float(goals.get("if_pct", 0)),
            "num_cats": sum(1 for c in composicao if safe_float(c.get("valor", 0)) > 0),
        }

    def _grade(self, comp: ScoreComponent, observed: float) -> dict:
        nota = self._interpolate_with_inversion(observed, comp)
        return self._componente_dict(comp, observed, nota)

    @staticmethod
    def _interpolate_with_inversion(val: float, comp: ScoreComponent) -> float:
        """Interpola respeitando ``invertido`` — swap de min/max."""
        if comp.invertido:
            return linear_interpolate(val, comp.range_max, comp.range_min)
        return linear_interpolate(val, comp.range_min, comp.range_max)

    @staticmethod
    def _componente_dict(comp: ScoreComponent, valor: float, nota: float) -> dict:
        # ADR-217 D2: status enum distingue 'emitted' (dado presente) de
        # 'absent_normalized' (dado faltando — peso vira penalidade natural).
        # Wave 0 trata todos como 'emitted' porque safe_float() coerce missing
        # para 0; wave futura (ADR-218) distingue ausência real via Optional.
        return {
            "code": comp.key,
            "nome": comp.nome_display,
            "valor": round(valor, 2),
            "peso": comp.peso,
            "nota": round(nota, 1),
            "status": "emitted",
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

    @staticmethod
    def _build_breakdown(componentes: list[dict], weight_sum: float) -> list[dict]:
        """Reformata `componentes` no shape consumido pelo `ScoreCard` (peso normalizado [0..1])."""
        if weight_sum <= 0:
            return []
        return [
            {
                "dimensao": c["nome"],
                "valor": c["nota"],
                "max": 10,
                "peso": round(c["peso"] / weight_sum, 4),
                "contribuicao": round(c["nota"] * c["peso"] / weight_sum, 2),
            }
            for c in componentes
        ]

    @staticmethod
    def _build_formula(componentes: list[dict]) -> str:
        """Fórmula textual exibida no rodapé do ScoreCard."""
        parts = " + ".join(f"{c['nome']}×{c['peso']:g}" for c in componentes)
        total = sum(c["peso"] for c in componentes)
        return f"Score = ({parts}) / {total:g}"

    @staticmethod
    def _build_context(score: float, classificacao: str) -> str:
        """Parágrafo `chart-context` — paridade com EXEMPLO_DE_RELATORIO.html L1809."""
        return (
            f"Indicador geral de saúde financeira da família, "
            f"com score de {score:.1f}/10 ({classificacao}). "
            "Reflete equilíbrio entre pontos fortes e oportunidades de melhoria."
        )

    @staticmethod
    def _build_conclusion(classificacao: str, breakdown: list[dict]) -> str:
        """Parágrafo `chart-conclusion` — top-2 drivers do breakdown."""
        if not breakdown:
            return f"A classificação '{classificacao}' reflete o conjunto dos componentes do score."
        drivers = _format_top_drivers(breakdown)
        return f"A classificação '{classificacao}' reflete {drivers}."


# =============================================================================
# Helpers
# =============================================================================


_DIMENSION_LABELS: dict[str, str] = {
    "taxa_poupanca_recorrente": "taxa de poupança recorrente",
    "cobertura_despesas": "cobertura de despesas pela reserva",
    "taxa_endividamento": "razão endividamento/patrimônio",
    "progresso_if": "progresso da meta IF",
    "diversificacao": "diversificação patrimonial",
}


def _humanize_dimension(key: str) -> str:
    """Mapeia chave técnica para frase curta legível na conclusão."""
    return _DIMENSION_LABELS.get(key, key.replace("_", " "))


def _format_top_drivers(breakdown: list[dict]) -> str:
    """Top-2 drivers do breakdown, com verbo de tom (`melhora`/`piora`)."""
    ordered = sorted(breakdown, key=lambda b: float(b.get("contribuicao") or 0), reverse=True)
    top2 = ordered[:2]
    labels = [_humanize_dimension(b["dimensao"]) for b in top2]
    notas = [float(b.get("valor") or 0) for b in top2]
    avg_nota = sum(notas) / len(notas) if notas else 0
    verbo = "melhora" if avg_nota >= 5 else "piora"
    if len(labels) >= 2:
        return f"{verbo} em {labels[0]} e {labels[1]}"
    if labels:
        return f"{verbo} em {labels[0]}"
    return "o conjunto dos componentes do score"
