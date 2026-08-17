"""Conversão ME→BRL com proveniência (ADR-390 · A40.l63).

O conversor não escolhe a taxa: o caller entrega cotação, identidade ou
default nomeado. Sem ConfigStore, sem date.today(), sem cache.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Mapping

_logger = logging.getLogger("mathoms.pipeline.conversao_me")

TaxaFonte = Literal[
    "ptax_31_12",
    "market_rate_corrente",
    "default_hardcoded",
    "irpf_ja_em_brl",
]
ConversaoStatus = Literal["converted", "identity", "missing_rate"]

_USD_KEYWORDS = ("dolar", "u$", "us$", "usd")
_EUR_KEYWORDS = ("euro", "eur")


@dataclass(frozen=True)
class FxQuote:
    """Cotação que o caller já escolheu (ADR-390 D1)."""

    rate: Decimal
    fonte: TaxaFonte
    observed_at: str | None = None


@dataclass(frozen=True)
class HardcodedFxDefault:
    """Default histórico nomeado — política do caller, não fallback interno."""

    pair: str
    rate: Decimal

    @classmethod
    def usd_brl(cls) -> HardcodedFxDefault:
        return cls(pair="USD/BRL", rate=Decimal("5.80"))

    @classmethod
    def eur_brl(cls) -> HardcodedFxDefault:
        return cls(pair="EUR/BRL", rate=Decimal("6.35"))

    @classmethod
    def for_moeda(cls, moeda: str) -> HardcodedFxDefault | None:
        table = {"USD": cls.usd_brl, "EUR": cls.eur_brl}
        factory = table.get(moeda.upper())
        return factory() if factory else None


@dataclass(frozen=True)
class ConversaoMeBrl:
    """Carimbo da conversão. `valor_brl` None = linha fora do total BRL."""

    valor_brl: Decimal | None
    taxa: Decimal | None
    taxa_data: str | None
    taxa_fonte: TaxaFonte | None
    status: ConversaoStatus
    moeda: str
    saldo_original: Decimal

    def to_wire(self) -> dict:
        return {
            "taxa": _taxa_str(self.taxa),
            "taxa_data": self.taxa_data,
            "taxa_fonte": self.taxa_fonte,
            "status": self.status,
        }


def convert_me_brl(amount: object, moeda: str, quote: FxQuote) -> ConversaoMeBrl:
    """Multiplica e carimba. Único sítio que faz `amount * rate`."""
    saldo = _to_decimal(amount)
    return ConversaoMeBrl(
        valor_brl=saldo * quote.rate,
        taxa=quote.rate,
        taxa_data=quote.observed_at,
        taxa_fonte=quote.fonte,
        status="converted",
        moeda=moeda.upper(),
        saldo_original=saldo,
    )


def identity_already_brl(amount: object) -> ConversaoMeBrl:
    """IRPF já veio em BRL — não reconverte, não inventa original em ME."""
    saldo = _to_decimal(amount)
    return ConversaoMeBrl(
        valor_brl=saldo,
        taxa=None,
        taxa_data=None,
        taxa_fonte="irpf_ja_em_brl",
        status="identity",
        moeda="BRL",
        saldo_original=saldo,
    )


def identity_native_brl(amount: object) -> ConversaoMeBrl:
    """Caixa já em BRL (extrato nacional)."""
    saldo = _to_decimal(amount)
    return ConversaoMeBrl(
        valor_brl=saldo,
        taxa=Decimal("1"),
        taxa_data=None,
        taxa_fonte=None,
        status="identity",
        moeda="BRL",
        saldo_original=saldo,
    )


def missing_rate(amount: object, moeda: str) -> ConversaoMeBrl:
    """Sem cotação e sem default nomeado — não inventa BRL."""
    saldo = _to_decimal(amount)
    return ConversaoMeBrl(
        valor_brl=None,
        taxa=None,
        taxa_data=None,
        taxa_fonte=None,
        status="missing_rate",
        moeda=moeda.upper(),
        saldo_original=saldo,
    )


def convert_with_hardcoded(
    amount: object, moeda: str, default: HardcodedFxDefault
) -> ConversaoMeBrl:
    quote = FxQuote(rate=default.rate, fonte="default_hardcoded")
    return convert_me_brl(amount, moeda, quote)


def apply_fx(
    amount: object, moeda: str, resolved: FxQuote | HardcodedFxDefault | None
) -> ConversaoMeBrl:
    """Despacha identidade / quote / hardcoded / missing. BRL nativo ignora resolved."""
    if moeda.upper() == "BRL":
        return identity_native_brl(amount)
    if isinstance(resolved, FxQuote):
        return convert_me_brl(amount, moeda, resolved)
    if isinstance(resolved, HardcodedFxDefault):
        return convert_with_hardcoded(amount, moeda, resolved)
    return missing_rate(amount, moeda)


def resolve_fx_input(
    moeda: str,
    *,
    typed_usd: object | None,
    typed_eur: object | None,
    taxas: Mapping[str, object],
) -> FxQuote | HardcodedFxDefault | None:
    """Monta a entrada do conversor a partir das taxas que o caller já tem."""
    code = moeda.upper()
    typed = {"USD": typed_usd, "EUR": typed_eur}.get(code)
    if typed is not None:
        return FxQuote(rate=_to_decimal(typed), fonte="market_rate_corrente")
    key = {"USD": "cambio_usd_brl", "EUR": "cambio_eur_brl"}.get(code)
    if key and taxas.get(key) is not None:
        return FxQuote(rate=_to_decimal(taxas[key]), fonte="market_rate_corrente")
    return HardcodedFxDefault.for_moeda(code)


def from_informe_entry(entry: Mapping[str, object]) -> ConversaoMeBrl:
    """Copia a conversão do informe — não remultiplica (ADR-390)."""
    moeda = str(entry.get("moeda") or "USD")
    original = _to_decimal(entry.get("saldo_original") or 0)
    if entry.get("saldo_brl") is None or entry.get("ptax_status") == "missing":
        return missing_rate(original, moeda)
    taxa_raw = entry.get("taxa_ptax_aplicada")
    return ConversaoMeBrl(
        valor_brl=_to_decimal(entry["saldo_brl"]),
        taxa=_to_decimal(taxa_raw) if taxa_raw is not None else None,
        taxa_data=_as_str_or_none(entry.get("ptax_data")),
        taxa_fonte="ptax_31_12",
        status="converted",
        moeda=moeda.upper(),
        saldo_original=original,
    )


def infer_declared_me_currency(text: str) -> str | None:
    """Moeda de origem declarada no texto (exposição), não unidade do saldo."""
    lowered = text.lower()
    if any(kw in lowered for kw in _USD_KEYWORDS):
        return "USD"
    if any(kw in lowered for kw in _EUR_KEYWORDS):
        return "EUR"
    return None


def warn_hardcoded(par: str, n_linhas: int) -> None:
    if n_linhas <= 0:
        return
    _logger.warning("fx_default_hardcoded", extra={"par": par, "n_linhas": n_linhas})


def _to_decimal(v: object) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _taxa_str(taxa: Decimal | None) -> str | None:
    return format(taxa, "f") if taxa is not None else None


def _as_str_or_none(v: object) -> str | None:
    if v is None:
        return None
    return str(v)
