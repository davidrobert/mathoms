"""Warnings tipados de domínio relacionados a Debt vs. baseline IRPF (ADR-097 D1 · ADR-227 §D6)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class DebtVsIrpfDeclaracaoConflict:
    """Per-property excede agregado IRPF em >10% (ADR-227 §D6) — per-property vence; UI sinaliza; não bloqueia compute."""

    member_key: str
    soma_debt_brl: Decimal
    total_dividas_irpf_brl: Decimal
    ratio: Decimal

    def format(self) -> str:
        """Mensagem amigável para renderização no card S4 (Onda 5)."""
        return (
            f"Dívidas declaradas por imóvel para {self.member_key} (R$ {self.soma_debt_brl:.2f}) "
            f"excedem em {(self.ratio - 1) * 100:.0f}% o total agregado do baseline IRPF "
            f"(R$ {self.total_dividas_irpf_brl:.2f}). Per-property prevalece; revise a "
            f"declaração ou as Debts vinculadas para reconciliar."
        )


__all__ = ["DebtVsIrpfDeclaracaoConflict"]
