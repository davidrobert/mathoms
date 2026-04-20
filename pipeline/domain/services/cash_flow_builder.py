"""CashFlowBuilder — agregação de receitas/despesas/fluxo mensal (Sessão A4a).

Decompõe em domain service puro:
- ``build_receitas_unified`` (e4_categorize.py:741)
- ``build_despesas_unified`` (e4_categorize.py:767)
- ``build_fluxo_mensal_detalhado`` (e4_categorize.py:793)

Recebe lista de :class:`ClassifiedTransaction`; retorna value objects
frozen (``ReceitasUnified``, ``DespesasUnified``, ``FluxoMensal``) com
``to_legacy_dict()`` compatível com o output E4 legado.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

from pipeline.domain.services.transaction_classifier import ClassifiedTransaction


_BRT = timezone(timedelta(hours=-3))


def _compute_periodo(transactions: Iterable[ClassifiedTransaction]) -> str:
    months = [t.data[:7] for t in transactions if t.data]
    if not months:
        return "N/D"
    return f"{min(months)} a {max(months)}"


# =============================================================================
# Value objects
# =============================================================================


@dataclass(frozen=True)
class ReceitasUnified:
    """Output ``receitas-4_unified.json`` (paridade com ``build_receitas_unified``)."""

    periodo: str
    categorias: tuple[str, ...]
    total_categorias: int
    total_transacoes: int
    totais_por_categoria: dict[str, float]
    total_geral: float
    dados: dict[str, list[dict]]
    consolidation_date: str

    def to_legacy_dict(self) -> dict:
        return {
            "consolidation_date": self.consolidation_date,
            "periodo": self.periodo,
            "categorias": list(self.categorias),
            "total_categorias": self.total_categorias,
            "total_transacoes": self.total_transacoes,
            "totais_por_categoria": dict(self.totais_por_categoria),
            "total_geral": self.total_geral,
            "dados": {cat: list(txs) for cat, txs in self.dados.items()},
        }


@dataclass(frozen=True)
class DespesasUnified:
    """Output ``despesas-4_unified.json`` (paridade com ``build_despesas_unified``)."""

    periodo: str
    categorias: tuple[str, ...]
    total_categorias: int
    total_transacoes: int
    totais_por_categoria: dict[str, float]
    total_geral: float
    dados: dict[str, list[dict]]
    consolidation_date: str

    def to_legacy_dict(self) -> dict:
        return {
            "consolidation_date": self.consolidation_date,
            "periodo": self.periodo,
            "categorias": list(self.categorias),
            "total_categorias": self.total_categorias,
            "total_transacoes": self.total_transacoes,
            "totais_por_categoria": dict(self.totais_por_categoria),
            "total_geral": self.total_geral,
            "dados": {cat: list(txs) for cat, txs in self.dados.items()},
        }


@dataclass(frozen=True)
class FluxoMensal:
    """Output ``fluxo_mensal_detalhado-4_unified.json`` (paridade com
    ``build_fluxo_mensal_detalhado``).
    """

    periodo: str
    meses_ordenados: tuple[str, ...]
    receitas: dict  # {"origens": [...], "por_mes": {...}}
    despesas: dict  # {"categorias": [...], "por_mes": {...}}

    def to_legacy_dict(self) -> dict:
        return {
            "periodo": self.periodo,
            "meses_ordenados": list(self.meses_ordenados),
            "receitas": {
                "origens": list(self.receitas.get("origens", [])),
                "por_mes": dict(self.receitas.get("por_mes", {})),
            },
            "despesas": {
                "categorias": list(self.despesas.get("categorias", [])),
                "por_mes": dict(self.despesas.get("por_mes", {})),
            },
        }


@dataclass(frozen=True)
class CashFlow:
    """Resultado agregado do ``CashFlowBuilder.build``."""

    receitas: ReceitasUnified
    despesas: DespesasUnified
    fluxo_mensal: FluxoMensal
    transferencias_count: int = 0


# =============================================================================
# Builder
# =============================================================================


class CashFlowBuilder:
    """Agrega :class:`ClassifiedTransaction` em :class:`CashFlow`.

    Stateless — sem config externa; a clock é injetável para testes determinísticos.
    """

    def __init__(self, *, now=None) -> None:
        self._now = now

    def _iso_now(self) -> str:
        return (self._now or datetime.now(_BRT)).isoformat()

    # -- API --

    def build(
        self, transactions: Iterable[ClassifiedTransaction]
    ) -> CashFlow:
        txs = list(transactions)
        receitas = [t for t in txs if t.kind == "receita"]
        despesas = [t for t in txs if t.kind == "despesa"]
        transferencias = [t for t in txs if t.kind == "transferencia"]

        return CashFlow(
            receitas=self.build_receitas_unified(receitas),
            despesas=self.build_despesas_unified(despesas),
            fluxo_mensal=self.build_fluxo_mensal(receitas, despesas),
            transferencias_count=len(transferencias),
        )

    def build_receitas_unified(
        self, receitas: list[ClassifiedTransaction]
    ) -> ReceitasUnified:
        """Paridade direta com ``build_receitas_unified`` do legado."""
        by_category: dict[str, list[dict]] = defaultdict(list)
        totais: dict[str, float] = defaultdict(float)

        for t in receitas:
            cat = t.categoria or ""
            by_category[cat].append(t.to_legacy_dict())
            totais[cat] += t.valor

        total_geral = sum(totais.values())

        return ReceitasUnified(
            periodo=_compute_periodo(receitas),
            categorias=tuple(sorted(by_category.keys())),
            total_categorias=len(by_category),
            total_transacoes=len(receitas),
            totais_por_categoria={k: v for k, v in totais.items()},
            total_geral=round(total_geral, 2),
            dados={
                cat: sorted(txs, key=lambda x: x.get("data", ""))
                for cat, txs in by_category.items()
            },
            consolidation_date=self._iso_now(),
        )

    def build_despesas_unified(
        self, despesas: list[ClassifiedTransaction]
    ) -> DespesasUnified:
        """Paridade direta com ``build_despesas_unified`` do legado."""
        by_category: dict[str, list[dict]] = defaultdict(list)
        totais: dict[str, float] = defaultdict(float)

        for t in despesas:
            cat = t.categoria or ""
            by_category[cat].append(t.to_legacy_dict())
            totais[cat] += t.valor

        total_geral = sum(totais.values())

        return DespesasUnified(
            periodo=_compute_periodo(despesas),
            categorias=tuple(sorted(by_category.keys())),
            total_categorias=len(by_category),
            total_transacoes=len(despesas),
            totais_por_categoria={k: v for k, v in totais.items()},
            total_geral=round(total_geral, 2),
            dados={
                cat: sorted(txs, key=lambda x: x.get("data", ""))
                for cat, txs in by_category.items()
            },
            consolidation_date=self._iso_now(),
        )

    def build_fluxo_mensal(
        self,
        receitas: list[ClassifiedTransaction],
        despesas: list[ClassifiedTransaction],
    ) -> FluxoMensal:
        """Paridade direta com ``build_fluxo_mensal_detalhado`` do legado."""
        all_tx = receitas + despesas
        months = sorted({t.data[:7] for t in all_tx if t.data})

        # Receitas por mês (por origem).
        origens: set[str] = set()
        receita_por_mes: dict[str, dict[str, float]] = {m: {} for m in months}
        for t in receitas:
            if not t.data:
                continue
            mes = t.data[:7]
            origem = t.origem or ""
            origens.add(origem)
            receita_por_mes[mes][origem] = (
                receita_por_mes[mes].get(origem, 0.0) + t.valor
            )
        # Fill zeros + _total.
        for m in months:
            for orig in origens:
                receita_por_mes[m].setdefault(orig, 0.0)
                receita_por_mes[m][orig] = round(receita_por_mes[m][orig], 2)
            receita_por_mes[m]["_total"] = round(
                sum(v for k, v in receita_por_mes[m].items() if k != "_total"),
                2,
            )

        # Despesas por mês (por categoria).
        categorias: set[str] = set()
        despesa_por_mes: dict[str, dict[str, float]] = {m: {} for m in months}
        for t in despesas:
            if not t.data:
                continue
            mes = t.data[:7]
            cat = t.categoria or ""
            categorias.add(cat)
            despesa_por_mes[mes][cat] = (
                despesa_por_mes[mes].get(cat, 0.0) + t.valor
            )
        for m in months:
            for c in categorias:
                despesa_por_mes[m].setdefault(c, 0.0)
                despesa_por_mes[m][c] = round(despesa_por_mes[m][c], 2)
            despesa_por_mes[m]["_total"] = round(
                sum(v for k, v in despesa_por_mes[m].items() if k != "_total"),
                2,
            )

        return FluxoMensal(
            periodo=_compute_periodo(all_tx),
            meses_ordenados=tuple(months),
            receitas={
                "origens": sorted(origens),
                "por_mes": receita_por_mes,
            },
            despesas={
                "categorias": sorted(categorias),
                "por_mes": despesa_por_mes,
            },
        )
