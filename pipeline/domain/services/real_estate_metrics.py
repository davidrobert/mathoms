"""``RealEstateMetricsCalculator`` — cap rate liquido + benchmarks + concentracao (Onda 2 · ADR-216)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal

# Classification enum espelhado de backend/app/models/property_identity.py (ADR-215 + ADR-235).
# Source of truth é o modelo; aqui replicamos como literal para evitar import cross-boundary
# (pipeline/ não importa backend/).
ClassificationLiteral = Literal[
    "residencia_principal",
    "uso_pessoal",
    "locado",
    "comercial",
    "especulacao",
    "nu_proprietario",
    "desconhecido",
]

# S4 filtra apenas classes de investimento (ADR-216 D8). ADR-235: nu_proprietario
# permanece fora — cap rate indefinido (não puxa média do portfolio).
INVESTMENT_CLASSIFICATIONS: tuple[str, ...] = ("locado", "comercial", "especulacao")

OrigemLiteral = Literal["informe", "irpf", "e3", "e4", "manual", "pro_rata", "none", "default"]
ConfidenceLiteral = Literal["high", "medium", "low"]

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")
_TWELVE = Decimal("12")
_PCT_QUANTUM = Decimal("0.01")
_BRL_QUANTUM = Decimal("0.01")


# =============================================================================
# Config (ADR-216 D6 · FORMULAS.md §Imóveis)
# =============================================================================


@dataclass(frozen=True)
class RealEstateConfig:
    """Defaults configuráveis (FORMULAS.md §Imóveis · ADR-134 override por workspace)."""

    vacancia_pct: Decimal = Decimal("0.15")
    manutencao_pct: Decimal = Decimal("0.01")
    ir_carne_leao_fallback_pct: Decimal = Decimal("0.275")
    concentracao_alerta_pct: Decimal = Decimal("40.0")
    spread_critico_pct_do_benchmark: Decimal = Decimal("0.70")
    spread_critico_concentracao_minima_pct: Decimal = Decimal("30.0")
    contrato_reajuste_pendente_meses: int = 12


@dataclass(frozen=True)
class BenchmarkRates:
    """Tríade de benchmarks já normalizada para líquido (ADR-216 D2 · FORMULAS.md)."""

    cdi_liquido_pct: Decimal
    ntnb_liquido_pct: Decimal
    ifix_yield_pct: Decimal
    as_of_date: date


# =============================================================================
# Input value objects (ADR-097 D3)
# =============================================================================


@dataclass(frozen=True)
class PropertyInput:
    """Imóvel + dados resolvidos pela cascade D9 (preenchido pelo adapter)."""

    property_id: str
    descricao: str
    classification: str
    valor_imovel: Decimal
    valor_imovel_origem: Literal["irpf", "mercado"] = "irpf"

    aluguel_bruto_anual: Decimal | None = None
    aluguel_origem: OrigemLiteral = "default"
    taxa_administracao_anual: Decimal | None = None
    ir_retido_anual: Decimal = _ZERO
    ir_carne_leao_anual: Decimal | None = None
    iptu_anual: Decimal | None = None
    iptu_origem: OrigemLiteral = "default"
    condominio_anual: Decimal | None = None
    condominio_origem: OrigemLiteral = "default"
    meses_locado_no_ano: int | None = None

    data_ultimo_reajuste: str | None = None
    indice_reajuste: str | None = None
    endereco_canonical: str | None = None
    imobiliaria_cnpj: str | None = None
    imobiliaria_nome: str | None = None
    meses_desde_ultimo_reajuste: int | None = None


# =============================================================================
# Result dataclasses
# =============================================================================


@dataclass(frozen=True)
class PropertyMetrics:
    """Métricas calculadas por imóvel (entra em ``real_estate.imoveis[]``)."""

    property_id: str
    descricao: str
    classification: str
    valor_imovel: Decimal
    valor_imovel_origem: str

    aluguel_mensal_bruto: Decimal | None
    taxa_administracao_mensal: Decimal | None
    iptu_mensal: Decimal | None
    condominio_mensal: Decimal | None
    ir_retido_mensal: Decimal
    meses_locado_no_ano: int | None
    vacancia_pct_empirica: Decimal | None

    cap_rate_bruto_pct: Decimal | None
    cap_rate_liquido_pct: Decimal | None
    gap_reajuste_pct: Decimal | None
    status_contrato: Literal["atualizado", "reajuste_pendente", "sem_renda", "desconhecido"]

    indice_reajuste: str | None
    data_ultimo_reajuste: str | None
    endereco_canonical: str | None
    imobiliaria_cnpj: str | None
    imobiliaria_nome: str | None
    origem_aluguel: OrigemLiteral


@dataclass(frozen=True)
class ComponenteCalculo:
    """Componente da fórmula líquida agregada — valor + origem + confiança (cascade D9)."""

    valor: Decimal
    origem: OrigemLiteral
    confidence: ConfidenceLiteral


# Map cascade origens → confidence (FORMULAS.md §D9 + data-engineer review 2026-05-15).
# - high: fonte primária com dado bruto declarado (informe da imobiliária, manual)
# - medium: fonte secundária derivada (irpf carnê-leão, transação E3, E4 agregado)
# - low: estimativa/default (pro_rata, default 1%, default 15%)
_ORIGEM_CONFIDENCE: dict[str, ConfidenceLiteral] = {
    "informe": "high",
    "manual": "high",
    "irpf": "medium",
    "e3": "medium",
    "e4": "medium",
    "pro_rata": "low",
    "default": "low",
    "none": "low",
}


def _confidence_for(origem: OrigemLiteral) -> ConfidenceLiteral:
    return _ORIGEM_CONFIDENCE.get(origem, "low")


@dataclass(frozen=True)
class Alerta:
    """Alerta canônico (FORMULAS.md §Alertas)."""

    code: Literal[
        "concentracao_alta", "spread_critico", "aluguel_sem_dado", "contrato_reajuste_pendente"
    ]
    severity: Literal["info", "warning", "critical"]
    context: str


@dataclass(frozen=True)
class ExcludedProperty:
    """Imóvel filtrado por classification (não-investimento) — transparência no UI."""

    property_id: str
    descricao: str
    classification: str
    motivo: str


@dataclass(frozen=True)
class RealEstateMetricsResult:
    """Output do calculator — pronto para serializar via ``to_payload()``."""

    cap_rate_liquido_pct: Decimal | None
    cap_rate_bruto_pct: Decimal | None
    componentes_calculo: dict[str, ComponenteCalculo]
    benchmarks: BenchmarkRates
    spreads_pp: dict[str, Decimal]
    spread_brl_anual: dict[str, Decimal]
    concentracao_pct: Decimal
    imoveis: list[PropertyMetrics]
    excluded_properties: list[ExcludedProperty]
    alertas: list[Alerta]
    valor_total_imoveis: Decimal


# =============================================================================
# Helpers
# =============================================================================


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
        # ADR-090: float só via str(v) para preservar a string-printed form.
        return Decimal(str(value))
    return _ZERO


def _safe_div(numerator: Decimal, denominator: Decimal) -> Decimal:
    """Divisão segura — retorna 0 se denominador for 0."""
    if denominator == _ZERO:
        return _ZERO
    return numerator / denominator


def _quantize_pct(v: Decimal) -> Decimal:
    """Arredonda percentual para 2 casas decimais."""
    return v.quantize(_PCT_QUANTUM)


def _quantize_brl(v: Decimal) -> Decimal:
    """Arredonda valor monetário para centavos."""
    return v.quantize(_BRL_QUANTUM)


def _status_contrato_for(
    aluguel_bruto: Decimal | None,
    meses_desde_reajuste: int | None,
    pendente_threshold: int,
) -> Literal["atualizado", "reajuste_pendente", "sem_renda", "desconhecido"]:
    """Determina ``status_contrato`` para badge da tabela por imóvel (UI)."""
    if aluguel_bruto is None or aluguel_bruto == _ZERO:
        return "sem_renda"
    if meses_desde_reajuste is None:
        return "desconhecido"
    if meses_desde_reajuste > pendente_threshold:
        return "reajuste_pendente"
    return "atualizado"


# =============================================================================
# Cálculo por imóvel
# =============================================================================


def _compute_property_metrics(
    prop: PropertyInput,
    config: RealEstateConfig,
) -> PropertyMetrics:
    """Calcula cap rate bruto + líquido por imóvel."""
    aluguel_bruto = prop.aluguel_bruto_anual

    if aluguel_bruto is None or aluguel_bruto <= _ZERO:
        return PropertyMetrics(
            property_id=prop.property_id,
            descricao=prop.descricao,
            classification=prop.classification,
            valor_imovel=prop.valor_imovel,
            valor_imovel_origem=prop.valor_imovel_origem,
            aluguel_mensal_bruto=None,
            taxa_administracao_mensal=None,
            iptu_mensal=None,
            condominio_mensal=None,
            ir_retido_mensal=_ZERO,
            meses_locado_no_ano=prop.meses_locado_no_ano,
            vacancia_pct_empirica=None,
            cap_rate_bruto_pct=None,
            cap_rate_liquido_pct=None,
            gap_reajuste_pct=None,
            status_contrato="sem_renda",
            indice_reajuste=prop.indice_reajuste,
            data_ultimo_reajuste=prop.data_ultimo_reajuste,
            endereco_canonical=prop.endereco_canonical,
            imobiliaria_cnpj=prop.imobiliaria_cnpj,
            imobiliaria_nome=prop.imobiliaria_nome,
            origem_aluguel=prop.aluguel_origem,
        )

    taxa_adm = prop.taxa_administracao_anual or _ZERO
    ir_retido = prop.ir_retido_anual

    # IR carnê-leão: derivado (irpf) ou fallback 27,5% (ADR-216 D6 · FORMULAS.md).
    if prop.ir_carne_leao_anual is not None:
        ir_carne_leao = prop.ir_carne_leao_anual
    else:
        ir_carne_leao = aluguel_bruto * config.ir_carne_leao_fallback_pct

    # IPTU/condomínio: do informe/E4 ou ausentes (default `0` para condomínio
    # quando não informado; IPTU usa default 1% do valor quando ausente é
    # decisão controversa — para v1, default IPTU = 0 quando ausente para não
    # inventar custo, e UI sinaliza via `origem == "default"`).
    iptu = prop.iptu_anual if prop.iptu_anual is not None else _ZERO
    condominio = prop.condominio_anual if prop.condominio_anual is not None else _ZERO

    # Manutenção: regra de bolso 1% do valor (FORMULAS.md §Defaults gradação 0,5/1/2-3%).
    manutencao = prop.valor_imovel * config.manutencao_pct

    # Vacância empírica (Informe traz meses_locado) ou default 15% (FORMULAS.md).
    if prop.meses_locado_no_ano is not None and 0 <= prop.meses_locado_no_ano <= 12:
        vacancia_pct_empirica = (_TWELVE - Decimal(prop.meses_locado_no_ano)) / _TWELVE
        vacancia = aluguel_bruto * vacancia_pct_empirica
    else:
        vacancia_pct_empirica = None
        vacancia = aluguel_bruto * config.vacancia_pct

    aluguel_liquido = (
        aluguel_bruto
        - taxa_adm
        - ir_retido
        - ir_carne_leao
        - iptu
        - condominio
        - manutencao
        - vacancia
    )

    cap_rate_bruto_pct = _quantize_pct(_safe_div(aluguel_bruto, prop.valor_imovel) * _HUNDRED)
    cap_rate_liquido_pct = _quantize_pct(_safe_div(aluguel_liquido, prop.valor_imovel) * _HUNDRED)

    # Gap de reajuste — fórmula da FORMULAS.md §D6. Sem índice acumulado disponível
    # nesta camada (vive em market_rates ou fiscal_parameters), deixar None.
    gap_reajuste_pct: Decimal | None = None

    status = _status_contrato_for(
        aluguel_bruto,
        prop.meses_desde_ultimo_reajuste,
        config.contrato_reajuste_pendente_meses,
    )

    return PropertyMetrics(
        property_id=prop.property_id,
        descricao=prop.descricao,
        classification=prop.classification,
        valor_imovel=prop.valor_imovel,
        valor_imovel_origem=prop.valor_imovel_origem,
        aluguel_mensal_bruto=_quantize_brl(aluguel_bruto / _TWELVE),
        taxa_administracao_mensal=_quantize_brl(taxa_adm / _TWELVE) if taxa_adm > _ZERO else None,
        iptu_mensal=_quantize_brl(iptu / _TWELVE) if iptu > _ZERO else None,
        condominio_mensal=_quantize_brl(condominio / _TWELVE) if condominio > _ZERO else None,
        ir_retido_mensal=_quantize_brl(ir_retido / _TWELVE),
        meses_locado_no_ano=prop.meses_locado_no_ano,
        vacancia_pct_empirica=_quantize_pct(vacancia_pct_empirica * _HUNDRED)
        if vacancia_pct_empirica is not None
        else None,
        cap_rate_bruto_pct=cap_rate_bruto_pct,
        cap_rate_liquido_pct=cap_rate_liquido_pct,
        gap_reajuste_pct=gap_reajuste_pct,
        status_contrato=status,
        indice_reajuste=prop.indice_reajuste,
        data_ultimo_reajuste=prop.data_ultimo_reajuste,
        endereco_canonical=prop.endereco_canonical,
        imobiliaria_cnpj=prop.imobiliaria_cnpj,
        imobiliaria_nome=prop.imobiliaria_nome,
        origem_aluguel=prop.aluguel_origem,
    )


# =============================================================================
# Agregação + benchmarks + alertas
# =============================================================================


_CLASSIFICATION_MOTIVO: dict[str, str] = {
    "residencia_principal": "Residência principal — não conta como investimento (cat_1).",
    "uso_pessoal": "Imóvel de uso pessoal/familiar — não gera renda de aluguel.",
    "desconhecido": "Classificação pendente — usuário precisa rotular em Configurações.",
}


def filter_investment_properties(
    properties: list[PropertyInput],
) -> tuple[list[PropertyInput], list[ExcludedProperty]]:
    """Filtra investimento e devolve excluídos com motivo (ADR-216 D8 · ADR-215 enum)."""
    investment: list[PropertyInput] = []
    excluded: list[ExcludedProperty] = []
    for p in properties:
        if p.classification in INVESTMENT_CLASSIFICATIONS:
            investment.append(p)
        else:
            motivo = _CLASSIFICATION_MOTIVO.get(
                p.classification, f"Classification '{p.classification}' não é investimento."
            )
            excluded.append(
                ExcludedProperty(
                    property_id=p.property_id,
                    descricao=p.descricao,
                    classification=p.classification,
                    motivo=motivo,
                )
            )
    return investment, excluded


def calculate_real_estate_metrics(
    properties: list[PropertyInput],
    patrimonio_liquido: Decimal,
    benchmarks: BenchmarkRates,
    config: RealEstateConfig | None = None,
) -> RealEstateMetricsResult:
    """Calcula payload `real_estate` (ADR-216) sobre imóveis de investimento."""
    cfg = config or RealEstateConfig()

    from pipeline.domain.services.real_estate_metrics_aggregator import (
        aggregate_componentes,
        compute_alertas,
    )

    investment, excluded = filter_investment_properties(properties)
    # Sort por valor para tabela determinística (UI mostra maiores primeiro).
    properties_sorted = sorted(investment, key=lambda p: p.valor_imovel, reverse=True)
    per_property = [_compute_property_metrics(p, cfg) for p in properties_sorted]
    componentes = aggregate_componentes(properties_sorted, cfg)

    valor_total = componentes["valor_total_imoveis"].valor
    aluguel_total = componentes["aluguel_anual_bruto"].valor

    cap_rate_bruto_pct: Decimal | None = None
    cap_rate_liquido_pct: Decimal | None = None
    if valor_total > _ZERO:
        liquido_anual = (
            aluguel_total
            - componentes["taxa_administracao_anual"].valor
            - componentes["ir_retido_anual"].valor
            - componentes["ir_carne_leao_anual"].valor
            - componentes["iptu_anual"].valor
            - componentes["condominio_anual"].valor
            - componentes["manutencao_anual"].valor
            - componentes["vacancia_anual"].valor
        )
        cap_rate_bruto_pct = _quantize_pct(_safe_div(aluguel_total, valor_total) * _HUNDRED)
        cap_rate_liquido_pct = _quantize_pct(_safe_div(liquido_anual, valor_total) * _HUNDRED)

    concentracao_pct = (
        _quantize_pct(_safe_div(valor_total, patrimonio_liquido) * _HUNDRED)
        if patrimonio_liquido > _ZERO
        else _ZERO
    )

    spreads_pp: dict[str, Decimal] = {}
    spread_brl_anual: dict[str, Decimal] = {}
    if cap_rate_liquido_pct is not None:
        for label, bench in (
            ("vs_cdi", benchmarks.cdi_liquido_pct),
            ("vs_ntnb", benchmarks.ntnb_liquido_pct),
            ("vs_ifix", benchmarks.ifix_yield_pct),
        ):
            spread_pp = _quantize_pct(cap_rate_liquido_pct - bench)
            spread_brl = _quantize_brl(valor_total * spread_pp / _HUNDRED)
            spreads_pp[label] = spread_pp
            spread_brl_anual[label] = spread_brl

    alertas = compute_alertas(
        cap_rate_liquido_pct, concentracao_pct, benchmarks, properties_sorted, cfg
    )

    return RealEstateMetricsResult(
        cap_rate_liquido_pct=cap_rate_liquido_pct,
        cap_rate_bruto_pct=cap_rate_bruto_pct,
        componentes_calculo=componentes,
        benchmarks=benchmarks,
        spreads_pp=spreads_pp,
        spread_brl_anual=spread_brl_anual,
        concentracao_pct=concentracao_pct,
        imoveis=per_property,
        excluded_properties=excluded,
        alertas=alertas,
        valor_total_imoveis=valor_total,
    )


__all__ = [
    "INVESTMENT_CLASSIFICATIONS",
    "Alerta",
    "BenchmarkRates",
    "ComponenteCalculo",
    "ConfidenceLiteral",
    "ExcludedProperty",
    "OrigemLiteral",
    "PropertyInput",
    "PropertyMetrics",
    "RealEstateConfig",
    "RealEstateMetricsResult",
    "calculate_real_estate_metrics",
    "filter_investment_properties",
    "result_to_payload",
]


# Re-export do serializer (split em real_estate_metrics_payload para boundary ≤500 linhas).
from pipeline.domain.services.real_estate_metrics_payload import (
    result_to_payload as result_to_payload,
)  # noqa: E402
