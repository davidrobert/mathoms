"""Conversores de sub-resultado tipado do E5 → dict do artefato.

Extraídos de ``e5_serialization`` quando o módulo bateu o teto de 500 linhas:
serializar ``PassiveIncomeResult``/``InformeProventosSummary`` é
responsabilidade própria, distinta de montar o output. ``build_e5_output``
reimporta os dois que consome, então o path de import antigo segue válido.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from pipeline.domain.services.passive_income_calculator import PassiveIncomeResult

_GoalsPayload = Mapping[str, Any]
_FontesPayload = Mapping[str, Decimal]


def _proventos_summary_to_dict(s) -> _GoalsPayload:
    """Wire JSON number (ADR-090 §consequências): Decimal → float só na borda."""
    return {
        "ticker": s.ticker,
        "ano_base": s.ano_base,
        "total_proventos_brl": float(s.total_proventos_brl),
        "ir_retido_brl": float(s.ir_retido_brl),
        "renda_liquida_brl": float(s.renda_liquida_brl),
        "custo_total_brl": float(s.custo_total_brl) if s.custo_total_brl is not None else None,
        "valor_mercado_brl": (
            float(s.valor_mercado_brl) if s.valor_mercado_brl is not None else None
        ),
        "yield_on_cost_pct": (
            float(s.yield_on_cost_pct) if s.yield_on_cost_pct is not None else None
        ),
        "yield_on_market_pct": (
            float(s.yield_on_market_pct) if s.yield_on_market_pct is not None else None
        ),
    }


def _janela_irpf(ano_referencia: int | None) -> str:
    """Rótulo de janela para mensalizações fiscais (ADR-306 §D1 família iii)."""
    return f"irpf_{ano_referencia}" if ano_referencia is not None else "irpf"


def _passive_income_to_dict(pi: PassiveIncomeResult) -> _GoalsPayload:
    """Serializa ``PassiveIncomeResult`` para o JSON top-level (UI consome)."""
    return {
        "status": pi.status,
        "renda_passiva_anual_brl": float(pi.renda_passiva_anual_brl),
        "renda_passiva_mensal_brl": float(pi.renda_passiva_mensal_brl),
        "renda_passiva_por_fonte_brl": _decimals_to_float(pi.renda_passiva_por_fonte_brl),
        # A37.l7 PR-2: excluídos do headline por design (ADR-191/ADR-336) —
        # irmãos explícitos, fora do dict conservativo.
        "renda_ativa_pj_excluida_brl": float(pi.renda_ativa_pj_excluida_brl),
        "ganho_capital_excluido_brl": float(pi.ganho_capital_excluido_brl),
        "patrimonio_gerador_brl": float(pi.patrimonio_gerador_brl),
        "trs_efetiva_pct": float(pi.trs_efetiva_pct),
        "ano_referencia_irpf": pi.ano_referencia_irpf,
        "defasagem_meses": pi.defasagem_meses,
        "acumuladores_pct_gerador": float(pi.acumuladores_pct_gerador),
        "janela": _janela_irpf(pi.ano_referencia_irpf),
        "janela_meses": 12,
    }


def _decimals_to_float(d: _FontesPayload) -> dict[str, float]:
    return {k: float(v) for k, v in d.items()}
