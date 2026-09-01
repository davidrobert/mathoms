"""Concentração imobiliária canônica base carteira (C11-Fase2 · [[ADR-340]] · numerador por [[ADR-420]] §D1): fórmula ÚNICA (SSOT) = imóveis REBALANCEÁVEIS sobre a carteira produtiva (investível financeiro + os mesmos imóveis, FIXA/toggle-independente); residência/veículos fora do denominador (não são carteira); `uso_pessoal` e `nu_proprietario` fora do numerador porque nenhuma prescrição de rebalanceamento os alcança — o ativo não some, vive em `ratios.imobilizacao_patrimonial_pct` (§D3). Chamada por ``RatiosCalculator`` (E5) e pela integração real_estate (E5.N) com os mesmos inputs → zero drift cross-superfície."""

from __future__ import annotations

from typing import Any, Mapping

# [[ADR-420]] §D5 — a chave de `patrimonio` que o numerador LÊ, exportada para quem
# publica a declaração ao lado do número. Repetir o literal em `ratios` criaria a
# segunda fonte que o C14 da [[A40.l80]] pegou no denominador (declarada ≠ usada):
# aqui a declaração e a leitura saem da MESMA constante, então não podem divergir.
CHAVE_DO_NUMERADOR = "imoveis_alocacao"


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def compute_concentracao_imobiliaria_pct(patrimonio: Mapping[str, Any]) -> float:
    """``alocacao / (investivel_financeiro + alocacao) × 100`` (0 com carteira vazia)."""
    alocacao = _num(patrimonio.get(CHAVE_DO_NUMERADOR))
    carteira = _num(patrimonio.get("investivel_financeiro")) + alocacao
    return round(alocacao / carteira * 100.0, 2) if carteira > 0 else 0.0
