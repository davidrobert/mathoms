"""RatiosCalculator — ratios financeiros do E5 (Sessão A5a · Fase 8 · A8.3 PR-A).

Extrai ``analyze_ratios`` (e5_analyze.py:1262) em domain service puro.
Calcula taxa de poupança (recorrente e total), endividamento, cobertura de
despesas, rentabilidade (TRS efetiva) e alíquota efetiva de IR.

Prefere janela de 12 meses (``fluxo.janela_12m``) quando disponível — mais
representativa que o período completo (paridade com legado).

Função pura. Recebe dicts ``fluxo``+``patrimonio`` (herdados das etapas
anteriores), ``passive_income`` (TRS efetiva opcional, A8.3) e ``irpf``
(alíquota efetiva opcional, A8.3). ``rentabilidade_pct`` e
``aliquota_efetiva_ir_pct`` resolvem para ``Decimal`` quando dados
disponíveis; ``None`` (serializado como ``"N/D"`` em ``to_legacy_dict``)
caso contrário — back-compat de fixtures legados.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer
from pipeline.domain.services.passive_income_calculator import PassiveIncomeResult

# Aliases — Mapping[str, Any] permite shape legado dinâmico no boundary sem
# triggar P3 (que pega ``Dict[str, Any]`` literal).
_FluxoPayload = Mapping[str, Any]
_PatrimonioPayload = Mapping[str, Any]


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
    """Output de ``RatiosCalculator.calculate`` — paridade com ``analyze_ratios``."""

    taxa_poupanca_recorrente_pct: float
    taxa_poupanca_total_pct: float
    taxa_endividamento_pct: float
    cobertura_despesas_meses: float
    rentabilidade_pct: Decimal | None = None
    aliquota_efetiva_ir_pct: Decimal | None = None
    janela_referencia: str = "N/D"
    janela_n_meses: int = 0

    def to_legacy_dict(self) -> dict:
        return {
            "taxa_poupanca_recorrente_pct": round(self.taxa_poupanca_recorrente_pct, 2),
            "taxa_poupanca_total_pct": round(self.taxa_poupanca_total_pct, 2),
            "taxa_endividamento_pct": round(self.taxa_endividamento_pct, 2),
            "cobertura_despesas_meses": round(self.cobertura_despesas_meses, 2),
            "rentabilidade_pct": _format_pct_or_nd(self.rentabilidade_pct),
            "aliquota_efetiva_ir_pct": _format_pct_or_nd(self.aliquota_efetiva_ir_pct),
            "janela_referencia": self.janela_referencia,
            "janela_n_meses": self.janela_n_meses,
        }


def _format_pct_or_nd(value: Decimal | None) -> str:
    """Serializa Decimal como string com 2 casas; ``None`` vira ``"N/D"``."""
    return f"{value:.2f}" if value is not None else "N/D"


# =============================================================================
# Service
# =============================================================================


class RatiosCalculator:
    """Calcula ratios financeiros a partir de ``fluxo`` + ``patrimonio``.

    Stateless. Paridade com ``analyze_ratios`` inclui taxa de poupança
    (recorrente e total), endividamento e cobertura. ``rentabilidade_pct``
    é populada com TRS efetiva quando ``passive_income.status == "ok"``;
    ``aliquota_efetiva_ir_pct`` é derivada de ``ir_pago_total / renda_total``
    quando ``irpf`` é fornecido com ano-base disponível.
    """

    def calculate(
        self,
        fluxo: _FluxoPayload,
        patrimonio: _PatrimonioPayload,
        *,
        passive_income: PassiveIncomeResult | None = None,
        irpf: IRPFAnalyzer | None = None,
    ) -> FinancialRatios:
        window = _resolve_window(fluxo)
        poupanca = _calc_poupanca(window)
        return FinancialRatios(
            taxa_poupanca_recorrente_pct=poupanca.recorrente_pct_value,
            taxa_poupanca_total_pct=poupanca.geral_pct_value,
            taxa_endividamento_pct=_calc_endividamento(patrimonio),
            cobertura_despesas_meses=_calc_cobertura(
                patrimonio, float(window.despesa_mensal_media_brl)
            ),
            rentabilidade_pct=_resolve_rentabilidade(passive_income),
            aliquota_efetiva_ir_pct=_resolve_aliquota_ir(irpf, passive_income),
            janela_referencia=window.referencia,
            janela_n_meses=window.n_meses,
        )


# =============================================================================
# Helpers — funções puras agrupadas por responsabilidade
# =============================================================================


@dataclass(frozen=True)
class _Window:
    """Janela de fluxo de caixa derivada (Decimal interno; serializa em float)."""

    receita_recorrente_brl: Decimal
    receita_total_brl: Decimal
    despesa_total_brl: Decimal
    despesa_mensal_media_brl: Decimal
    referencia: str
    n_meses: int


@dataclass(frozen=True)
class _Poupanca:
    recorrente_pct_value: float
    geral_pct_value: float


def _resolve_window(fluxo: _FluxoPayload) -> _Window:
    j12m = fluxo.get("janela_12m", {}) if isinstance(fluxo, dict) else {}
    src = j12m if j12m else (fluxo if isinstance(fluxo, dict) else {})
    referencia = str(j12m.get("periodo", "janela 12m")) if j12m else "período completo"
    n_meses = int(_safe_float(j12m.get("n_meses", 12))) if j12m else 0
    return _Window(
        receita_recorrente_brl=Decimal(str(_safe_float(src.get("receita_recorrente", 0)))),
        receita_total_brl=Decimal(str(_safe_float(src.get("receita_total", 0)))),
        despesa_total_brl=Decimal(str(_safe_float(src.get("despesa_total", 0)))),
        despesa_mensal_media_brl=Decimal(str(_safe_float(src.get("despesa_mensal_media", 0)))),
        referencia=referencia,
        n_meses=n_meses,
    )


def _calc_poupanca(window: _Window) -> _Poupanca:
    recorrente = _ratio_pct(
        float(window.receita_recorrente_brl - window.despesa_total_brl),
        float(window.receita_recorrente_brl),
    )
    pct_total = _ratio_pct(
        float(window.receita_total_brl - window.despesa_total_brl),
        float(window.receita_total_brl),
    )
    return _Poupanca(recorrente_pct_value=recorrente, geral_pct_value=pct_total)


def _ratio_pct(numerator: float, denominator: float) -> float:
    return (numerator / denominator * 100) if denominator > 0 else 0.0


def _calc_endividamento(patrimonio: _PatrimonioPayload) -> float:
    bruto = _safe_float(patrimonio.get("bruto", 0))
    dividas = _safe_float(patrimonio.get("dividas", 0))
    return _ratio_pct(dividas, bruto)


def _calc_cobertura(patrimonio: _PatrimonioPayload, despesa_mensal_media: float) -> float:
    investivel = _safe_float(patrimonio.get("investivel", 0))
    return investivel / despesa_mensal_media if despesa_mensal_media > 0 else 0.0


def _resolve_rentabilidade(
    passive_income: PassiveIncomeResult | None,
) -> Decimal | None:
    if passive_income is None or passive_income.status != "ok":
        return None
    return passive_income.trs_efetiva_pct


def _resolve_aliquota_ir(
    irpf: IRPFAnalyzer | None,
    passive_income: PassiveIncomeResult | None,
) -> Decimal | None:
    """Deriva alíquota efetiva (ir_pago_total / renda_total × 100) quando possível."""
    if irpf is None:
        return None
    ano = _resolve_ano_base(irpf, passive_income)
    if ano is None:
        return None
    renda_total = irpf.renda_anual_familiar(ano)
    if renda_total <= Decimal("0"):
        return None
    ir_pago = irpf.ir_pago_total(ano)
    return (ir_pago / renda_total * Decimal("100")).quantize(Decimal("0.01"))


def _resolve_ano_base(irpf: IRPFAnalyzer, passive_income: PassiveIncomeResult | None) -> int | None:
    if passive_income is not None and passive_income.ano_referencia_irpf is not None:
        return passive_income.ano_referencia_irpf
    anos = irpf.anos_base_disponiveis()
    return anos[-1] if anos else None
