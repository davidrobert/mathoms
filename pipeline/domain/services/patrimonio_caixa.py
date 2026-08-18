"""Caixa + moeda estrangeira — categoria #6 da taxonomia ADR-145.

O negativo de posição corrente segue cru: a guarda de sinal ([[ADR-394]] §Emenda
D6) reclassifica cheque especial. Residual IRPF ainda tem floor zero — negativo
ali é dupla-contagem, não saldo devedor.
"""

from __future__ import annotations

from pipeline.domain.services.patrimonio_types import PatrimonioInputs, safe_float

_TIPOS_MOEDA_ESTRANGEIRA = {"moeda_estrangeira", "moeda_estrangeira_irpf"}


_RESIDUAL_KEYS = (
    "residencia",
    "imoveis_investimento",
    "veiculos",
    "investimentos_titular",
    "investimentos_conjuge",
)


def compute_caixa(inputs: PatrimonioInputs, **componentes):
    """Caixa + ME. Posição corrente cru; residual IRPF com floor zero."""
    if inputs.has_current_positions:
        return inputs.caixa_total_brl, [d.to_dict() for d in inputs.caixa_detalhes]
    residual = componentes["total_bens_irpf"] - sum(componentes[k] for k in _RESIDUAL_KEYS)
    return max(0.0, residual), []


def caixa_me_from_detalhes(detalhes: list) -> float:
    """Soma só o caixa em moeda estrangeira do E3."""
    return sum(
        safe_float(d.get("valor_brl", 0))
        for d in detalhes
        if isinstance(d, dict) and d.get("tipo") in _TIPOS_MOEDA_ESTRANGEIRA
    )


__all__ = ["caixa_me_from_detalhes", "compute_caixa"]
