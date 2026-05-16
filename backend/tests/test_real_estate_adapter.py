"""Unit tests do adapter ADR-216 P-A — cascade D9 + benchmarks + classification filter."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models.market_rate import MarketRate
from backend.app.models.property_identity import PropertyIdentity, WorkspacePropertyOverride
from backend.app.services.real_estate_adapter import (
    PAIR_CDI,
    PAIR_IFIX_YIELD_12M,
    PAIR_NTNB_REAL_10Y,
    CascadeSources,
    E4ReceitaAluguelEntry,
    IRPFAluguelEntry,
    build_property_inputs,
    fetch_benchmarks,
)
from pipeline.domain.services.real_estate_metrics import RealEstateConfig

# ────────────────────────── Fixtures ──────────────────────────────────────────


@pytest.fixture
def db():
    """In-memory SQLite com apenas a tabela ``market_rates`` necessária aos testes."""
    engine = create_engine("sqlite:///:memory:")
    MarketRate.__table__.create(engine, checkfirst=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_market_rates(db, snapshot: date = date(2026, 5, 15)) -> None:
    """Replica o seed da migration adr216realestate1 para uso em testes."""
    pairs = [
        (PAIR_CDI, Decimal("10.90")),
        (PAIR_NTNB_REAL_10Y, Decimal("6.50")),
        (PAIR_IFIX_YIELD_12M, Decimal("9.20")),
    ]
    for pair, rate in pairs:
        db.add(
            MarketRate(
                pair=pair,
                rate=rate,
                observed_at=snapshot,
                source="test",
                created_at=datetime.now(timezone.utc),
            )
        )
    db.commit()


def _identity(
    *, property_id: str = "p1", descricao: str = "Apto SP", endereco: str = "Apto SP"
) -> PropertyIdentity:
    return PropertyIdentity(
        id=property_id,
        workspace_id="ws1",
        titular_key="t",
        codigo_rfb="11",
        endereco_canonical=endereco,
        first_seen_year=2024,
        descricao_sample=descricao,
        low_confidence=False,
    )


def _override(
    *, property_id: str = "p1", classification: str = "locado"
) -> WorkspacePropertyOverride:
    return WorkspacePropertyOverride(
        id=f"o-{property_id}",
        workspace_id="ws1",
        property_id=property_id,
        classification=classification,
        override_source="user_manual",
    )


# ────────────────────────── fetch_benchmarks ──────────────────────────────────


def test_fetch_benchmarks_normaliza_liquido_cdi_ntnb_ifix(db):
    """CDI×(1-17,5%); NTNB×(1-15%); IFIX sem normalização (isento PF)."""
    _seed_market_rates(db)
    b = fetch_benchmarks(db, as_of_date=date(2026, 5, 15))

    # CDI 10.9 × 0.825 = 8.9925 → quantize half-even = 8.99
    assert b.cdi_liquido_pct == Decimal("8.99")
    # NTNB 6.5 × 0.85 = 5.525 → quantize half-even = 5.52 (banker's rounding default)
    assert b.ntnb_liquido_pct == Decimal("5.52")
    # IFIX isento PF
    assert b.ifix_yield_pct == Decimal("9.20")
    assert b.as_of_date == date(2026, 5, 15)


def test_fetch_benchmarks_zero_quando_pair_ausente_degradacao_graceful(db):
    """Sem seed, fetch retorna zero (não levanta) — UI sinaliza via empty state."""
    b = fetch_benchmarks(db, as_of_date=date(2026, 5, 15))
    assert b.cdi_liquido_pct == Decimal("0.00")
    assert b.ntnb_liquido_pct == Decimal("0.00")
    assert b.ifix_yield_pct == Decimal("0.00")


def test_fetch_benchmarks_aceita_override_ir_efetivo_cdi(db):
    """``cdi_ir_efetivo_pct`` permite workspace ajustar normalização."""
    _seed_market_rates(db)
    b = fetch_benchmarks(
        db,
        as_of_date=date(2026, 5, 15),
        cdi_ir_efetivo_pct=Decimal("0.225"),  # 22,5% (curto prazo)
    )
    # 10.9 × 0.775 = 8.4475 → 8.45
    assert b.cdi_liquido_pct == Decimal("8.45")


def test_fetch_benchmarks_le_data_anterior_quando_exato_nao_existe(db):
    """``get_latest_on_or_before`` deve achar seed em data <= as_of_date."""
    _seed_market_rates(db, snapshot=date(2026, 5, 1))
    b = fetch_benchmarks(db, as_of_date=date(2026, 5, 15))
    # Achou seed 2026-05-01
    assert b.cdi_liquido_pct == Decimal("8.99")


# ────────────────────────── build_property_inputs ─────────────────────────────


def test_build_inputs_irpf_pro_rata_proporcional_ao_valor():
    """Cascade D9 #2 (IRPF carnê-leão) distribui pro-rata pelo valor."""
    id_a = _identity(property_id="pA", descricao="A")
    id_b = _identity(property_id="pB", descricao="B")
    overrides = {
        "pA": _override(property_id="pA", classification="locado"),
        "pB": _override(property_id="pB", classification="locado"),
    }
    bens = {"pA": Decimal("2000000"), "pB": Decimal("1000000")}
    sources = CascadeSources(
        informe_imobiliaria_by_property={},
        irpf_carne_leao=(
            IRPFAluguelEntry(
                pagador_nome="X",
                pagador_cpf_masked=None,
                valor_brl=Decimal("60000"),
                ir_recolhido_brl=Decimal("16500"),
            ),
        ),
        e4_receita_aluguel_total=None,
    )

    inputs = build_property_inputs(
        [id_a, id_b], overrides, bens, sources, config=RealEstateConfig()
    )
    map_inputs = {p.property_id: p for p in inputs}
    # pA = 2/3 do valor → 40000; pB = 1/3 → 20000
    assert map_inputs["pA"].aluguel_bruto_anual == Decimal("40000")
    assert map_inputs["pB"].aluguel_bruto_anual == Decimal("20000")
    assert map_inputs["pA"].aluguel_origem == "irpf"
    assert map_inputs["pA"].ir_carne_leao_anual == Decimal("11000")
    assert map_inputs["pB"].ir_carne_leao_anual == Decimal("5500")


def test_build_inputs_informe_sobrescreve_cascade_irpf():
    """Informe (#1) ganha de IRPF (#2) — origem = "informe" + IR retido propagado."""
    id_a = _identity(property_id="pA")
    overrides = {"pA": _override(property_id="pA", classification="locado")}
    bens = {"pA": Decimal("1000000")}
    sources = CascadeSources(
        informe_imobiliaria_by_property={
            "pA": {"aluguel_bruto_anual": "30000", "ir_retido_anual": "0"}
        },
        irpf_carne_leao=(
            IRPFAluguelEntry(
                pagador_nome="X",
                pagador_cpf_masked=None,
                valor_brl=Decimal("60000"),
                ir_recolhido_brl=Decimal("16500"),
            ),
        ),
        e4_receita_aluguel_total=None,
    )
    inputs = build_property_inputs([id_a], overrides, bens, sources, config=RealEstateConfig())
    assert inputs[0].aluguel_bruto_anual == Decimal("30000")
    assert inputs[0].aluguel_origem == "informe"


def test_build_inputs_e4_fallback_quando_irpf_e_informe_ausentes():
    """Cascade D9 #3 (E4 receita agregada) — distribui pro-rata anualizando."""
    id_a = _identity(property_id="pA")
    overrides = {"pA": _override(property_id="pA", classification="locado")}
    bens = {"pA": Decimal("1000000")}
    sources = CascadeSources(
        informe_imobiliaria_by_property={},
        irpf_carne_leao=(),
        e4_receita_aluguel_total=E4ReceitaAluguelEntry(
            valor_total_brl=Decimal("12000"), n_meses_periodo=6
        ),
    )
    inputs = build_property_inputs([id_a], overrides, bens, sources, config=RealEstateConfig())
    # 12000 / 6 × 12 = 24000 anual
    assert inputs[0].aluguel_bruto_anual == Decimal("24000")
    assert inputs[0].aluguel_origem == "e4"


def test_build_inputs_sem_fontes_marca_origem_none():
    """Cascade exaurido — aluguel None + origem 'none' (não 'default')."""
    id_a = _identity(property_id="pA")
    overrides = {"pA": _override(property_id="pA", classification="locado")}
    bens = {"pA": Decimal("1000000")}
    sources = CascadeSources(
        informe_imobiliaria_by_property={},
        irpf_carne_leao=(),
        e4_receita_aluguel_total=None,
    )
    inputs = build_property_inputs([id_a], overrides, bens, sources, config=RealEstateConfig())
    assert inputs[0].aluguel_bruto_anual is None
    assert inputs[0].aluguel_origem == "none"


def test_build_inputs_residencia_recebe_classification_correta():
    """Override com classification 'residencia_principal' aparece no PropertyInput."""
    id_a = _identity(property_id="pA", descricao="Residência")
    overrides = {"pA": _override(property_id="pA", classification="residencia_principal")}
    bens = {"pA": Decimal("1500000")}
    sources = CascadeSources(
        informe_imobiliaria_by_property={},
        irpf_carne_leao=(),
        e4_receita_aluguel_total=None,
    )
    inputs = build_property_inputs([id_a], overrides, bens, sources, config=RealEstateConfig())
    assert inputs[0].classification == "residencia_principal"
    # Residência NÃO recebe pro-rata IRPF — fica sem aluguel
    assert inputs[0].aluguel_bruto_anual is None


def test_build_inputs_sem_override_default_desconhecido():
    """Imóvel sem override em ``workspace_property_overrides`` → 'desconhecido' (ADR-215)."""
    id_a = _identity(property_id="pA")
    bens = {"pA": Decimal("1000000")}
    sources = CascadeSources(
        informe_imobiliaria_by_property={},
        irpf_carne_leao=(),
        e4_receita_aluguel_total=None,
    )
    inputs = build_property_inputs([id_a], {}, bens, sources, config=RealEstateConfig())
    assert inputs[0].classification == "desconhecido"


def test_build_inputs_residencia_excluida_do_pro_rata_denominator():
    """Pro-rata IRPF deve dividir apenas por imóveis de investimento (ADR-216 D8)."""
    id_locado = _identity(property_id="pA", descricao="Locado")
    id_res = _identity(property_id="pB", descricao="Residência")
    overrides = {
        "pA": _override(property_id="pA", classification="locado"),
        "pB": _override(property_id="pB", classification="residencia_principal"),
    }
    # pB tem 2x o valor de pA — se entrasse no denominador, pA receberia 1/3 do aluguel
    bens = {"pA": Decimal("1000000"), "pB": Decimal("2000000")}
    sources = CascadeSources(
        informe_imobiliaria_by_property={},
        irpf_carne_leao=(
            IRPFAluguelEntry(
                pagador_nome="X",
                pagador_cpf_masked=None,
                valor_brl=Decimal("30000"),
                ir_recolhido_brl=Decimal("8250"),
            ),
        ),
        e4_receita_aluguel_total=None,
    )
    inputs = build_property_inputs(
        [id_locado, id_res], overrides, bens, sources, config=RealEstateConfig()
    )
    locado_input = next(p for p in inputs if p.property_id == "pA")
    # pA é o único investment; recebe 100% do aluguel IRPF (denominator = 1000000, não 3000000)
    assert locado_input.aluguel_bruto_anual == Decimal("30000")
