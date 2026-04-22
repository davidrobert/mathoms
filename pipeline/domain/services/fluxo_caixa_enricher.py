"""FluxoCaixaEnricher — enriquece dados de fluxo com one-time, janela 12m
e datasets Chart.js (Sessão A5c · Fase 8).

Extrai ``analyze_fluxo_caixa`` (e5_analyze.py:1050) em domain service puro.
Complementa o ``CashFlowBuilder`` (A4a) com métricas adicionais:

- Separação receita recorrente vs one-time (por categoria e palavras-chave).
- Período mensal + média mensal (receita_recorrente_mensal, despesa_mensal_media).
- Janela de 12 meses (rolling) — usada por ratios e score.
- Datasets Chart.js (receita_datasets, despesa_datasets) para frontend.

Input esperado: dicts ``receitas-4_unified``, ``despesas-4_unified``,
``fluxo_mensal_detalhado-4_unified`` (outputs do E4).

Função pura. Config tipada (R9/ISP).
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
# Config
# =============================================================================


_DEFAULT_ONE_TIME_CATEGORIES = frozenset(
    {
        "receita_venda_ativo",
        "receita_resgate",
        "receita_fgts",
        "receita_restituicao",
    }
)

_DEFAULT_ONE_TIME_KEYWORDS = (
    "venda",
    "resgate",
    "fgts",
    "restituicao",
    "restituição",
)

_DEFAULT_ONE_TIME_ORIGIN_NAMES = frozenset(
    {
        "Resgates",
        "Restituições",
        "Venda de Ativo",
        "FGTS",
    }
)


@dataclass(frozen=True)
class FluxoEnricherConfig:
    """Categorias e keywords para identificar receita one-time.

    Sources no legado:
    - ``one_time_categories`` ← ``categorization.json::one_time_income_categories``
    - ``one_time_keywords`` ← ``categorization.json::one_time_income_keywords``
    - ``one_time_origin_names`` ← hardcoded no legado (mapping de origens UI).
    - ``janela_meses`` ← hardcoded 12 no legado.
    """

    one_time_categories: frozenset[str] = _DEFAULT_ONE_TIME_CATEGORIES
    one_time_keywords: tuple[str, ...] = _DEFAULT_ONE_TIME_KEYWORDS
    one_time_origin_names: frozenset[str] = _DEFAULT_ONE_TIME_ORIGIN_NAMES
    janela_meses: int = 12

    @classmethod
    def from_categorization(cls, categorization: dict | None = None) -> "FluxoEnricherConfig":
        cat = categorization or {}
        cats_raw = cat.get("one_time_income_categories")
        kws_raw = cat.get("one_time_income_keywords")
        return cls(
            one_time_categories=(
                frozenset(str(c) for c in cats_raw) if cats_raw else _DEFAULT_ONE_TIME_CATEGORIES
            ),
            one_time_keywords=(
                tuple(str(k).lower() for k in kws_raw) if kws_raw else _DEFAULT_ONE_TIME_KEYWORDS
            ),
        )


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class Janela12m:
    periodo: str
    n_meses: int
    receita_total: float
    receita_recorrente: float
    receita_one_time: float
    receita_recorrente_mensal: float
    despesa_total: float
    despesa_mensal_media: float
    fluxo_liquido: float
    taxa_poupanca_recorrente: float
    taxa_poupanca_total: float

    def to_dict(self) -> dict:
        return {
            "periodo": self.periodo,
            "n_meses": self.n_meses,
            "receita_total": round(self.receita_total, 2),
            "receita_recorrente": round(self.receita_recorrente, 2),
            "receita_one_time": round(self.receita_one_time, 2),
            "receita_recorrente_mensal": round(self.receita_recorrente_mensal, 2),
            "despesa_total": round(self.despesa_total, 2),
            "despesa_mensal_media": round(self.despesa_mensal_media, 2),
            "fluxo_liquido": round(self.fluxo_liquido, 2),
            "taxa_poupanca_recorrente": round(self.taxa_poupanca_recorrente, 2),
            "taxa_poupanca_total": round(self.taxa_poupanca_total, 2),
        }


@dataclass(frozen=True)
class FluxoCaixaEnriched:
    receita_total: float
    receita_recorrente: float
    receita_one_time: float
    receita_recorrente_mensal: float
    despesa_total: float
    despesa_mensal_media: float
    fluxo_liquido: float
    por_fonte: dict[str, float]
    por_fonte_detalhado: dict[str, float]
    despesas_por_categoria: dict[str, float]
    tabela_receitas: tuple[dict, ...]
    chart_labels: tuple[str, ...]
    chart_receita_datasets: tuple[dict, ...]
    chart_despesa_datasets: tuple[dict, ...]
    chart_totais_receita: tuple[float, ...]
    chart_totais_despesa: tuple[float, ...]
    janela_12m: Janela12m

    def to_legacy_dict(self) -> dict:
        return {
            "receita_total": round(self.receita_total, 2),
            "receita_recorrente": round(self.receita_recorrente, 2),
            "receita_one_time": round(self.receita_one_time, 2),
            "receita_recorrente_mensal": round(self.receita_recorrente_mensal, 2),
            "despesa_total": round(self.despesa_total, 2),
            "despesa_mensal_media": round(self.despesa_mensal_media, 2),
            "fluxo_liquido": round(self.fluxo_liquido, 2),
            "por_fonte": {k: round(v, 2) for k, v in self.por_fonte.items()},
            "por_fonte_detalhado": {k: round(v, 2) for k, v in self.por_fonte_detalhado.items()},
            "despesas_por_categoria": {
                k: round(v, 2) for k, v in self.despesas_por_categoria.items()
            },
            "tabela_receitas": list(self.tabela_receitas),
            "receita_despesa_mensal_detalhado": {
                "labels": list(self.chart_labels),
                "receita_datasets": list(self.chart_receita_datasets),
                "despesa_datasets": list(self.chart_despesa_datasets),
                "totais_receita": [round(v, 2) for v in self.chart_totais_receita],
                "totais_despesa": [round(v, 2) for v in self.chart_totais_despesa],
            },
            "janela_12m": self.janela_12m.to_dict(),
        }


# =============================================================================
# Service
# =============================================================================


class FluxoCaixaEnricher:
    """Enriquece E4 (receitas/despesas/fluxo_mensal) com métricas derivadas."""

    def __init__(self, config: FluxoEnricherConfig | None = None) -> None:
        self._config = config or FluxoEnricherConfig()

    def enrich(
        self,
        receitas: dict[str, Any],
        despesas: dict[str, Any],
        fluxo_mensal: dict[str, Any],
    ) -> FluxoCaixaEnriched:
        receita_total = _safe_float((receitas or {}).get("total_geral", 0))
        despesa_total = _safe_float((despesas or {}).get("total_geral", 0))

        # Split one-time vs recorrente.
        receita_one_time, receita_recorrente = self._split_receita(receita_total, receitas)

        meses = list((fluxo_mensal or {}).get("meses_ordenados", []) or [])
        num_months = len(meses) or 1  # paridade com fallback do legado.

        receita_recorrente_mensal = receita_recorrente / num_months if num_months > 0 else 0.0
        despesa_mensal_media = despesa_total / num_months if num_months > 0 else 0.0
        fluxo_liquido = receita_total - despesa_total

        por_fonte = dict((receitas or {}).get("totais_por_categoria", {}) or {})
        despesas_por_categoria = dict((despesas or {}).get("totais_por_categoria", {}) or {})

        # Chart.js datasets.
        chart_data = self._build_chart_datasets(fluxo_mensal, meses)

        # Tabela de receitas (% do total_geral_por_fonte).
        tabela_receitas = self._build_tabela_receitas(por_fonte)

        # Janela 12m.
        janela_12m = self._compute_janela_12m(fluxo_mensal, meses)

        # por_fonte_detalhado (12m window).
        por_fonte_detalhado = self._compute_por_fonte_detalhado(fluxo_mensal, meses)

        return FluxoCaixaEnriched(
            receita_total=receita_total,
            receita_recorrente=receita_recorrente,
            receita_one_time=receita_one_time,
            receita_recorrente_mensal=receita_recorrente_mensal,
            despesa_total=despesa_total,
            despesa_mensal_media=despesa_mensal_media,
            fluxo_liquido=fluxo_liquido,
            por_fonte=por_fonte,
            por_fonte_detalhado=por_fonte_detalhado,
            despesas_por_categoria=despesas_por_categoria,
            tabela_receitas=tabela_receitas,
            chart_labels=chart_data["labels"],
            chart_receita_datasets=chart_data["receita_datasets"],
            chart_despesa_datasets=chart_data["despesa_datasets"],
            chart_totais_receita=chart_data["totais_receita"],
            chart_totais_despesa=chart_data["totais_despesa"],
            janela_12m=janela_12m,
        )

    # -- Helpers --

    def _split_receita(self, receita_total: float, receitas: dict) -> tuple[float, float]:
        cfg = self._config
        one_time = 0.0
        recorrente = receita_total
        dados = (receitas or {}).get("dados", {}) or {}
        for categoria, transacoes in dados.items():
            if categoria in cfg.one_time_categories:
                cat_total = sum(_safe_float(t.get("valor", 0)) for t in transacoes)
                one_time += cat_total
                recorrente -= cat_total
                continue
            for txn in transacoes:
                desc = str(txn.get("descricao", "")).lower()
                if any(kw in desc for kw in cfg.one_time_keywords):
                    val = _safe_float(txn.get("valor", 0))
                    one_time += val
                    recorrente -= val
        return one_time, recorrente

    def _build_tabela_receitas(self, por_fonte: dict[str, float]) -> tuple[dict, ...]:
        total = sum(v for v in por_fonte.values() if v > 0)
        items: list[dict] = []
        for cat, val in sorted(por_fonte.items(), key=lambda x: x[1], reverse=True):
            if val > 0:
                items.append(
                    {
                        "categoria": str(cat).replace("_", " ").title(),
                        "valor": round(val, 2),
                        "pct": round(val / total * 100, 2) if total > 0 else 0,
                    }
                )
        return tuple(items)

    def _build_chart_datasets(self, fluxo_mensal: dict, meses: list[str]) -> dict:
        receita_por_mes = (fluxo_mensal or {}).get("receitas", {}).get("por_mes", {}) or {}
        despesa_por_mes = (fluxo_mensal or {}).get("despesas", {}).get("por_mes", {}) or {}

        # labels "YY/MM" from "YYYY-MM".
        labels = tuple(f"{m[:4][-2:]}/{m[-2:]}" if len(m) >= 7 else m for m in meses)

        # Receita datasets por origem.
        receita_sources: set[str] = set()
        for mes_data in receita_por_mes.values():
            receita_sources.update(k for k in (mes_data or {}).keys() if k != "_total")

        receita_datasets: list[dict] = []
        for source in sorted(receita_sources):
            data = [
                _safe_float((receita_por_mes.get(mes, {}) or {}).get(source, 0)) for mes in meses
            ]
            if any(d > 0 for d in data):
                receita_datasets.append({"label": source, "data": data})

        # Despesa datasets por categoria.
        despesa_categories: set[str] = set()
        for mes_data in despesa_por_mes.values():
            despesa_categories.update(k for k in (mes_data or {}).keys() if k != "_total")

        despesa_datasets: list[dict] = []
        for cat in sorted(despesa_categories):
            data = [_safe_float((despesa_por_mes.get(mes, {}) or {}).get(cat, 0)) for mes in meses]
            if any(d > 0 for d in data):
                despesa_datasets.append(
                    {
                        "label": str(cat).replace("_", " ").title(),
                        "data": data,
                    }
                )

        totais_receita = tuple(
            _safe_float((receita_por_mes.get(mes, {}) or {}).get("_total", 0)) for mes in meses
        )
        totais_despesa = tuple(
            _safe_float((despesa_por_mes.get(mes, {}) or {}).get("_total", 0)) for mes in meses
        )

        return {
            "labels": labels,
            "receita_datasets": tuple(receita_datasets),
            "despesa_datasets": tuple(despesa_datasets),
            "totais_receita": totais_receita,
            "totais_despesa": totais_despesa,
        }

    def _compute_janela_12m(self, fluxo_mensal: dict, meses: list[str]) -> Janela12m:
        cfg = self._config
        n_janela = min(cfg.janela_meses, len(meses))
        meses_12m = meses[-n_janela:] if n_janela > 0 else []
        inicio = meses_12m[0] if meses_12m else ""
        fim = meses_12m[-1] if meses_12m else ""

        receita_por_mes = (fluxo_mensal or {}).get("receitas", {}).get("por_mes", {}) or {}
        despesa_por_mes = (fluxo_mensal or {}).get("despesas", {}).get("por_mes", {}) or {}

        receita_total = 0.0
        receita_recorrente = 0.0
        despesa_total = 0.0

        for mes in meses_12m:
            mes_rec = receita_por_mes.get(mes, {}) or {}
            for origem, valor in mes_rec.items():
                if origem == "_total":
                    continue
                v = _safe_float(valor)
                receita_total += v
                if origem not in cfg.one_time_origin_names and not any(
                    kw in origem.lower() for kw in cfg.one_time_keywords
                ):
                    receita_recorrente += v
            mes_desp = despesa_por_mes.get(mes, {}) or {}
            despesa_total += _safe_float(mes_desp.get("_total", 0))

        receita_one_time = receita_total - receita_recorrente
        receita_rec_mensal = receita_recorrente / n_janela if n_janela > 0 else 0.0
        despesa_mensal_media = despesa_total / n_janela if n_janela > 0 else 0.0
        fluxo_liquido = receita_total - despesa_total

        taxa_rec = (
            ((receita_recorrente - despesa_total) / receita_recorrente * 100)
            if receita_recorrente > 0
            else 0.0
        )
        taxa_tot = (
            ((receita_total - despesa_total) / receita_total * 100) if receita_total > 0 else 0.0
        )

        return Janela12m(
            periodo=f"{inicio} a {fim}",
            n_meses=n_janela,
            receita_total=receita_total,
            receita_recorrente=receita_recorrente,
            receita_one_time=receita_one_time,
            receita_recorrente_mensal=receita_rec_mensal,
            despesa_total=despesa_total,
            despesa_mensal_media=despesa_mensal_media,
            fluxo_liquido=fluxo_liquido,
            taxa_poupanca_recorrente=taxa_rec,
            taxa_poupanca_total=taxa_tot,
        )

    def _compute_por_fonte_detalhado(
        self, fluxo_mensal: dict, meses: list[str]
    ) -> dict[str, float]:
        cfg = self._config
        n_janela = min(cfg.janela_meses, len(meses))
        meses_12m = meses[-n_janela:] if n_janela > 0 else []

        receita_por_mes = (fluxo_mensal or {}).get("receitas", {}).get("por_mes", {}) or {}
        totals: dict[str, float] = {}
        for mes in meses_12m:
            mes_rec = receita_por_mes.get(mes, {}) or {}
            for origem, valor in mes_rec.items():
                if origem == "_total":
                    continue
                v = _safe_float(valor)
                if v > 0:
                    totals[origem] = totals.get(origem, 0.0) + v
        return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))
