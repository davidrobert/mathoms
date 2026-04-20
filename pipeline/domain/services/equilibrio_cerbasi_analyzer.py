"""EquilibrioCerbasiAnalyzer — equilíbrio presente vs futuro (Sessão A5c).

Extrai ``analyze_equilibrio_cerbasi`` (e5_analyze.py:2351) em domain service
puro. Calcula % de gastos em categorias "presente" vs "futuro" e classifica
o perfil (Investidor / Equilibrado / Endividado consciente / Gastador).

Categorias não-classificadas somam no "presente" (paridade com legado).

Função pura. Config tipada (R9/ISP) recebe categorias + escada de classificação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "."))
    except ValueError:
        return 0.0


# =============================================================================
# Defaults (paridade com legado)
# =============================================================================


_DEFAULT_PRESENTE = frozenset({
    "moradia", "alimentacao", "transporte", "saude", "lazer",
    "servicos_domesticos", "pets", "cuidados_pessoais",
    "assinaturas", "vestuario", "compras_online",
})

_DEFAULT_FUTURO = frozenset({
    "educacao", "investimentos", "previdencia", "financeiro",
    "reserva_desejos", "poupanca", "aportes",
})


@dataclass(frozen=True)
class ClassificacaoFaixa:
    minimo_futuro_pct: float
    label: str


_DEFAULT_CLASSIFICACAO = (
    ClassificacaoFaixa(30, "Investidor"),
    ClassificacaoFaixa(20, "Equilibrado"),
    ClassificacaoFaixa(10, "Endividado consciente"),
    ClassificacaoFaixa(0, "Gastador"),
)


# =============================================================================
# Config
# =============================================================================


@dataclass(frozen=True)
class EquilibrioCerbasiConfig:
    """Categorias e classificação. Source no legado:
    ``scoring.json::cerbasi.{categorias_presente, categorias_futuro, classificacao}``.
    """

    categorias_presente: frozenset[str] = _DEFAULT_PRESENTE
    categorias_futuro: frozenset[str] = _DEFAULT_FUTURO
    classificacao: tuple[ClassificacaoFaixa, ...] = _DEFAULT_CLASSIFICACAO

    @classmethod
    def from_scoring(cls, scoring: dict | None = None) -> "EquilibrioCerbasiConfig":
        cfg = (scoring or {}).get("cerbasi") or {}
        presente = cfg.get("categorias_presente")
        futuro = cfg.get("categorias_futuro")
        classif_raw = cfg.get("classificacao")

        classif: tuple[ClassificacaoFaixa, ...]
        if classif_raw:
            classif = tuple(
                ClassificacaoFaixa(
                    minimo_futuro_pct=_safe_float(f.get("minimo_futuro_pct", 0)),
                    label=str(f.get("label", "")),
                )
                for f in classif_raw
                if isinstance(f, dict)
            )
        else:
            classif = _DEFAULT_CLASSIFICACAO

        return cls(
            categorias_presente=(
                frozenset(str(c) for c in presente) if presente else _DEFAULT_PRESENTE
            ),
            categorias_futuro=(
                frozenset(str(c) for c in futuro) if futuro else _DEFAULT_FUTURO
            ),
            classificacao=classif,
        )


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class EquilibrioCerbasi:
    pct_presente: float
    pct_futuro: float
    classificacao: str
    presente: str = "Consolidação patrimonial"
    futuro: str = "Independência Financeira"

    def to_legacy_dict(self) -> dict:
        return {
            "pct_presente": self.pct_presente,
            "pct_futuro": self.pct_futuro,
            "classificacao": self.classificacao,
            "presente": self.presente,
            "futuro": self.futuro,
        }


# =============================================================================
# Service
# =============================================================================


class EquilibrioCerbasiAnalyzer:
    """Classifica o perfil financeiro presente-vs-futuro."""

    def __init__(self, config: EquilibrioCerbasiConfig | None = None) -> None:
        self._config = config or EquilibrioCerbasiConfig()

    def analyze(self, fluxo: dict[str, Any]) -> EquilibrioCerbasi:
        cfg = self._config
        despesas = (fluxo or {}).get("despesas_por_categoria", {}) or {}

        gasto_presente = 0.0
        gasto_futuro = 0.0
        gasto_nao_classificado = 0.0

        for cat, valor in despesas.items():
            v = _safe_float(valor)
            if cat in cfg.categorias_presente:
                gasto_presente += v
            elif cat in cfg.categorias_futuro:
                gasto_futuro += v
            else:
                gasto_nao_classificado += v

        # Paridade com legado: não-classificado soma no presente.
        gasto_presente += gasto_nao_classificado
        gasto_total = gasto_presente + gasto_futuro

        pct_presente = (
            round(gasto_presente / gasto_total * 100, 1) if gasto_total > 0 else 0.0
        )
        pct_futuro = (
            round(gasto_futuro / gasto_total * 100, 1) if gasto_total > 0 else 0.0
        )

        classificacao = self._classify(pct_futuro)

        return EquilibrioCerbasi(
            pct_presente=pct_presente,
            pct_futuro=pct_futuro,
            classificacao=classificacao,
        )

    def _classify(self, pct_futuro: float) -> str:
        for faixa in sorted(
            self._config.classificacao,
            key=lambda f: f.minimo_futuro_pct,
            reverse=True,
        ):
            if pct_futuro >= faixa.minimo_futuro_pct:
                return faixa.label
        return "Gastador"
