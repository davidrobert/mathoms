"""CashFlowBuilder — agregação de receitas/despesas/fluxo mensal (Sessão A4a).

Decompõe em domain service puro:
- ``build_receitas_unified`` (e4_categorize.py:741)
- ``build_despesas_unified`` (e4_categorize.py:767)
- ``build_fluxo_mensal_detalhado`` (e4_categorize.py:793)

Recebe lista de :class:`ClassifiedTransaction`; retorna value objects
frozen (``ReceitasUnified``, ``DespesasUnified``, ``FluxoMensal``) com
``to_legacy_dict()`` compatível com o output E4 legado.

ADR-255 (Camada A): aplica dedup cross-document por hash determinístico K4
antes de agregar — defesa em profundidade. Quando ADR-255 PR2 propagar
``transaction_hash`` desde E3, o builder prefere o campo da tx; até lá,
computa inline com :func:`compute_transaction_hash`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

from pipeline.domain.services._tx_identity import (
    build_hash_inputs,
    cents_int,
    compute_identity_hash,
    normalize_banco,
    normalize_descricao,
    normalize_tipo_conta,
    normalize_titular,
)
from pipeline.domain.services.transaction_classifier import ClassifiedTransaction

_BRT = timezone(timedelta(hours=-3))

# ADR-255 — limiar de materialidade acima do qual colisão vira `needs_review`
# em vez de dedup silente. Valor em centavos.
_NEEDS_REVIEW_THRESHOLD_CENTS = 10_000 * 100


def _compute_periodo(transactions: Iterable[ClassifiedTransaction]) -> str:
    months = [t.data[:7] for t in transactions if t.data]
    if not months:
        return "N/D"
    return f"{min(months)} a {max(months)}"


# =============================================================================
# Dedup cross-document (ADR-255 Camada A)
# =============================================================================


@dataclass(frozen=True)
class DedupReviewEntry:
    """Colisão materialmente significativa que exige confirmação humana (ADR-255)."""

    transaction_hash: str
    data: str
    banco_norm: str
    titular_norm: str
    tipo_conta_norm: str
    valor_cents: int
    reason: str  # "material_value" | "missing_tipo_conta"
    collision_count: int  # quantas duplicatas foram colapsadas (≥ 1)


@dataclass(frozen=True)
class DedupReport:
    """Telemetria do dedup K4 aplicado em :meth:`CashFlowBuilder.build`."""

    collapsed_count: int  # total de duplicatas removidas (silentes + review)
    review_entries: tuple[DedupReviewEntry, ...] = ()

    @property
    def review_count(self) -> int:
        return len(self.review_entries)

    def to_log_dict(self) -> dict:
        """Resumo para log estruturado (sem PII — sem descrição/valor exato)."""
        return {
            "dups_collapsed": self.collapsed_count,
            "dups_review": self.review_count,
            "sample_hashes": [e.transaction_hash for e in self.review_entries[:5]],
        }


def _tx_hash(tx: ClassifiedTransaction, *, natural_key_v2: bool = False) -> str:
    """Prefere ``tx.transaction_hash`` (PR2); fallback computed (PR1, v1/v2 por ADR-287)."""
    explicit = getattr(tx, "transaction_hash", None)
    if explicit:
        return explicit
    inputs = build_hash_inputs(
        tx.data, tx.banco, tx.titular, tx.tipo_conta, tx.valor, tx.moeda, tx.descricao, tipo=tx.tipo
    )
    return compute_identity_hash(inputs, valor=tx.valor, natural_key_v2=natural_key_v2)


def _classify_review_reason(
    incoming: ClassifiedTransaction, first: ClassifiedTransaction
) -> str | None:
    """Retorna razão de review ou ``None`` se dedup pode ser silente."""
    max_cents = max(cents_int(abs(incoming.valor)), cents_int(abs(first.valor)))
    if max_cents >= _NEEDS_REVIEW_THRESHOLD_CENTS:
        return "material_value"
    if not (incoming.tipo_conta or "").strip() or not (first.tipo_conta or "").strip():
        return "missing_tipo_conta"
    return None


def _make_review_entry(
    tx_hash: str, tx: ClassifiedTransaction, reason: str, collision_count: int
) -> DedupReviewEntry:
    return DedupReviewEntry(
        transaction_hash=tx_hash,
        data=tx.data or "",
        banco_norm=normalize_banco(tx.banco),
        titular_norm=normalize_titular(tx.titular),
        tipo_conta_norm=normalize_tipo_conta(tx.tipo_conta),
        valor_cents=cents_int(abs(tx.valor)),
        reason=reason,
        collision_count=collision_count,
    )


def _try_dedup_one(
    tx: ClassifiedTransaction,
    seen: dict[str, ClassifiedTransaction],
    collisions: dict[str, int],
    reasons: dict[str, str],
    *,
    natural_key_v2: bool = False,
) -> None:
    """Atualiza state in-place com 1 transação (primeira vence)."""
    h = _tx_hash(tx, natural_key_v2=natural_key_v2)
    if h not in seen:
        seen[h] = tx
        return
    collisions[h] += 1
    if h in reasons:
        return
    reason = _classify_review_reason(tx, seen[h])
    if reason is not None:
        reasons[h] = reason


def _dedup_transactions(
    transactions: list[ClassifiedTransaction],
    *,
    natural_key_v2: bool = False,
) -> tuple[list[ClassifiedTransaction], DedupReport]:
    """Dedup K4 dentro de 1 kind (caller separa receita/despesa/transferencia)."""
    seen: dict[str, ClassifiedTransaction] = {}
    collisions: dict[str, int] = defaultdict(int)
    reasons: dict[str, str] = {}
    for tx in transactions:
        _try_dedup_one(tx, seen, collisions, reasons, natural_key_v2=natural_key_v2)
    entries = tuple(
        _make_review_entry(h, seen[h], reasons[h], collisions[h]) for h in sorted(reasons)
    )
    return list(seen.values()), DedupReport(
        collapsed_count=sum(collisions.values()), review_entries=entries
    )


def _merge_dedup_reports(*reports: DedupReport) -> DedupReport:
    """Combina relatórios de dedup independentes (kinds separadas)."""
    collapsed = sum(r.collapsed_count for r in reports)
    entries: list[DedupReviewEntry] = []
    for r in reports:
        entries.extend(r.review_entries)
    entries.sort(key=lambda e: e.transaction_hash)
    return DedupReport(collapsed_count=collapsed, review_entries=tuple(entries))


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
    # ADR-255 — telemetria do dedup cross-document; default vazio preserva
    # construtores em call-sites legados de teste que instanciam CashFlow
    # diretamente sem chamar build().
    dedup_report: DedupReport = field(default_factory=lambda: DedupReport(collapsed_count=0))


# =============================================================================
# Builder
# =============================================================================


class CashFlowBuilder:
    """Agrega :class:`ClassifiedTransaction` em :class:`CashFlow`.

    Stateless — sem config externa; a clock é injetável para testes determinísticos.
    """

    def __init__(self, *, now=None, dedup_natural_key_v2: bool = False) -> None:
        self._now = now
        # ADR-287 (A25.l2) — fallback de hash no dedup usa v2 quando o flag
        # do workspace está ligado; off preserva o shim v1 (zero-behavior).
        self._dedup_natural_key_v2 = dedup_natural_key_v2

    def _iso_now(self) -> str:
        return (self._now or datetime.now(_BRT)).isoformat()

    # -- API --

    def build(self, transactions: Iterable[ClassifiedTransaction]) -> CashFlow:
        # ADR-255 Camada A — dedup K4 por kind (sinal em ``kind``, não em valor).
        txs = list(transactions)
        by_kind = {
            k: _dedup_transactions(
                [t for t in txs if t.kind == k],
                natural_key_v2=self._dedup_natural_key_v2,
            )
            for k in ("receita", "despesa", "transferencia")
        }
        receitas, rep_r = by_kind["receita"]
        despesas, rep_d = by_kind["despesa"]
        transferencias, rep_t = by_kind["transferencia"]
        return CashFlow(
            receitas=self.build_receitas_unified(receitas),
            despesas=self.build_despesas_unified(despesas),
            fluxo_mensal=self.build_fluxo_mensal(receitas, despesas),
            transferencias_count=len(transferencias),
            dedup_report=_merge_dedup_reports(rep_r, rep_d, rep_t),
        )

    def build_receitas_unified(self, receitas: list[ClassifiedTransaction]) -> ReceitasUnified:
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

    def build_despesas_unified(self, despesas: list[ClassifiedTransaction]) -> DespesasUnified:
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
            receita_por_mes[mes][origem] = receita_por_mes[mes].get(origem, 0.0) + t.valor
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
            despesa_por_mes[mes][cat] = despesa_por_mes[mes].get(cat, 0.0) + t.valor
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
