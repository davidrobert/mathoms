"""Agregação de componentes + alertas (Onda 2 · ADR-216)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.real_estate_metrics import (
    Alerta,
    BenchmarkRates,
    ComponenteCalculo,
    OrigemLiteral,
    PropertyInput,
    RealEstateConfig,
    _confidence_for,
)

_ZERO = Decimal("0")
_TWELVE = Decimal("12")
_BRL_QUANTUM = Decimal("0.01")


def _quantize_brl(v: Decimal) -> Decimal:
    """Arredonda valor monetário para centavos."""
    return v.quantize(_BRL_QUANTUM)


def _dominant_origem(samples: list[tuple[Decimal, OrigemLiteral]]) -> OrigemLiteral:
    """Origem do imóvel com maior valor (modo por valor monetário)."""
    non_zero = [(v, o) for v, o in samples if v > _ZERO]
    if not non_zero:
        return "default"
    non_zero.sort(key=lambda t: t[0], reverse=True)
    return non_zero[0][1]


def aggregate_componentes(
    properties: list[PropertyInput],
    config: RealEstateConfig,
) -> dict[str, ComponenteCalculo]:
    """Soma componentes anuais e propaga ``origem`` dominante (por valor) da cascade D9."""
    if not properties:
        zero = ComponenteCalculo(valor=_ZERO, origem="default", confidence="low")
        return {
            "aluguel_anual_bruto": zero,
            "taxa_administracao_anual": zero,
            "ir_retido_anual": zero,
            "ir_carne_leao_anual": zero,
            "iptu_anual": zero,
            "condominio_anual": zero,
            "manutencao_anual": zero,
            "vacancia_anual": zero,
            "valor_total_imoveis": zero,
        }

    aluguel = sum((p.aluguel_bruto_anual or _ZERO for p in properties), _ZERO)
    taxa_adm = sum((p.taxa_administracao_anual or _ZERO for p in properties), _ZERO)
    ir_retido = sum((p.ir_retido_anual for p in properties), _ZERO)
    iptu = sum((p.iptu_anual or _ZERO for p in properties), _ZERO)
    condominio = sum((p.condominio_anual or _ZERO for p in properties), _ZERO)
    valor_total = sum((p.valor_imovel for p in properties), _ZERO)

    manutencao = valor_total * config.manutencao_pct

    vacancia = _ZERO
    for p in properties:
        aluguel_p = p.aluguel_bruto_anual or _ZERO
        if p.meses_locado_no_ano is not None and 0 <= p.meses_locado_no_ano <= 12:
            vacancia += aluguel_p * (_TWELVE - Decimal(p.meses_locado_no_ano)) / _TWELVE
        else:
            vacancia += aluguel_p * config.vacancia_pct

    # IR carnê-leão per-property (alíquota marginal pode variar quando IRPF disponível).
    ir_carne_leao = _ZERO
    biggest_value_irpf = _ZERO
    biggest_value_fallback = _ZERO
    for p in properties:
        aluguel_p = p.aluguel_bruto_anual or _ZERO
        if aluguel_p == _ZERO:
            continue
        if p.ir_carne_leao_anual is not None:
            ir_carne_leao += p.ir_carne_leao_anual
            if aluguel_p > biggest_value_irpf:
                biggest_value_irpf = aluguel_p
        else:
            ir_carne_leao += aluguel_p * config.ir_carne_leao_fallback_pct
            if aluguel_p > biggest_value_fallback:
                biggest_value_fallback = aluguel_p
    ir_origem_dominante: OrigemLiteral = (
        "irpf" if biggest_value_irpf >= biggest_value_fallback else "default"
    )

    aluguel_origem = _dominant_origem(
        [(p.aluguel_bruto_anual or _ZERO, p.aluguel_origem) for p in properties]
    )
    iptu_origem = _dominant_origem([(p.iptu_anual or _ZERO, p.iptu_origem) for p in properties])
    condominio_origem = _dominant_origem(
        [(p.condominio_anual or _ZERO, p.condominio_origem) for p in properties]
    )
    taxa_adm_origem: OrigemLiteral = "informe" if taxa_adm > _ZERO else "default"
    ir_retido_origem: OrigemLiteral = "informe" if ir_retido > _ZERO else "default"

    def _make(valor: Decimal, origem: OrigemLiteral) -> ComponenteCalculo:
        return ComponenteCalculo(
            valor=_quantize_brl(valor), origem=origem, confidence=_confidence_for(origem)
        )

    vacancia_origem: OrigemLiteral = (
        "informe"
        if any(
            p.meses_locado_no_ano is not None
            for p in properties
            if (p.aluguel_bruto_anual or _ZERO) > _ZERO
        )
        else "default"
    )

    return {
        "aluguel_anual_bruto": _make(aluguel, aluguel_origem),
        "taxa_administracao_anual": _make(taxa_adm, taxa_adm_origem),
        "ir_retido_anual": _make(ir_retido, ir_retido_origem),
        "ir_carne_leao_anual": _make(ir_carne_leao, ir_origem_dominante),
        "iptu_anual": _make(iptu, iptu_origem),
        "condominio_anual": _make(condominio, condominio_origem),
        "manutencao_anual": _make(manutencao, "default"),
        "vacancia_anual": _make(vacancia, vacancia_origem),
        "valor_total_imoveis": _make(valor_total, "irpf"),
    }


def compute_alertas(
    cap_rate_liquido_pct: Decimal | None,
    concentracao_pct: Decimal,
    benchmarks: BenchmarkRates,
    properties: list[PropertyInput],
    config: RealEstateConfig,
) -> list[Alerta]:
    """Gera alertas canônicos (FORMULAS.md §Alertas)."""
    alertas: list[Alerta] = []

    if concentracao_pct > config.concentracao_alerta_pct:
        conc_br = f"{concentracao_pct:.1f}".replace(".", ",")
        alertas.append(
            Alerta(
                code="concentracao_alta",
                severity="warning",
                context=(
                    f"Concentração em imóveis ({conc_br}%) acima de "
                    f"{config.concentracao_alerta_pct:.0f}% da carteira produtiva — "
                    f"revisão de alocação recomendada."
                ),
            )
        )

    if (
        cap_rate_liquido_pct is not None
        and benchmarks.cdi_liquido_pct > _ZERO
        and cap_rate_liquido_pct
        < config.spread_critico_pct_do_benchmark * benchmarks.cdi_liquido_pct
        and concentracao_pct > config.spread_critico_concentracao_minima_pct
    ):
        alertas.append(
            Alerta(
                code="spread_critico",
                severity="warning",
                context=(
                    f"Cap rate líquido ({f'{cap_rate_liquido_pct:.2f}'.replace('.', ',')}%) < "
                    f"{int(config.spread_critico_pct_do_benchmark * 100)}% do CDI líquido "
                    f"({f'{benchmarks.cdi_liquido_pct:.2f}'.replace('.', ',')}%) combinado com concentração imobiliária "
                    f"acima de {config.spread_critico_concentracao_minima_pct:.0f}% da carteira produtiva — "
                    f"considerar revisão estratégica."
                ),
            )
        )

    if properties and all(p.aluguel_origem == "pro_rata" for p in properties):
        alertas.append(
            Alerta(
                code="aluguel_sem_dado",
                severity="info",
                context=(
                    "Aluguel por imóvel estimado — para precisão, carregue o "
                    "Informe de Rendimentos da Imobiliária."
                ),
            )
        )

    for p in properties:
        if (
            p.meses_desde_ultimo_reajuste is not None
            and p.meses_desde_ultimo_reajuste > config.contrato_reajuste_pendente_meses
        ):
            alertas.append(
                Alerta(
                    code="contrato_reajuste_pendente",
                    severity="info",
                    context=(
                        f"{p.descricao}: contrato sem reajuste há "
                        f"{p.meses_desde_ultimo_reajuste} meses."
                    ),
                )
            )

    return alertas


__all__ = ["aggregate_componentes", "compute_alertas"]
