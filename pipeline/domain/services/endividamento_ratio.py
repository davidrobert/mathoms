"""Razão dívida/patrimônio, com a regra de supressão junto ([[A40.l114]]).

Mora fora de ``ratios_calculator`` porque a regra não é aritmética de razão: ela
decide *quando a razão não existe*. Publicar `0,0` sobre passivo que ninguém
conseguiu ler é afirmação sobre o patrimônio da família ([[ADR-431]]), e na direção
perigosa — subdeclarar passivo deixa a prescrição mais agressiva, não mais cautelosa.
"""

from __future__ import annotations

from typing import Any, Mapping

from pipeline.domain.services.money_parsing import valor_monetario_float


def _safe_float(val: Any) -> float:
    return valor_monetario_float(val)


# `None` e não `0,0`: disciplina do irmão `imobilizacao_patrimonial_pct`
# ([[ADR-420]] §D3) — razão sobre numerador não apurado é indefinida, e `0,0` leria
# como "sem dívida" justamente na família endividada.
def calc_endividamento_pct(patrimonio: Mapping[str, Any]) -> float | None:
    """Percentual do bruto comprometido; ``None`` com linha de dívida ilegível."""
    if _safe_float(patrimonio.get("dividas_nao_apuradas", 0)) > 0:
        return None
    bruto = _safe_float(patrimonio.get("bruto", 0))
    dividas = _safe_float(patrimonio.get("dividas", 0))
    return round((dividas / bruto * 100) if bruto > 0 else 0.0, 2)
