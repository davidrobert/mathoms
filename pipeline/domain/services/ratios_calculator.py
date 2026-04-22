"""RatiosCalculator — ratios financeiros do E5 (Sessão A5a · Fase 8).

Extrai ``analyze_ratios`` (e5_analyze.py:1262) em domain service puro.
Calcula taxa de poupança (recorrente e total), endividamento, cobertura de
despesas e placeholders para rentabilidade/IR.

Prefere janela de 12 meses (``fluxo.janela_12m``) quando disponível — mais
representativa que o período completo (paridade com legado).

Função pura. Recebe dicts ``fluxo`` e ``patrimonio`` (herdados das etapas
anteriores); não tem config externa (salvo constantes placeholder como
``"N/D"`` para rentabilidade/IR que serão preenchidas em A5c+).
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
            return float(val.replace(",", "."))
        except ValueError:
            return 0.0
    return 0.0


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class FinancialRatios:
    """Output de ``RatiosCalculator.calculate`` — paridade com
    ``analyze_ratios`` do legado via :meth:`to_legacy_dict`.
    """

    taxa_poupanca_recorrente_pct: float
    taxa_poupanca_total_pct: float
    taxa_endividamento_pct: float
    cobertura_despesas_meses: float
    rentabilidade_pct: str = "N/D"
    aliquota_efetiva_ir_pct: str = "N/D"
    janela_referencia: str = "N/D"
    janela_n_meses: int = 0

    def to_legacy_dict(self) -> dict:
        return {
            "taxa_poupanca_recorrente_pct": round(self.taxa_poupanca_recorrente_pct, 2),
            "taxa_poupanca_total_pct": round(self.taxa_poupanca_total_pct, 2),
            "taxa_endividamento_pct": round(self.taxa_endividamento_pct, 2),
            "cobertura_despesas_meses": round(self.cobertura_despesas_meses, 2),
            "rentabilidade_pct": self.rentabilidade_pct,
            "aliquota_efetiva_ir_pct": self.aliquota_efetiva_ir_pct,
            "janela_referencia": self.janela_referencia,
            "janela_n_meses": self.janela_n_meses,
        }


# =============================================================================
# Service
# =============================================================================


class RatiosCalculator:
    """Calcula ratios financeiros a partir de ``fluxo`` + ``patrimonio``.

    Stateless. Paridade com ``analyze_ratios`` inclui:
    - Preferência por janela de 12 meses.
    - Taxa de poupança (recorrente e total).
    - Endividamento como % do patrimônio bruto.
    - Cobertura = investivel / despesa mensal média.
    - Rentabilidade e alíquota IR permanecem como placeholders ``"N/D"``
      (cálculo requer dados de performance e IR retido — fora do escopo do
      service atual).
    """

    def calculate(self, fluxo: dict[str, Any], patrimonio: dict[str, Any]) -> FinancialRatios:
        j12m = fluxo.get("janela_12m", {}) if isinstance(fluxo, dict) else {}

        if j12m:
            receita_recorrente = _safe_float(j12m.get("receita_recorrente", 0))
            despesa_total = _safe_float(j12m.get("despesa_total", 0))
            receita_total = _safe_float(j12m.get("receita_total", 0))
            despesa_mensal_media = _safe_float(j12m.get("despesa_mensal_media", 0))
            janela = str(j12m.get("periodo", "janela 12m"))
            n_meses = int(_safe_float(j12m.get("n_meses", 12)))
        else:
            receita_recorrente = _safe_float(fluxo.get("receita_recorrente", 0))
            despesa_total = _safe_float(fluxo.get("despesa_total", 0))
            receita_total = _safe_float(fluxo.get("receita_total", 0))
            despesa_mensal_media = _safe_float(fluxo.get("despesa_mensal_media", 0))
            janela = "período completo"
            n_meses = 0

        # Taxa poupança recorrente (12m).
        taxa_poupanca_recorrente = 0.0
        if receita_recorrente > 0:
            taxa_poupanca_recorrente = (
                (receita_recorrente - despesa_total) / receita_recorrente
            ) * 100

        # Taxa poupança total (12m).
        taxa_poupanca_total = 0.0
        if receita_total > 0:
            taxa_poupanca_total = ((receita_total - despesa_total) / receita_total) * 100

        # Endividamento — sem janela (patrimônio).
        bruto = _safe_float(patrimonio.get("bruto", 0))
        dividas = _safe_float(patrimonio.get("dividas", 0))
        taxa_endividamento = (dividas / bruto * 100) if bruto > 0 else 0.0

        # Cobertura despesas (meses).
        investivel = _safe_float(patrimonio.get("investivel", 0))
        cobertura_meses = investivel / despesa_mensal_media if despesa_mensal_media > 0 else 0.0

        return FinancialRatios(
            taxa_poupanca_recorrente_pct=taxa_poupanca_recorrente,
            taxa_poupanca_total_pct=taxa_poupanca_total,
            taxa_endividamento_pct=taxa_endividamento,
            cobertura_despesas_meses=cobertura_meses,
            janela_referencia=janela,
            janela_n_meses=n_meses,
        )
