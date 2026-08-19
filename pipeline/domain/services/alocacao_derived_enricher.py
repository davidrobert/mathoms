"""Injeta ``alocacao_alvo.derived`` no bloco de goals do E5 ([[ADR-141]] §Emenda item 4).

Saiu de ``e5_serialization`` em [[ADR-400]]: enriquecimento de domínio não é
serialização, e a supressão por incerteza de classificação trouxe um terceiro
input que tornava a assinatura do módulo de wire ainda mais larga.
"""

from __future__ import annotations

from typing import Any

_GoalsPayload = dict[str, Any]


def enrich_alocacao_with_deviation(
    goals: _GoalsPayload,
    tabela_classes: list,
    *,
    patrimonio: dict[str, Any] | None = None,
    nao_classificado_pct: float | None = None,
) -> _GoalsPayload:
    """Desvio atual-vs-alvo + supressões de cobertura e de incerteza de classe."""
    from pipeline.domain.services.alocacao_alvo_deviation import AlocacaoAlvoDeviationCalculator
    from pipeline.domain.services.investimentos_cobertura import motivo_supressao_e5

    alvo = (goals or {}).get("alocacao_alvo")
    if not isinstance(alvo, dict) or "rf_pos_pct" not in alvo:
        return goals
    result = AlocacaoAlvoDeviationCalculator().calculate(tabela_classes or [], alvo)
    result = result.talvez_suprimir(motivo_supressao_e5(patrimonio))
    result = result.suprimir_por_incerteza(nao_classificado_pct)
    return {**goals, "alocacao_alvo": {**alvo, "derived": result.to_dict()}}
