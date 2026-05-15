"""Serialização do ``RealEstateMetricsResult`` para o shape do schema E5 (Onda 2 · ADR-216)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.real_estate_metrics import RealEstateMetricsResult


def _decimal_to_payload(v: Decimal | None) -> float | None:
    """Decimal → float (ADR-209 alinhado com resto do E5; débito Decimal-string conhecido)."""
    if v is None:
        return None
    return float(v)


def result_to_payload(result: RealEstateMetricsResult) -> dict[str, object]:
    """Serializa ``RealEstateMetricsResult`` para o shape do schema E5 (chave `real_estate`)."""
    componentes = {
        key: {
            "valor": _decimal_to_payload(c.valor),
            "origem": c.origem,
            "confidence": c.confidence,
        }
        for key, c in result.componentes_calculo.items()
    }

    benchmarks = {
        "cdi_liquido_pct": _decimal_to_payload(result.benchmarks.cdi_liquido_pct),
        "ntnb_liquido_pct": _decimal_to_payload(result.benchmarks.ntnb_liquido_pct),
        "ifix_yield_pct": _decimal_to_payload(result.benchmarks.ifix_yield_pct),
        "as_of_date": result.benchmarks.as_of_date.isoformat(),
    }

    imoveis = [
        {
            "property_id": p.property_id,
            "descricao": p.descricao,
            "classification": p.classification,
            "valor_imovel": _decimal_to_payload(p.valor_imovel),
            "valor_imovel_origem": p.valor_imovel_origem,
            "aluguel_mensal_bruto": _decimal_to_payload(p.aluguel_mensal_bruto),
            "taxa_administracao_mensal": _decimal_to_payload(p.taxa_administracao_mensal),
            "iptu_mensal": _decimal_to_payload(p.iptu_mensal),
            "condominio_mensal": _decimal_to_payload(p.condominio_mensal),
            "ir_retido_mensal": _decimal_to_payload(p.ir_retido_mensal),
            "meses_locado_no_ano": p.meses_locado_no_ano,
            "vacancia_pct_empirica": _decimal_to_payload(p.vacancia_pct_empirica),
            "cap_rate_bruto_pct": _decimal_to_payload(p.cap_rate_bruto_pct),
            "cap_rate_liquido_pct": _decimal_to_payload(p.cap_rate_liquido_pct),
            "gap_reajuste_pct": _decimal_to_payload(p.gap_reajuste_pct),
            "status_contrato": p.status_contrato,
            "indice_reajuste": p.indice_reajuste,
            "data_ultimo_reajuste": p.data_ultimo_reajuste,
            "endereco_canonical": p.endereco_canonical,
            "imobiliaria_cnpj": p.imobiliaria_cnpj,
            "imobiliaria_nome": p.imobiliaria_nome,
            "origem_aluguel": p.origem_aluguel,
        }
        for p in result.imoveis
    ]

    return {
        "cap_rate_liquido_pct": _decimal_to_payload(result.cap_rate_liquido_pct),
        "cap_rate_bruto_pct": _decimal_to_payload(result.cap_rate_bruto_pct),
        "componentes_calculo": componentes,
        "benchmarks": benchmarks,
        "spreads_pp": {k: _decimal_to_payload(v) for k, v in result.spreads_pp.items()},
        "spread_brl_anual": {k: _decimal_to_payload(v) for k, v in result.spread_brl_anual.items()},
        "concentracao_pct": _decimal_to_payload(result.concentracao_pct),
        "valor_total_imoveis": _decimal_to_payload(result.valor_total_imoveis),
        "imoveis": imoveis,
        "excluded_properties": [
            {
                "property_id": e.property_id,
                "descricao": e.descricao,
                "classification": e.classification,
                "motivo": e.motivo,
            }
            for e in result.excluded_properties
        ],
        "alertas": [
            {"code": a.code, "severity": a.severity, "context": a.context} for a in result.alertas
        ],
    }


__all__ = ["result_to_payload"]
