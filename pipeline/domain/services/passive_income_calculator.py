"""``PassiveIncomeCalculator`` — TRS efetiva e renda passiva observada (Lane A8.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Literal, Mapping

from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer
from pipeline.llm.schemas.e16_irpf_full import (
    CodigoRendimentoIsento,
    CodigoRendimentoTribExclusiva,
    IRPFFullOutput,
)

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")
_TWELVE = Decimal("12")
_PCT_QUANTUM = Decimal("0.01")

# Aliases — boundary aceita dict legado (PatrimonioCalculator emite shape
# dinâmico não tipado) sem propagar Dict[str, Any] para a API pública (P3).
PatrimonioPayload = Mapping[str, Any]
HoldingsPayload = Mapping[str, Any]
StatusEmpty = Literal["sem_irpf", "gerador_zero"]
Status = Literal["ok", "sem_irpf", "gerador_zero"]


@dataclass(frozen=True)
class PassiveIncomeConfig:
    """Parâmetros do cálculo TRS efetiva (D15: meta 5% Perini, 4% Trinity)."""

    trs_meta_pct: Decimal = Decimal("5.0")
    trs_trinity_pct: Decimal = Decimal("4.0")
    incluir_imoveis_investimento: bool = True
    excluir_residencia: bool = True
    excluir_veiculos: bool = True
    excluir_derivativos: bool = True
    reserva_emergencia_meses: int = 6
    acumulador_tickers: tuple[str, ...] = (
        "BOVA11",
        "IVVB11",
        "IVV",
        "SPY",
        "VOO",
        "WRLD11",
    )


@dataclass(frozen=True)
class PassiveIncomeResult:
    """Output de :meth:`PassiveIncomeCalculator.calculate` — render UI do S7."""

    renda_passiva_anual_brl: Decimal
    renda_passiva_mensal_brl: Decimal
    renda_passiva_por_fonte_brl: dict[str, Decimal]
    patrimonio_gerador_brl: Decimal
    trs_efetiva_pct: Decimal
    ano_referencia_irpf: int | None
    defasagem_meses: int | None
    acumuladores_pct_gerador: Decimal
    status: Status


def _to_decimal(value: Any) -> Decimal:
    """Coerce ``int|str|Decimal|float|None`` → Decimal (float via ``str(v)``)."""
    if value is None or isinstance(value, bool):
        return _ZERO
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, str)):
        try:
            return Decimal(value)
        except Exception:
            return _ZERO
    if isinstance(value, float):
        return Decimal(str(value))
    return _ZERO


def _holding_tokens(raw: str) -> frozenset[str]:
    """Tokens uppercase do nome da posição — descrições IRPF embutem o ticker
    em qualquer posição ("1000 ACOES BOVA11 ..."), não só no primeiro token
    (ADR-306: primeiro-token zerava ``acumuladores_pct_gerador`` no dogfood)."""
    if not raw:
        return frozenset()
    return frozenset(raw.strip().upper().split())


@dataclass(frozen=True)
class _RendaPassivaBuckets:
    """Buckets internos da renda passiva observada por fonte RFB."""

    dividendos: Decimal = _ZERO
    jcp: Decimal = _ZERO
    aplicacoes: Decimal = _ZERO
    ganho_capital: Decimal = _ZERO
    exterior: Decimal = _ZERO
    alugueis: Decimal = _ZERO

    @property
    def total(self) -> Decimal:
        return (
            self.dividendos
            + self.jcp
            + self.aplicacoes
            + self.ganho_capital
            + self.exterior
            + self.alugueis
        )

    def to_dict(self) -> dict[str, Decimal]:
        return {
            "dividendos": self.dividendos,
            "jcp": self.jcp,
            "aplicacoes": self.aplicacoes,
            "ganho_capital": self.ganho_capital,
            "exterior": self.exterior,
            "alugueis": self.alugueis,
        }


@dataclass(frozen=True)
class _OkContext:
    """Inputs já validados para ``_build_ok_result`` (ano-base e gerador resolvidos)."""

    irpf: IRPFAnalyzer
    ano_ref: int
    gerador: Decimal
    investimentos_atuais: HoldingsPayload | None
    reference_date: date


class PassiveIncomeCalculator:
    """Computa TRS efetiva e carteira de renda — pure service (R9/ISP)."""

    def __init__(self, config: PassiveIncomeConfig) -> None:
        self._config = config

    def calculate(
        self,
        *,
        irpf: IRPFAnalyzer | None,
        patrimonio: PatrimonioPayload,
        investimentos_atuais: HoldingsPayload | None,
        reference_date: date,
        despesa_mensal_media_brl: Decimal,
    ) -> PassiveIncomeResult:
        """Devolve KPIs + status enum (``ok`` | ``sem_irpf`` | ``gerador_zero``)."""
        ano_ref = self._resolve_ano_referencia(irpf)
        if irpf is None or ano_ref is None:
            return self._empty_result(status="sem_irpf", ano_ref=None)
        gerador = self._patrimonio_gerador(
            patrimonio, investimentos_atuais, _to_decimal(despesa_mensal_media_brl)
        )
        if gerador <= _ZERO:
            return self._empty_result(status="gerador_zero", ano_ref=ano_ref)
        ctx = _OkContext(irpf, ano_ref, gerador, investimentos_atuais, reference_date)
        return self._build_ok_result(ctx)

    def _build_ok_result(self, ctx: _OkContext) -> PassiveIncomeResult:
        buckets = self._renda_passiva_observada(irpf=ctx.irpf, ano=ctx.ano_ref)
        anual = buckets.total
        return PassiveIncomeResult(
            renda_passiva_anual_brl=anual,
            renda_passiva_mensal_brl=(anual / _TWELVE) if anual > _ZERO else _ZERO,
            renda_passiva_por_fonte_brl=buckets.to_dict(),
            patrimonio_gerador_brl=ctx.gerador,
            trs_efetiva_pct=(anual / ctx.gerador * _HUNDRED).quantize(_PCT_QUANTUM),
            ano_referencia_irpf=ctx.ano_ref,
            defasagem_meses=self._defasagem_meses(
                ano_ref=ctx.ano_ref, reference_date=ctx.reference_date
            ),
            acumuladores_pct_gerador=self._pct_acumuladores(
                gerador=ctx.gerador, investimentos_atuais=ctx.investimentos_atuais
            ),
            status="ok",
        )

    def _renda_passiva_observada(self, *, irpf: IRPFAnalyzer, ano: int) -> _RendaPassivaBuckets:
        """Decompõe rendimentos passivos por código RFB (cod 09/10/12/06 + exterior)."""
        decls = irpf.declarations_for_year(ano)
        explicit = _aggregate_explicit_buckets(decls)
        # paridade com IRPFAnalyzer: bucket aluguel ainda em trabalho em main;
        # delta vs split_trabalho_vs_capital absorve quando PR-B mergear.
        capital_total = irpf.split_trabalho_vs_capital(ano).capital_brl
        delta = capital_total - explicit.total
        alugueis = delta if delta > _ZERO else _ZERO
        return _RendaPassivaBuckets(
            dividendos=explicit.dividendos,
            jcp=explicit.jcp,
            aplicacoes=explicit.aplicacoes,
            ganho_capital=explicit.ganho_capital,
            exterior=explicit.exterior,
            alugueis=alugueis,
        )

    def _patrimonio_gerador(
        self,
        patrimonio: PatrimonioPayload,
        investimentos_atuais: HoldingsPayload | None,
        despesa_mensal_media_brl: Decimal,
    ) -> Decimal:
        """Carteira de renda (D1): inv_titular+conjuge ± imóveis ± caixa-reserva − derivativos."""
        gerador = self._sum_investimentos_membro(
            patrimonio, "titular"
        ) + self._sum_investimentos_membro(patrimonio, "conjuge")
        if self._config.incluir_imoveis_investimento:
            gerador += _to_decimal(patrimonio.get("imoveis_investimento", 0))
        gerador += self._caixa_excedente(patrimonio, despesa_mensal_media_brl)
        if self._config.excluir_derivativos:
            gerador -= _sum_derivativos(patrimonio, investimentos_atuais)
        return max(gerador, _ZERO)

    def _caixa_excedente(
        self, patrimonio: PatrimonioPayload, despesa_mensal_media_brl: Decimal
    ) -> Decimal:
        caixa = _to_decimal(patrimonio.get("caixa_moeda_estrangeira", 0))
        reserva = despesa_mensal_media_brl * Decimal(self._config.reserva_emergencia_meses)
        excedente = caixa - reserva
        return excedente if excedente > _ZERO else _ZERO

    @staticmethod
    def _sum_investimentos_membro(
        patrimonio: PatrimonioPayload, membro_role: Literal["titular", "conjuge"]
    ) -> Decimal:
        """Lê chave canônica ``investimentos_<role>`` ou fallback dinâmico."""
        canonical = f"investimentos_{membro_role}"
        if canonical in patrimonio:
            return _to_decimal(patrimonio[canonical])
        return _scan_dynamic_member_key(patrimonio, membro_role)

    def _pct_acumuladores(
        self,
        *,
        gerador: Decimal,
        investimentos_atuais: HoldingsPayload | None,
    ) -> Decimal:
        """% do gerador em tickers ETF/fundo acumulador — heurística banner UI."""
        if gerador <= _ZERO or not investimentos_atuais:
            return _ZERO
        tickers = {t.upper() for t in self._config.acumulador_tickers}
        total = _sum_holdings_matching_tickers(investimentos_atuais, tickers)
        if total <= _ZERO:
            return _ZERO
        return (total / gerador * _HUNDRED).quantize(_PCT_QUANTUM)

    @staticmethod
    def _resolve_ano_referencia(irpf: IRPFAnalyzer | None) -> int | None:
        if irpf is None:
            return None
        anos = irpf.anos_base_disponiveis()
        return anos[-1] if anos else None

    @staticmethod
    def _defasagem_meses(*, ano_ref: int, reference_date: date) -> int:
        """Meses entre 1º jan do ano-base+1 (limite declaração) e ``reference_date``."""
        delta_anos = reference_date.year - (ano_ref + 1)
        delta_meses = reference_date.month - 1
        total = delta_anos * 12 + delta_meses
        return max(total, 0)

    @staticmethod
    def _empty_result(
        *,
        status: StatusEmpty,
        ano_ref: int | None,
    ) -> PassiveIncomeResult:
        return PassiveIncomeResult(
            renda_passiva_anual_brl=_ZERO,
            renda_passiva_mensal_brl=_ZERO,
            renda_passiva_por_fonte_brl=_RendaPassivaBuckets().to_dict(),
            patrimonio_gerador_brl=_ZERO,
            trs_efetiva_pct=_ZERO,
            ano_referencia_irpf=ano_ref,
            defasagem_meses=None,
            acumuladores_pct_gerador=_ZERO,
            status=status,
        )


def _scan_dynamic_member_key(patrimonio: PatrimonioPayload, membro_role: str) -> Decimal:
    """Fallback para chaves dinâmicas estilo ``investimentos_david``."""
    for key, value in patrimonio.items():
        if not isinstance(key, str) or not key.startswith("investimentos_"):
            continue
        if membro_role in key.lower():
            return _to_decimal(value)
    return _ZERO


def _sum_derivativos(
    patrimonio: PatrimonioPayload,
    investimentos_atuais: HoldingsPayload | None,
) -> Decimal:
    """Soma derivativos do patrimônio + holdings com ``tipo`` derivativo."""
    total = _to_decimal(patrimonio.get("derivativos", 0))
    total += _to_decimal(patrimonio.get("derivativos_brl", 0))
    if investimentos_atuais:
        total += _sum_derivative_holdings(investimentos_atuais)
    return total


def _sum_derivative_holdings(investimentos_atuais: HoldingsPayload) -> Decimal:
    total = _ZERO
    for holding in investimentos_atuais.get("dados", []) or []:
        if not isinstance(holding, dict):
            continue
        tipo = str(holding.get("tipo", "")).lower()
        if _is_derivative_type(tipo):
            total += _to_decimal(holding.get("valor_atual", 0))
    return total


def _is_derivative_type(tipo: str) -> bool:
    return "derivativ" in tipo or "opcao" in tipo or "futuro" in tipo


def _sum_holdings_matching_tickers(
    investimentos_atuais: HoldingsPayload, tickers: set[str]
) -> Decimal:
    total = _ZERO
    for holding in investimentos_atuais.get("dados", []) or []:
        if not isinstance(holding, dict):
            continue
        if _holding_tokens(str(holding.get("nome", ""))) & tickers:
            total += _to_decimal(holding.get("valor_atual", 0))
    return total


def _aggregate_explicit_buckets(decls: list[IRPFFullOutput]) -> _RendaPassivaBuckets:
    """Agrega buckets RFB explícitos (cod 09/10/12/06) ao longo de declarações."""
    acc = _RendaPassivaBuckets()
    for d in decls:
        acc = _add_decl_to_buckets(acc, d)
    return acc


def _add_decl_to_buckets(acc: _RendaPassivaBuckets, d: IRPFFullOutput) -> _RendaPassivaBuckets:
    return _RendaPassivaBuckets(
        dividendos=acc.dividendos + _sum_isentos(d, CodigoRendimentoIsento.lucros_dividendos.value),
        jcp=acc.jcp + _sum_exclusiva(d, CodigoRendimentoTribExclusiva.jcp.value),
        aplicacoes=acc.aplicacoes
        + _sum_isentos(d, "12")
        + _sum_exclusiva(d, CodigoRendimentoTribExclusiva.rendimentos_aplicacoes_financeiras.value),
        ganho_capital=acc.ganho_capital
        + _sum_exclusiva(d, CodigoRendimentoTribExclusiva.ganho_capital.value),
        exterior=acc.exterior + _sum_exterior(d),
    )


def _sum_isentos(d: IRPFFullOutput, codigo: str) -> Decimal:
    total = _ZERO
    for r in d.rendimentos_isentos:
        if r.codigo_rfb.value == codigo:
            total += r.valor_brl
    return total


def _sum_exclusiva(d: IRPFFullOutput, codigo: str) -> Decimal:
    total = _ZERO
    for r in d.rendimentos_tributacao_exclusiva:
        if r.codigo_rfb.value == codigo:
            total += r.valor_brl
    return total


def _sum_exterior(d: IRPFFullOutput) -> Decimal:
    total = _ZERO
    for fp in d.rendimentos_exterior:
        total += fp.valor_brl
    return total


__all__ = [
    "PassiveIncomeCalculator",
    "PassiveIncomeConfig",
    "PassiveIncomeResult",
]
