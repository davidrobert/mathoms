"""Adapter ADR-216 P-A — boundary DB/SQLAlchemy ↔ service puro (ADR-097 D2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy.orm import Session

from backend.app.models.property_identity import (
    CLASSIFICATION_DESCONHECIDO,
    PropertyIdentity,
    WorkspacePropertyOverride,
)
from backend.app.repositories.market_rate_repository import (
    MarketRateNotFound,
    MarketRateRepository,
)
from pipeline.domain.services.real_estate_metrics import (
    BenchmarkRates,
    OrigemLiteral,
    PropertyInput,
    RealEstateConfig,
    RealEstateMetricsResult,
    calculate_real_estate_metrics,
)

# Convenção: market_rates pair names (ADR-216 D2 · FORMULAS.md §Imóveis).
PAIR_CDI = "CDI"
PAIR_NTNB_REAL_10Y = "NTNB_REAL_10Y"
PAIR_IFIX_YIELD_12M = "IFIX_YIELD_12M"

# Normalização nominal → líquido (FORMULAS.md §Benchmarks):
# - CDI: IR efetivo RF ponderado pela curva (default 17,5%); ADR-134 override.
# - NTN-B real: IR 15% (longo prazo); já é taxa real (acima IPCA).
# - IFIX yield: isento IR PF (FII tijolo); sem normalização.
_CDI_IR_EFETIVO_DEFAULT = Decimal("0.175")
_NTNB_IR_LONGO_PRAZO = Decimal("0.15")

_ZERO = Decimal("0")
_BRL_QUANTUM = Decimal("0.01")


def _quantize_brl(v: Decimal) -> Decimal:
    """Arredonda para centavos (boundary entre cascade D9 e service)."""
    return v.quantize(_BRL_QUANTUM)


@dataclass(frozen=True)
class IRPFAluguelEntry:
    """Linha de carnê-leão (rendimentos_pf) — hidratada do payload E1.6."""

    pagador_nome: str
    pagador_cpf_masked: str | None
    valor_brl: Decimal
    ir_recolhido_brl: Decimal
    membro_key: str | None = None


@dataclass(frozen=True)
class E4ReceitaAluguelEntry:
    """Receita categorizada como "Aluguel" no E4 (cash flow agregado)."""

    valor_total_brl: Decimal
    n_meses_periodo: int
    membro_key: str | None = None


@dataclass(frozen=True)
class CascadeSources:
    """Fontes brutas resolvidas pelo caller para cascade D9 (injeção pura, sem DB)."""

    informe_imobiliaria_by_property: Mapping[str, dict[str, Any]] = ()  # type: ignore[assignment]
    irpf_carne_leao: tuple[IRPFAluguelEntry, ...] = ()
    e4_receita_aluguel_total: E4ReceitaAluguelEntry | None = None


def fetch_benchmarks(
    db: Session,
    as_of_date: date,
    *,
    cdi_ir_efetivo_pct: Decimal | None = None,
) -> BenchmarkRates:
    """Lê 3 pairs do market_rates e normaliza para líquido (ADR-216 D2)."""
    repo = MarketRateRepository(db)
    ir_cdi = cdi_ir_efetivo_pct if cdi_ir_efetivo_pct is not None else _CDI_IR_EFETIVO_DEFAULT

    cdi_nominal = _safe_fetch_rate(repo, PAIR_CDI, as_of_date)
    ntnb_real = _safe_fetch_rate(repo, PAIR_NTNB_REAL_10Y, as_of_date)
    ifix = _safe_fetch_rate(repo, PAIR_IFIX_YIELD_12M, as_of_date)

    cdi_liq = cdi_nominal * (Decimal("1") - ir_cdi)
    ntnb_liq = ntnb_real * (Decimal("1") - _NTNB_IR_LONGO_PRAZO)
    ifix_liq = ifix

    return BenchmarkRates(
        cdi_liquido_pct=_quantize_pct(cdi_liq),
        ntnb_liquido_pct=_quantize_pct(ntnb_liq),
        ifix_yield_pct=_quantize_pct(ifix_liq),
        as_of_date=as_of_date,
    )


def _safe_fetch_rate(repo: MarketRateRepository, pair: str, as_of_date: date) -> Decimal:
    """Retorna rate ou Decimal('0') quando pair não está seedado (degradação graceful)."""
    try:
        return repo.get_rate(pair, as_of_date)
    except MarketRateNotFound:
        return _ZERO


def _quantize_pct(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"))


def build_property_inputs(
    identities: list[PropertyIdentity],
    overrides: Mapping[str, WorkspacePropertyOverride],
    valor_by_property: Mapping[str, Decimal],
    sources: CascadeSources,
    *,
    config: RealEstateConfig,
) -> list[PropertyInput]:
    """Resolve cascade D9 (Informe→IRPF→E4→none) e produz ``PropertyInput[]`` frozen."""
    valor_total_investment = _ZERO
    investment_identities: list[PropertyIdentity] = []
    for ident in identities:
        classification = _resolve_classification(ident, overrides)
        if classification in ("locado", "comercial", "especulacao"):
            v = valor_by_property.get(ident.id, _ZERO)
            valor_total_investment += v
            investment_identities.append(ident)

    aluguel_anual_irpf_total = sum((e.valor_brl for e in sources.irpf_carne_leao), _ZERO)
    ir_carne_leao_anual_irpf_total = sum(
        (e.ir_recolhido_brl for e in sources.irpf_carne_leao), _ZERO
    )

    inputs: list[PropertyInput] = []
    for ident in identities:
        classification = _resolve_classification(ident, overrides)
        valor_imovel = valor_by_property.get(ident.id, _ZERO)

        aluguel_anual: Decimal | None
        aluguel_origem: OrigemLiteral
        ir_carne_leao: Decimal | None

        informe = sources.informe_imobiliaria_by_property.get(ident.id)
        if informe is not None:
            aluguel_anual = _to_decimal(informe.get("aluguel_bruto_anual"))
            aluguel_origem = "informe"
            ir_carne_leao = _to_decimal(informe.get("ir_retido_anual"))
        elif (
            classification in ("locado", "comercial", "especulacao")
            and aluguel_anual_irpf_total > _ZERO
            and valor_total_investment > _ZERO
        ):
            # Pro-rata multiplica antes de dividir para preservar precisão Decimal.
            aluguel_anual = _quantize_brl(
                aluguel_anual_irpf_total * valor_imovel / valor_total_investment
            )
            aluguel_origem = "irpf"
            ir_carne_leao = _quantize_brl(
                ir_carne_leao_anual_irpf_total * valor_imovel / valor_total_investment
            )
        elif (
            classification in ("locado", "comercial", "especulacao")
            and sources.e4_receita_aluguel_total is not None
            and valor_total_investment > _ZERO
        ):
            e4 = sources.e4_receita_aluguel_total
            anual = (
                e4.valor_total_brl * Decimal("12") / Decimal(e4.n_meses_periodo)
                if e4.n_meses_periodo
                else _ZERO
            )
            aluguel_anual = _quantize_brl(anual * valor_imovel / valor_total_investment)
            aluguel_origem = "e4"
            ir_carne_leao = None  # adapter usa fallback do service (27,5%)
        else:
            aluguel_anual = None
            aluguel_origem = "none"
            ir_carne_leao = None

        inputs.append(
            PropertyInput(
                property_id=ident.id,
                descricao=ident.descricao_sample or ident.endereco_canonical or "(sem descrição)",
                classification=classification,
                valor_imovel=valor_imovel,
                valor_imovel_origem="irpf",
                aluguel_bruto_anual=aluguel_anual,
                aluguel_origem=aluguel_origem,
                ir_carne_leao_anual=ir_carne_leao,
                endereco_canonical=ident.endereco_canonical,
            )
        )
    return inputs


def _resolve_classification(
    ident: PropertyIdentity, overrides: Mapping[str, WorkspacePropertyOverride]
) -> str:
    """Override (DB-first) > default 'desconhecido' (FORMULAS.md §D8 · ADR-215)."""
    o = overrides.get(ident.id)
    if o is not None:
        return o.classification
    return CLASSIFICATION_DESCONHECIDO


def _to_decimal(v: Any) -> Decimal:
    if v is None:
        return _ZERO
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, str)):
        try:
            return Decimal(v)
        except Exception:
            return _ZERO
    if isinstance(v, float):
        return Decimal(str(v))
    return _ZERO


def calculate_for_workspace(
    db: Session,
    *,
    identities: list[PropertyIdentity],
    overrides: Mapping[str, WorkspacePropertyOverride],
    valor_by_property: Mapping[str, Decimal],
    sources: CascadeSources,
    concentracao_imobiliaria_pct: Decimal,
    as_of_date: date,
    config: RealEstateConfig | None = None,
    cdi_ir_efetivo_pct: Decimal | None = None,
) -> RealEstateMetricsResult:
    """Entry point: hidrata + busca benchmarks + chama service. Tudo no boundary backend/."""
    cfg = config or RealEstateConfig()
    benchmarks = fetch_benchmarks(db, as_of_date, cdi_ir_efetivo_pct=cdi_ir_efetivo_pct)
    inputs = build_property_inputs(
        identities=identities,
        overrides=overrides,
        valor_by_property=valor_by_property,
        sources=sources,
        config=cfg,
    )
    return calculate_real_estate_metrics(
        properties=inputs,
        concentracao_imobiliaria_pct=concentracao_imobiliaria_pct,
        benchmarks=benchmarks,
        config=cfg,
    )


__all__ = [
    "CascadeSources",
    "E4ReceitaAluguelEntry",
    "IRPFAluguelEntry",
    "PAIR_CDI",
    "PAIR_IFIX_YIELD_12M",
    "PAIR_NTNB_REAL_10Y",
    "build_property_inputs",
    "calculate_for_workspace",
    "fetch_benchmarks",
]
