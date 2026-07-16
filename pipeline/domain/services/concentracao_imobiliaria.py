"""Concentração imobiliária canônica — base carteira (C11-Fase2 · [[ADR-340]]).

Fórmula ÚNICA (SSOT de definição): imóveis de renda (cat_2) sobre a **carteira
produtiva** (investível financeiro + cat_2, FIXA — toggle-independente). Mede
quanto do capital produtivo está travado em imóvel ilíquido; residência e
veículos ficam **fora** do denominador (não são carteira). Numerador cat_2
completo — imóvel vago/especulação é ainda mais ilíquido, conta no risco.

Chamada por ``RatiosCalculator`` (E5, emite ``ratios.concentracao_imobiliaria``)
e pela integração real_estate (E5.N, alimenta ``concentracao_pct`` + alertas).
Mesmos inputs (dict ``patrimonio``) → mesmo resultado; zero drift cross-superfície.
"""

from __future__ import annotations

from typing import Any, Mapping


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def compute_concentracao_imobiliaria_pct(patrimonio: Mapping[str, Any]) -> float:
    """``cat_2 / (investivel_financeiro + cat_2) × 100`` (0 quando carteira vazia)."""
    cat2 = _num(patrimonio.get("imoveis_investimento"))
    carteira = _num(patrimonio.get("investivel_financeiro")) + cat2
    return round(cat2 / carteira * 100.0, 2) if carteira > 0 else 0.0
