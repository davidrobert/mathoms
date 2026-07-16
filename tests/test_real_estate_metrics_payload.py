"""Unit tests — Onda 2 (ADR-216) payload serialization + schema + boundary checks."""

from __future__ import annotations

import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.real_estate_metrics import (
    BenchmarkRates,
    PropertyInput,
    calculate_real_estate_metrics,
    result_to_payload,
)


def _benchmarks(cdi: str = "8.7", ntnb: str = "5.5", ifix: str = "9.2") -> BenchmarkRates:
    return BenchmarkRates(
        cdi_liquido_pct=Decimal(cdi),
        ntnb_liquido_pct=Decimal(ntnb),
        ifix_yield_pct=Decimal(ifix),
        as_of_date=date(2026, 5, 15),
    )


def _property(
    *,
    property_id: str = "p1",
    classification: str = "locado",
    valor: str = "1200000",
    aluguel: str | None = "25200",
    aluguel_origem: str = "informe",
    taxa_adm: str | None = "2520",
    iptu: str | None = "4800",
    meses_locado: int | None = 12,
    ir_carne_leao: str | None = None,
) -> PropertyInput:
    return PropertyInput(
        property_id=property_id,
        descricao="Apto",
        classification=classification,
        valor_imovel=Decimal(valor),
        aluguel_bruto_anual=Decimal(aluguel) if aluguel is not None else None,
        aluguel_origem=aluguel_origem,
        taxa_administracao_anual=Decimal(taxa_adm) if taxa_adm is not None else None,
        ir_retido_anual=Decimal("0"),
        ir_carne_leao_anual=Decimal(ir_carne_leao) if ir_carne_leao is not None else None,
        iptu_anual=Decimal(iptu) if iptu is not None else None,
        meses_locado_no_ano=meses_locado,
    )


# ────────────────────────── Empty states ────────────────────────────────────


def test_zero_imoveis_investimento_devolve_cap_rate_none():
    """Sem imóveis de investimento → cap rates None, payload coerente."""
    p = _property(classification="residencia_principal")
    result = calculate_real_estate_metrics(
        [p], concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    assert result.cap_rate_liquido_pct is None
    assert result.cap_rate_bruto_pct is None
    assert result.imoveis == []
    assert len(result.excluded_properties) == 1


def test_lista_de_imoveis_vazia():
    result = calculate_real_estate_metrics(
        [], concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    assert result.cap_rate_liquido_pct is None
    assert result.imoveis == []
    assert result.excluded_properties == []
    assert result.alertas == []
    assert result.valor_total_imoveis == Decimal("0")


# ────────────────────────── Componentes_calculo ─────────────────────────────


def test_componentes_carrega_origem_e_confidence():
    """Cada componente do payload tem valor + origem + confidence (data-engineer 2026-05-15)."""
    p = _property(
        aluguel="25200",
        aluguel_origem="informe",
        taxa_adm="2520",
        iptu="4800",
        ir_carne_leao="6930",  # irpf
    )
    result = calculate_real_estate_metrics(
        [p], concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    componentes = result.componentes_calculo
    assert componentes["aluguel_anual_bruto"].origem == "informe"
    assert componentes["aluguel_anual_bruto"].confidence == "high"
    assert componentes["taxa_administracao_anual"].confidence == "high"
    assert componentes["ir_carne_leao_anual"].origem == "irpf"
    assert componentes["ir_carne_leao_anual"].confidence == "medium"
    assert componentes["manutencao_anual"].origem == "default"
    assert componentes["manutencao_anual"].confidence == "low"


def test_componentes_origem_dominante_por_valor_em_carteira_mista():
    """Em carteira mista, origem do maior valor predomina (modo por valor)."""
    p_irpf = _property(property_id="p1", valor="2000000", aluguel="40000", aluguel_origem="irpf")
    p_informe = _property(
        property_id="p2", valor="500000", aluguel="10000", aluguel_origem="informe"
    )
    result = calculate_real_estate_metrics(
        [p_irpf, p_informe], concentracao_imobiliaria_pct=Decimal("20"), benchmarks=_benchmarks()
    )
    assert result.componentes_calculo["aluguel_anual_bruto"].origem == "irpf"


# ────────────────────────── ADR-090 — Decimal puro ──────────────────────────


def test_calculo_usa_decimal_em_todo_pipeline():
    """ADR-090: dinheiro em Decimal interno; serializer faz coerção para payload."""
    p = _property()
    result = calculate_real_estate_metrics(
        [p], concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    assert isinstance(result.cap_rate_liquido_pct, Decimal)
    assert isinstance(result.concentracao_pct, Decimal)
    assert isinstance(result.componentes_calculo["aluguel_anual_bruto"].valor, Decimal)


# ────────────────────────── Payload serialization ───────────────────────────


def test_result_to_payload_shape_top_level():
    """Payload top-level mandatory keys (data-engineer contract)."""
    p = _property()
    result = calculate_real_estate_metrics(
        [p], concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    payload = result_to_payload(result)

    expected_keys = {
        "cap_rate_liquido_pct",
        "cap_rate_bruto_pct",
        "componentes_calculo",
        "benchmarks",
        "spreads_pp",
        "spread_brl_anual",
        "concentracao_pct",
        "valor_total_imoveis",
        "imoveis",
        "excluded_properties",
        "alertas",
    }
    assert expected_keys.issubset(payload.keys())


def test_result_to_payload_imovel_shape():
    """Cada item de `imoveis[]` carrega campos mínimos para card S4."""
    p = _property()
    result = calculate_real_estate_metrics(
        [p], concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    payload = result_to_payload(result)
    imovel = payload["imoveis"][0]

    must_have_keys = {
        "property_id",
        "descricao",
        "classification",
        "valor_imovel",
        "cap_rate_bruto_pct",
        "cap_rate_liquido_pct",
        "status_contrato",
        "origem_aluguel",
    }
    assert must_have_keys.issubset(imovel.keys())


def test_result_to_payload_excluded_properties_com_motivo():
    """`excluded_properties` é populado para UI mostrar por que imóveis foram filtrados."""
    props = [
        _property(property_id="p1", classification="locado"),
        _property(property_id="p2", classification="residencia_principal"),
    ]
    result = calculate_real_estate_metrics(
        props, concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    payload = result_to_payload(result)
    assert len(payload["excluded_properties"]) == 1
    exc = payload["excluded_properties"][0]
    assert exc["property_id"] == "p2"
    assert exc["classification"] == "residencia_principal"
    assert exc["motivo"]  # não vazio


# ────────────────────────── Ordering ────────────────────────────────────────


def test_imoveis_ordenados_por_valor_descendente():
    """Tabela determinística — maior valor primeiro (UI consistente)."""
    p_pequeno = _property(property_id="small", valor="200000")
    p_grande = _property(property_id="big", valor="2000000")
    p_medio = _property(property_id="med", valor="800000")
    result = calculate_real_estate_metrics(
        [p_pequeno, p_grande, p_medio],
        concentracao_imobiliaria_pct=Decimal("20"),
        benchmarks=_benchmarks(),
    )
    assert [i.property_id for i in result.imoveis] == ["big", "med", "small"]


# ────────────────────────── Schema + boundary ───────────────────────────────


def test_payload_passa_no_e5_analysis_schema_canonico():
    """Payload `real_estate` valida contra config/schemas/e5_analysis.schema.json (ADR-212 hook)."""
    schema_path = (
        Path(__file__).resolve().parent.parent / "config" / "schemas" / "e5_analysis.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    real_estate_schema = schema["properties"]["real_estate"]

    props = [
        _property(property_id="p1", aluguel="25200", aluguel_origem="informe"),
        _property(property_id="p2", classification="residencia_principal"),
    ]
    result = calculate_real_estate_metrics(
        props,
        concentracao_imobiliaria_pct=Decimal("30"),
        benchmarks=_benchmarks(),
    )
    payload = result_to_payload(result)

    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        pytest.skip("jsonschema não disponível neste ambiente — gate roda em CI")

    Draft202012Validator(real_estate_schema).validate(payload)


def test_pipeline_boundaries_pipeline_sem_framework_imports():
    """ADR-097 + boundary check: este módulo não importa framework code."""
    services_dir = Path(__file__).resolve().parent.parent / "pipeline" / "domain" / "services"
    targets = [
        "real_estate_metrics.py",
        "real_estate_metrics_aggregator.py",
        "real_estate_metrics_payload.py",
    ]
    for name in targets:
        source = (services_dir / name).read_text(encoding="utf-8")
        for forbidden in (
            "from fastapi",
            "import fastapi",
            "from sqlalchemy",
            "from celery",
            "from backend",
        ):
            assert forbidden not in source, f"Boundary violation: {forbidden!r} em {name}"


def test_benchmarks_propagados_para_payload():
    p = _property()
    result = calculate_real_estate_metrics(
        [p], concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    payload = result_to_payload(result)
    assert payload["benchmarks"]["cdi_liquido_pct"] == 8.7
    assert payload["benchmarks"]["ntnb_liquido_pct"] == 5.5
    assert payload["benchmarks"]["ifix_yield_pct"] == 9.2
    assert payload["benchmarks"]["as_of_date"] == "2026-05-15"
