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

from pipeline.domain.services.money_parsing import valor_monetario_float
from pipeline.observability.view_model_pii import redact_cartorial


def _safe_float(val) -> float:
    # O strip incondicional de `.` inflava valor ISO em 100× (r5/M28).
    return valor_monetario_float(val)


# =============================================================================
# Result
# =============================================================================


# Campos cujo valor obriga declaração de fonte no item — e vice-versa
# (bijeção; gate em ``tests/test_endividamento_fontes_bijecao.py``).
_CAMPOS_COM_FONTE = (
    "saldo_devedor",
    "parcela_mensal",
    "taxa_juros_aa",
    "desembolso_mensal_observado_brl",
)


@dataclass(frozen=True)
class DividaItem:
    # Ausência é None, nunca sentinela ("N/D"/0.0) — contrato tipado no schema E5
    # e guardrail do parecer tratam null como dado faltante (A37.l4 · DE-07).
    descricao: str
    saldo_devedor: float
    # ADR-398: a origem do saldo é `baseline_irpf` (estoque de 31/12) ou
    # `declarado` (usuário). Nenhum outro campo do item tem fonte hoje.
    fonte_saldo: str = "baseline_irpf"
    membro: str | None = None
    divida_id: str | None = None
    tipo: str | None = None
    saldo_ano_referencia: int | None = None
    parcela_mensal: float | None = None
    # Percentual absoluto AO ANO. O sufixo `_aa` é load-bearing: sem ele o
    # classificador monetário-por-default lê 12.5 como R$ 0,12 no snapshot.
    taxa_juros_aa: float | None = None

    def to_dict(self) -> dict:
        item = {
            "divida_id": self.divida_id,
            # A40.l6 redige PII cartorial; o rótulo já nasce de vocabulário
            # fechado (ADR-401 D4), então aqui é cinto-e-suspensório, não a
            # garantia — a peneira de `_CODIGO_CANONICO` é que fecha a porta.
            "descricao": redact_cartorial(self.descricao),
            "membro": self.membro,
            "tipo": self.tipo,
            "saldo_devedor": round(self.saldo_devedor, 2),
            "saldo_ano_referencia": self.saldo_ano_referencia,
            "parcela_mensal": round(self.parcela_mensal, 2)
            if self.parcela_mensal is not None
            else None,
            "taxa_juros_aa": self.taxa_juros_aa,
        }
        item["fontes"] = self._fontes(item)
        return item

    def _fontes(self, item: dict) -> dict:
        """Derivada do próprio item — bijeção por construção, não por disciplina."""
        origens = {
            "saldo_devedor": self.fonte_saldo,
            "parcela_mensal": "declarado",
            "taxa_juros_aa": "declarado",
            "desembolso_mensal_observado_brl": "observado_e4",
        }
        return {c: origens[c] for c in _CAMPOS_COM_FONTE if item.get(c) is not None}


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
