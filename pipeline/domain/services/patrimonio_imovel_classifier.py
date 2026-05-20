"""Splitters de imóveis por classification (ADR-215 §1 + §6 · ADR-227 §D3)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.patrimonio_types import (
    RealEstateValuationContext,
    imovel_property_id,
    imovel_valor,
)
from pipeline.domain.services.real_estate_valuation_resolver import resolve_valor_efetivo

# ADR-215 P3: classification de override DB-first (ADR-215 §1).
CLASSIFICATION_RESIDENCIA_PRINCIPAL = "residencia_principal"
CLASSIFICATION_USO_PESSOAL = "uso_pessoal"
CLASSIFICATION_LOCADO = "locado"
CLASSIFICATION_COMERCIAL = "comercial"
CLASSIFICATION_ESPECULACAO = "especulacao"
CLASSIFICATION_DESCONHECIDO = "desconhecido"

# ADR-142 §Decisão + ADR-215 §6: classifications que produzem fluxo de caixa
# (entram em ``investivel_efetivo`` quando ``include_real_estate_in_if=True``).
# `uso_pessoal | especulacao | desconhecido` nunca entram — Perini/Cerbasi
# tratam patrimônio improdutivo como capital de uso, fora do múltiplo de IF.
_CLASSIFICATIONS_GERADORAS = frozenset({CLASSIFICATION_LOCADO, CLASSIFICATION_COMERCIAL})


def split_imoveis_with_overrides(
    *,
    titular_bens: dict,
    conjuge_bens: dict,
    overrides_by_property_id: dict[str, str],
) -> tuple[float, float]:
    """Separa cat_1 (residencia_principal) de demais imóveis (ADR-215 §1)."""
    residencia = 0.0
    imoveis_outros = 0.0
    for im in (titular_bens.get("imoveis") or []) + (conjuge_bens.get("imoveis") or []):
        pid = imovel_property_id(im)
        if pid and overrides_by_property_id.get(pid) == CLASSIFICATION_RESIDENCIA_PRINCIPAL:
            residencia += imovel_valor(im)
        else:
            imoveis_outros += imovel_valor(im)
    return residencia, imoveis_outros


def split_imoveis_geradores_vs_nao_geradores(
    *,
    titular_bens: dict,
    conjuge_bens: dict,
    overrides_by_property_id: dict[str, str],
) -> tuple[float, float]:
    """Separa cat_2 em geradores (locado/comercial) vs não-geradores (ADR-215 §6)."""
    geradores = 0.0
    nao_geradores = 0.0
    for im in (titular_bens.get("imoveis") or []) + (conjuge_bens.get("imoveis") or []):
        pid = imovel_property_id(im)
        cls = overrides_by_property_id.get(pid) if pid else None
        if cls == CLASSIFICATION_RESIDENCIA_PRINCIPAL:
            continue  # cat_1, fora de cat_2
        if cls in _CLASSIFICATIONS_GERADORAS:
            geradores += imovel_valor(im)
        else:
            nao_geradores += imovel_valor(im)
    return geradores, nao_geradores


def sum_imoveis_geradores_liquidos(
    imoveis: list[dict],
    overrides: dict[str, str],
    valuation_context: RealEstateValuationContext,
) -> Decimal:
    """Σ max(0, valor_efetivo − saldo_devedor) por imóvel gerador (ADR-227 §D3)."""
    total = Decimal("0")
    for im in imoveis:
        pid = imovel_property_id(im)
        if overrides.get(pid) not in _CLASSIFICATIONS_GERADORAS:
            continue
        valor_irpf = Decimal(str(imovel_valor(im)))
        valor_efetivo, _, _ = resolve_valor_efetivo(pid or "", valor_irpf, valuation_context)
        saldo = valuation_context.debts_by_property.get(pid or "", Decimal("0"))
        total += max(Decimal("0"), valor_efetivo - saldo)
    return total


__all__ = [
    "CLASSIFICATION_RESIDENCIA_PRINCIPAL",
    "CLASSIFICATION_USO_PESSOAL",
    "CLASSIFICATION_LOCADO",
    "CLASSIFICATION_COMERCIAL",
    "CLASSIFICATION_ESPECULACAO",
    "CLASSIFICATION_DESCONHECIDO",
    "split_imoveis_with_overrides",
    "split_imoveis_geradores_vs_nao_geradores",
    "sum_imoveis_geradores_liquidos",
]
