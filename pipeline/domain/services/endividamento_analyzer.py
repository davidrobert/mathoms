"""EndividamentoAnalyzer — análise de dívidas (Sessão A5b · Fase 8).

Extrai ``analyze_endividamento`` (e5_analyze.py:1602) em domain service puro.
Consolida dívidas por membro a partir do baseline e computa proporção sobre
o patrimônio bruto.

Função pura. Depende de ``_resolve_members`` (A5b vai reexpor) e
``MemberAnalyzer`` (A3c) para extração de totais por membro — aqui
recebemos os membros já resolvidos como lista de dicts para manter o service
desacoplado da lógica de resolução (que vive no orquestrador E5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.replace(".", "").replace(",", "."))
        except ValueError:
            return 0.0
    return 0.0


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class DividaItem:
    descricao: str
    saldo_devedor: float
    parcela_mensal: float = 0.0
    taxa_juros: str = "N/D"

    def to_dict(self) -> dict:
        return {
            "descricao": self.descricao,
            "saldo_devedor": round(self.saldo_devedor, 2),
            "parcela_mensal": round(self.parcela_mensal, 2),
            "taxa_juros": self.taxa_juros,
        }


@dataclass(frozen=True)
class EndividamentoAnalysis:
    total_dividas: float
    percentual_patrimonio: float
    dividas: tuple[DividaItem, ...]
    detalhe: str

    def to_legacy_dict(self) -> dict:
        return {
            "total_dividas": round(self.total_dividas, 2),
            "percentual_patrimonio": round(self.percentual_patrimonio, 2),
            "dividas": [d.to_dict() for d in self.dividas],
            "detalhe": self.detalhe,
        }


# =============================================================================
# Service
# =============================================================================


class EndividamentoAnalyzer:
    """Analisa estrutura de dívidas da família.

    Recebe ``patrimonio`` (dict com ``bruto`` e ``dividas``) e ``members``
    como lista de dicts ``{"nome": str, "data": dict}`` já resolvidos. Para
    cada membro com ``total_dividas > 0`` (fallback ``dividas``), cria um
    :class:`DividaItem` com descrição ``"Financiamento imobiliário ({nome})"``
    (paridade com legado).
    """

    def analyze(
        self,
        patrimonio: dict[str, Any],
        members: list[dict[str, Any]],
    ) -> EndividamentoAnalysis:
        bruto = _safe_float(patrimonio.get("bruto", 0))
        dividas_total = _safe_float(patrimonio.get("dividas", 0))
        pct = (dividas_total / bruto * 100) if bruto > 0 else 0.0

        items: list[DividaItem] = []
        for entry in members or []:
            if not isinstance(entry, dict):
                continue
            member_data = entry.get("data") or {}
            nome = entry.get("nome") or ""
            divida_val = _safe_float(
                member_data.get("total_dividas", member_data.get("dividas", 0))
            )
            if divida_val > 0:
                items.append(
                    DividaItem(
                        descricao=f"Financiamento imobiliário ({nome})",
                        saldo_devedor=divida_val,
                    )
                )

        detalhe_parts = [d.descricao for d in items]
        detalhe = "; ".join(detalhe_parts) if detalhe_parts else "Sem dívidas identificadas"

        return EndividamentoAnalysis(
            total_dividas=dividas_total,
            percentual_patrimonio=pct,
            dividas=tuple(items),
            detalhe=detalhe,
        )
