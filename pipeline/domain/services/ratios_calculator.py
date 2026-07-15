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
from typing import Any, Literal, Mapping

from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer
from pipeline.domain.services.passive_income_calculator import PassiveIncomeResult

# Aliases — Mapping[str, Any] permite shape legado dinâmico no boundary sem
# triggar P3 (que pega ``Dict[str, Any]`` literal).
_FluxoPayload = Mapping[str, Any]
_PatrimonioPayload = Mapping[str, Any]

RentabilidadeStatus = Literal["ok", "sem_irpf", "gerador_zero", "sem_dados_essencial", "suspeito"]

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")
_PCT_QUANTUM = Decimal("0.01")


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


def _to_decimal(val) -> Decimal:
    if val is None:
        return _ZERO
    if isinstance(val, Decimal):
        return val
    if isinstance(val, bool):
        return _ZERO
    if isinstance(val, (int, str)):
        try:
            return Decimal(val)
        except Exception:
            return _ZERO
    if isinstance(val, float):
        return Decimal(str(val))
    return _ZERO


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class RentabilidadeConfig:
    """Parâmetros do card Rentabilidade ([[ADR-191]] §D3); ``meta_pct`` é 5% por padrão."""

    meta_pct: Decimal = Decimal("5.0")
    # A28.l2 — guardrail de sanidade determinístico do E5 (fonte única; a
    # A28.l11 apenas consome): TRS acima disso é implausível como yield de
    # carteira → status "suspeito"; nunca publicar o número sem flag.
    suspeito_threshold_pct: Decimal = Decimal("8.0")


@dataclass(frozen=True)
class RentabilidadeRatio:
    """Card Rentabilidade — TRS efetiva + ano-base + cobertura essencial + status ([[ADR-191]] §D3/D4)."""

    valor_pct: Decimal | None
    ano_base: int | None
    defasagem_meses: int | None
    meta_pct: Decimal
    cobertura_despesa_essencial_pct: Decimal | None
    status: RentabilidadeStatus

    def to_dict(self) -> dict:
        return {
            "valor_pct": _serialize_decimal(self.valor_pct),
            "ano_base": self.ano_base,
            "defasagem_meses": self.defasagem_meses,
            "meta_pct": _serialize_decimal(self.meta_pct),
            "cobertura_despesa_essencial_pct": _serialize_decimal(
                self.cobertura_despesa_essencial_pct
            ),
            "status": self.status,
        }


@dataclass(frozen=True)
class FinancialRatios:
    """Output de ``RatiosCalculator.calculate`` — paridade com ``analyze_ratios``."""

    taxa_poupanca_recorrente_pct: float
    taxa_poupanca_total_pct: float
    taxa_endividamento_pct: float
    # ADR-335: renomeado de `cobertura_despesas_meses`; numerador financeiro-only
    # (sem imóvel ilíquido). `to_legacy_dict` emite o nome antigo como alias
    # deprecated por 1 ciclo.
    autonomia_financeira_meses: float
    rentabilidade_pct: Decimal | None = None
    aliquota_efetiva_ir_pct: Decimal | None = None
    janela_referencia: str = "N/D"
    janela_n_meses: int = 0
    janela: str = "full"
    rentabilidade: RentabilidadeRatio | None = None

    def to_legacy_dict(self) -> dict:
        return {
            "taxa_poupanca_recorrente_pct": round(self.taxa_poupanca_recorrente_pct, 2),
            "taxa_poupanca_total_pct": round(self.taxa_poupanca_total_pct, 2),
            "taxa_endividamento_pct": round(self.taxa_endividamento_pct, 2),
            "autonomia_financeira_meses": round(self.autonomia_financeira_meses, 2),
            # ADR-335: alias deprecated por 1 ciclo (view-model/consumidores antigos).
            "cobertura_despesas_meses": round(self.autonomia_financeira_meses, 2),
            "rentabilidade_pct": _format_pct_or_nd(self.rentabilidade_pct),
            "aliquota_efetiva_ir_pct": _format_pct_or_nd(self.aliquota_efetiva_ir_pct),
            "janela_referencia": self.janela_referencia,
            "janela_n_meses": self.janela_n_meses,
            "janela": self.janela,
            "janela_meses": self.janela_n_meses,
            "rentabilidade": (
                self.rentabilidade.to_dict() if self.rentabilidade is not None else None
            ),
        }


def _format_pct_or_nd(value: Decimal | None) -> str:
    """Serializa Decimal como string com 2 casas; ``None`` vira ``"N/D"``."""
    return f"{value:.2f}" if value is not None else "N/D"


def _serialize_decimal(value: Decimal | None) -> float | None:
    """Decimal → float arredondado (2 casas) para JSON; ``None`` preservado."""
    if value is None:
        return None
    return float(value.quantize(_PCT_QUANTUM))


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

    def __init__(self, rentabilidade_config: RentabilidadeConfig | None = None) -> None:
        self._rentabilidade_config = rentabilidade_config or RentabilidadeConfig()

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
            autonomia_financeira_meses=_calc_autonomia_financeira(
                patrimonio, float(window.despesa_mensal_media_brl)
            ),
            rentabilidade_pct=_resolve_rentabilidade(passive_income),
            aliquota_efetiva_ir_pct=_resolve_aliquota_ir(irpf, passive_income),
            janela_referencia=window.referencia,
            janela_n_meses=window.n_meses,
            janela=window.janela,
            rentabilidade=_build_rentabilidade(passive_income, window, self._rentabilidade_config),
        )


# =============================================================================
# Helpers — funções puras agrupadas por responsabilidade
# =============================================================================


@dataclass(frozen=True)
class _Window:
    """Janela de fluxo de caixa derivada (Decimal interno; ``despesa_mensal_essencial_brl`` é 0 sem ``categorias_in``)."""

    receita_recorrente_brl: Decimal
    receita_total_brl: Decimal
    despesa_total_brl: Decimal
    # ADR-333: consumo = despesa_total − transferência patrimonial (aporte); denominador da poupança.
    despesa_consumo_brl: Decimal
    despesa_mensal_media_brl: Decimal
    despesa_mensal_essencial_brl: Decimal
    referencia: str
    n_meses: int
    janela: str


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
        # ADR-333: fallback p/ despesa_total em payload legado (pré-despesa_consumo).
        despesa_consumo_brl=Decimal(
            str(_safe_float(src.get("despesa_consumo", src.get("despesa_total", 0))))
        ),
        despesa_mensal_media_brl=Decimal(str(_safe_float(src.get("despesa_mensal_media", 0)))),
        despesa_mensal_essencial_brl=Decimal(
            str(_safe_float(src.get("despesa_mensal_essencial", 0)))
        ),
        referencia=referencia,
        n_meses=n_meses,
        janela="12m" if j12m else "full",
    )


def _calc_poupanca(window: _Window) -> _Poupanca:
    # ADR-333: poupança = renda − CONSUMO (aporte é transferência, não consumo).
    recorrente = _ratio_pct(
        float(window.receita_recorrente_brl - window.despesa_consumo_brl),
        float(window.receita_recorrente_brl),
    )
    pct_total = _ratio_pct(
        float(window.receita_total_brl - window.despesa_consumo_brl),
        float(window.receita_total_brl),
    )
    return _Poupanca(recorrente_pct_value=recorrente, geral_pct_value=pct_total)


def _ratio_pct(numerator: float, denominator: float) -> float:
    return (numerator / denominator * 100) if denominator > 0 else 0.0


def _calc_endividamento(patrimonio: _PatrimonioPayload) -> float:
    bruto = _safe_float(patrimonio.get("bruto", 0))
    dividas = _safe_float(patrimonio.get("dividas", 0))
    return _ratio_pct(dividas, bruto)


def _calc_autonomia_financeira(
    patrimonio: _PatrimonioPayload, despesa_mensal_media: float
) -> float:
    # ADR-335: autonomia financeira (runway de liquidez) usa `investivel_financeiro`
    # (cat_3+4+5+6, SEM cat_2 imóvel ilíquido) — numerador de horizonte de choque,
    # toggle-independente. Distinto do `investivel_efetivo` da IF (ADR-142/215 §6),
    # que legitimamente conta cat_2 quando `imoveis_no_if=true` (horizonte de décadas).
    investivel = _safe_float(patrimonio.get("investivel_financeiro", 0))
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


def _build_rentabilidade(
    passive_income: PassiveIncomeResult | None,
    window: _Window,
    config: RentabilidadeConfig,
) -> RentabilidadeRatio | None:
    """Compõe ``RentabilidadeRatio`` aninhado ([[ADR-191]] §D3/D4)."""
    if passive_income is None:
        return None
    if passive_income.status == "sem_irpf":
        return _rentabilidade_empty(config, status="sem_irpf")
    if passive_income.status == "gerador_zero":
        return _rentabilidade_empty(config, status="gerador_zero", pi=passive_income)
    cobertura, status = _cobertura_essencial(
        passive_income.renda_passiva_mensal_brl, window.despesa_mensal_essencial_brl
    )
    if _trs_suspeita(passive_income.trs_efetiva_pct, config):
        status = "suspeito"
    return _rentabilidade_ok(passive_income, config, cobertura, status)


def _trs_suspeita(trs_efetiva_pct: Decimal, config: RentabilidadeConfig) -> bool:
    """Guardrail A28.l2: TRS acima do plausível — nunca publicar sem flag."""
    return trs_efetiva_pct > config.suspeito_threshold_pct


def _rentabilidade_ok(
    pi: PassiveIncomeResult,
    config: RentabilidadeConfig,
    cobertura: Decimal | None,
    status: RentabilidadeStatus,
) -> RentabilidadeRatio:
    return RentabilidadeRatio(
        valor_pct=pi.trs_efetiva_pct,
        ano_base=pi.ano_referencia_irpf,
        defasagem_meses=pi.defasagem_meses,
        meta_pct=config.meta_pct,
        cobertura_despesa_essencial_pct=cobertura,
        status=status,
    )


def _rentabilidade_empty(
    config: RentabilidadeConfig,
    *,
    status: RentabilidadeStatus,
    pi: PassiveIncomeResult | None = None,
) -> RentabilidadeRatio:
    return RentabilidadeRatio(
        valor_pct=None,
        ano_base=pi.ano_referencia_irpf if pi else None,
        defasagem_meses=pi.defasagem_meses if pi else None,
        meta_pct=config.meta_pct,
        cobertura_despesa_essencial_pct=None,
        status=status,
    )


def _cobertura_essencial(
    renda_passiva_mensal: Decimal, despesa_mensal_essencial: Decimal
) -> tuple[Decimal | None, RentabilidadeStatus]:
    if despesa_mensal_essencial <= _ZERO:
        return None, "sem_dados_essencial"
    cobertura = (renda_passiva_mensal / despesa_mensal_essencial * _HUNDRED).quantize(_PCT_QUANTUM)
    return cobertura, "ok"
