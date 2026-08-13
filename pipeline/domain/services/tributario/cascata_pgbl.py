"""Regra da base dedutível de PGBL da cascata fiscal — ADR-236 §D5 (rules-as-code, ADR-143).

Extraído de ``cascata_calculator`` sem mudança de comportamento: o arquivo estava
em 498/500 linhas e a base dedutível é a concern que a A40.l34 possui.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pipeline.domain.models.transaction import Money

#: PGBL — art. 11 Lei 9.532/97.
PGBL_LIMITE_PCT: Decimal = Decimal("0.12")


# ADR-375 D4 cond. 1: `tipo_declaracao_ir` desconhecido não afirma dedutibilidade.
# A afirmação não é decorativa — `pgbl_aplicavel` é precondição de T1 e T3, os dois
# triggers que prescrevem aporte em PGBL. Ordem das guardas é deliberada: sem base
# tributável o modelo de declaração é discutível, e o leitor recebe um pedido por vez.
def compute_pgbl(
    renda_pf_tributavel_total: Money, tipo_declaracao_ir: Optional[str] = None
) -> tuple[Money, bool, Optional[str]]:
    """Retorna (limite_anual, aplicavel, motivo_inaplicavel)."""
    limite = Money.brl(renda_pf_tributavel_total.amount * PGBL_LIMITE_PCT)
    if tipo_declaracao_ir == "simplificada":
        return limite, False, "declaracao_simplificada"
    if renda_pf_tributavel_total.amount <= 0:
        return limite, False, "renda_tributavel_pf_zerada"
    if tipo_declaracao_ir is None:
        return limite, False, "tipo_declaracao_desconhecido"
    return limite, True, None
