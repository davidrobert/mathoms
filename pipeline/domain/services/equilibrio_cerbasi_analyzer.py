"""EquilibrioCerbasiAnalyzer — equilíbrio presente vs futuro (Sessão A5c · ADR-306).

Extrai ``analyze_equilibrio_cerbasi`` (e5_analyze.py:2351) em domain service
puro. Classifica o perfil (Investidor / Equilibrado / Endividado consciente /
Gastador) sobre a **renda** da janela canônica 12m (ADR-306 §D5): poupança
realizada (``max(0, receita_recorrente − despesa_total)``) conta como "futuro";
base = gasto_presente + gasto_futuro + poupança (== renda no superávit,
== despesa total no déficit — pcts somam 100).

Categorias não-classificadas somam no "presente" (paridade com legado).
Sem ``janela_12m`` no fluxo, degrada para o período completo (rótulo ``full``).

Função pura. Config tipada (R9/ISP) recebe categorias + escada de classificação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

# Payload de fluxo enriquecido é JSON dinâmico — alias único (padrão ratios_calculator).
_FluxoPayload = dict[str, Any]

_ZERO = Decimal("0")


def _money(value: Any) -> Decimal:
    """Dinheiro em memória é Decimal (ADR-090); parse defensivo de payload."""
    return Decimal(str(_safe_float(value)))


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


_DEFAULT_PRESENTE = frozenset(
    {
        "moradia",
        "alimentacao",
        "transporte",
        "saude",
        "lazer",
        "servicos_domesticos",
        "pets",
        "cuidados_pessoais",
        "assinaturas",
        "vestuario",
        "compras_online",
    }
)

_DEFAULT_FUTURO = frozenset(
    {
        "educacao",
        "investimentos",
        "previdencia",
        "financeiro",
        "reserva_desejos",
        "poupanca",
        "aportes",
    }
)


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
            categorias_futuro=(frozenset(str(c) for c in futuro) if futuro else _DEFAULT_FUTURO),
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
    janela: str = "full"
    janela_meses: int = 0
    componentes: dict[str, float] = field(default_factory=dict)

    def to_legacy_dict(self) -> dict:
        return {
            "pct_presente": self.pct_presente,
            "pct_futuro": self.pct_futuro,
            "classificacao": self.classificacao,
            "presente": self.presente,
            "futuro": self.futuro,
            "janela": self.janela,
            "janela_meses": self.janela_meses,
            "componentes": {k: round(v, 2) for k, v in self.componentes.items()},
        }


# =============================================================================
# Service
# =============================================================================


class EquilibrioCerbasiAnalyzer:
    """Classifica o perfil financeiro presente-vs-futuro."""

    def __init__(self, config: EquilibrioCerbasiConfig | None = None) -> None:
        self._config = config or EquilibrioCerbasiConfig()

    def analyze(self, fluxo: _FluxoPayload) -> EquilibrioCerbasi:
        window = _resolve_cerbasi_window(fluxo)
        gasto_presente, gasto_futuro = self._split_gastos(window.despesas_por_categoria)

        # ADR-306 §D5: poupança realizada é alocação ao futuro. Residual
        # (fallback); aporte observado de primeira classe é follow-up.
        poupanca = float(max(_ZERO, window.receita_recorrente - window.despesa_janela))
        base = gasto_presente + gasto_futuro + poupanca

        pct_presente = round(gasto_presente / base * 100, 1) if base > 0 else 0.0
        pct_futuro = round((gasto_futuro + poupanca) / base * 100, 1) if base > 0 else 0.0

        return EquilibrioCerbasi(
            pct_presente=pct_presente,
            pct_futuro=pct_futuro,
            classificacao=self._classify(pct_futuro),
            janela=window.janela,
            janela_meses=window.janela_meses,
            componentes={
                "gasto_presente": gasto_presente,
                "gasto_futuro": gasto_futuro,
                "poupanca": poupanca,
                "base": base,
            },
        )

    def _split_gastos(self, despesas: dict[str, float]) -> tuple[float, float]:
        """Retorna ``(presente, futuro)``; não-classificado soma no presente (legado)."""
        cfg = self._config
        presente = 0.0
        futuro = 0.0
        for cat, valor in despesas.items():
            v = _safe_float(valor)
            if cat in cfg.categorias_futuro:
                futuro += v
            else:
                presente += v
        return presente, futuro

    def _classify(self, pct_futuro: float) -> str:
        for faixa in sorted(
            self._config.classificacao,
            key=lambda f: f.minimo_futuro_pct,
            reverse=True,
        ):
            if pct_futuro >= faixa.minimo_futuro_pct:
                return faixa.label
        return "Gastador"


@dataclass(frozen=True)
class _CerbasiWindow:
    despesas_por_categoria: dict[str, float]
    receita_recorrente: Decimal
    despesa_janela: Decimal
    janela: str
    janela_meses: int


def _resolve_cerbasi_window(fluxo: _FluxoPayload) -> _CerbasiWindow:
    """Prefere ``janela_12m`` (ADR-306); degrada para o período completo."""
    src = fluxo if isinstance(fluxo, dict) else {}
    j12m = src.get("janela_12m") or {}
    if isinstance(j12m, dict) and j12m.get("despesas_por_categoria"):
        return _CerbasiWindow(
            despesas_por_categoria=j12m["despesas_por_categoria"] or {},
            receita_recorrente=_money(j12m.get("receita_recorrente", 0)),
            despesa_janela=_money(j12m.get("despesa_total", 0)),
            janela="12m",
            janela_meses=int(_safe_float(j12m.get("n_meses", 0))),
        )
    return _CerbasiWindow(
        despesas_por_categoria=src.get("despesas_por_categoria", {}) or {},
        receita_recorrente=_money(src.get("receita_recorrente", 0)),
        despesa_janela=_money(src.get("despesa_total", 0)),
        janela="full",
        janela_meses=int(_safe_float(src.get("janela_meses", 0))),
    )
