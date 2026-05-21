"""Leitor de renda tributável PF (base PGBL canônica) — ADR-236 §D2 · ADR-157.

Agrega `rendimentos_pj[].rendimentos_tributaveis_brl + rendimentos_pf[].valor_brl`
do artifact `extract_irpf_full`. Exclui 13º (tributação exclusiva), lucros
isentos e exterior — V1 cobre só "ficha Rendimentos Tributáveis". Money em
Decimal string (ADR-090).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pipeline.domain.models.transaction import Money


@dataclass(frozen=True)
class RendaTributavelPF:
    # Decomposição da renda tributável PF anual (PGBL base canônica).
    # `fontes_pj`/`fontes_pf`: contagem de itens — gate UI "renda PF não
    # detectada" quando ambos == 0 (ADR-236 §R2).

    total: Money
    rendimentos_pj_total: Money
    rendimentos_pf_total: Money
    fontes_pj: int
    fontes_pf: int

    @property
    def has_renda_tributavel(self) -> bool:
        return self.fontes_pj + self.fontes_pf > 0


def extract_renda_tributavel_pf(irpf_artifact: dict[str, Any] | None) -> RendaTributavelPF:
    """Agrega base PGBL a partir do artifact `extract_irpf_full` (ADR-236 §D2)."""
    if not isinstance(irpf_artifact, dict):
        return _empty()
    pj_items = irpf_artifact.get("rendimentos_pj") or []
    pf_items = irpf_artifact.get("rendimentos_pf") or []
    pj_total = _sum_money(pj_items, field="rendimentos_tributaveis_brl")
    pf_total = _sum_money(pf_items, field="valor_brl")
    return RendaTributavelPF(
        total=pj_total + pf_total,
        rendimentos_pj_total=pj_total,
        rendimentos_pf_total=pf_total,
        fontes_pj=_count_valid(pj_items, field="rendimentos_tributaveis_brl"),
        fontes_pf=_count_valid(pf_items, field="valor_brl"),
    )


def _sum_money(items: list[Any], *, field: str) -> Money:
    total = Money.zero("BRL")
    for it in items:
        if not isinstance(it, dict):
            continue
        raw = it.get(field)
        amount = _parse_decimal_strict(raw)
        if amount is None:
            continue
        total = total + Money.brl(amount)
    return total


def _count_valid(items: list[Any], *, field: str) -> int:
    return sum(
        1
        for it in items
        if isinstance(it, dict) and _parse_decimal_strict(it.get(field)) is not None
    )


def _parse_decimal_strict(raw: Any) -> Decimal | None:
    """Aceita Decimal string (ADR-090) ou int; rejeita float/None/malformado → ``None``."""
    if raw is None or isinstance(raw, (bool, float)):
        return None
    if isinstance(raw, str):
        try:
            return Decimal(raw)
        except (ValueError, TypeError):
            return None
    if isinstance(raw, (int, Decimal)):
        return Decimal(raw)
    return None


def _empty() -> RendaTributavelPF:
    zero = Money.zero("BRL")
    return RendaTributavelPF(
        total=zero,
        rendimentos_pj_total=zero,
        rendimentos_pf_total=zero,
        fontes_pj=0,
        fontes_pf=0,
    )
