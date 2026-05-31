"""Unit tests cascade D9 fonte #1 (Informe imobiliária) — ADR-216 Onda 0.5b."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.models.market_rate import MarketRate
from backend.app.models.property_identity import PropertyIdentity, WorkspacePropertyOverride
from backend.app.services.real_estate_e5_integration import populate_real_estate


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    MarketRate.__table__.create(engine, checkfirst=True)
    PropertyIdentity.__table__.create(engine, checkfirst=True)
    WorkspacePropertyOverride.__table__.create(engine, checkfirst=True)
    Local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    s = Local()
    try:
        yield s
    finally:
        s.close()
        engine.dispose()


def _seed_rates(db):
    for pair, rate in [("CDI", "10.90"), ("NTNB_REAL_10Y", "6.50"), ("IFIX_YIELD_12M", "9.20")]:
        db.add(
            MarketRate(
                pair=pair,
                rate=Decimal(rate),
                observed_at=date(2026, 5, 15),
                source="test",
                created_at=datetime.now(timezone.utc),
            )
        )
    db.commit()


def _seed_property(db, ws, pid, endereco, classification):
    db.add(_property_identity(ws, pid, endereco))
    db.add(_classification_override(ws, pid, classification))
    db.commit()


def _property_identity(ws, pid, endereco):
    return PropertyIdentity(
        id=pid,
        workspace_id=ws,
        titular_key="t1",
        codigo_rfb="11",
        endereco_canonical=endereco,
        first_seen_year=2024,
        descricao_sample=endereco,
        low_confidence=False,
    )


def _classification_override(ws, pid, classification):
    return WorkspacePropertyOverride(
        id=f"o-{pid}",
        workspace_id=ws,
        property_id=pid,
        classification=classification,
        override_source="user_manual",
    )


def _e5() -> dict:
    return {
        "patrimonio": {"liquido": 5000000.0},
        "fluxo_caixa": {
            "receitas_por_fonte": {},
            "receita_despesa_mensal_detalhado": {"labels": []},
        },
    }


def _informe(endereco: str, bruto: str, *, meses: int = 12, cnpj: str = "12345678000190") -> dict:
    """Payload completo de 1 informe com 1 imóvel — minimal valid stub."""
    return {
        "imobiliaria_cnpj": cnpj,
        "imobiliaria_nome": "Imob",
        "ano_referencia": 2024,
        "imoveis": [
            {
                "endereco": endereco,
                "aluguel_bruto_anual": bruto,
                "taxa_administracao_anual": "0",
                "ir_retido_anual": "0",
                "aluguel_liquido_anual": bruto,
                "meses_locado_no_periodo": meses,
            }
        ],
        "confidence": 0.9,
    }


def _irpf_carne_leao(descricao: str, valor: str, ir: str = "0") -> dict:
    return {
        "bens_direitos": [
            {"codigo_rfb": "11", "descricao": descricao, "valor_brl": "1000000", "membro_key": "t1"}
        ],
        "rendimentos_pf": [{"pagador_nome": "Inq", "valor_brl": valor, "ir_recolhido_brl": ir}],
    }


def test_informe_sobrescreve_irpf_quando_ambos_presentes(db):
    """Cascade D9 #1: informe tem precedência sobre IRPF (ADR-216)."""
    _seed_rates(db)
    _seed_property(db, "ws1", "pA", "Apto Vila Madalena", "locado")
    payload = populate_real_estate(
        workspace_id="ws1",
        e5_data=_e5(),
        irpf_payload=_irpf_carne_leao("Apto Vila Madalena", "50000", "13750"),
        db=db,
        informe_payloads=[_informe("Apto Vila Madalena", "36000")],
    )
    im = payload["imoveis"][0]
    assert im["aluguel_mensal_bruto"] == pytest.approx(3000.0, abs=0.5)
    assert im["origem_aluguel"] == "informe"


def test_informe_soma_multiplas_imobiliarias_no_mesmo_imovel(db):
    """Dois informes apontando ao mesmo imóvel → soma aluguéis brutos."""
    _seed_rates(db)
    _seed_property(db, "ws1", "pA", "Apto SP", "locado")
    informes = [
        _informe("Apto SP", "12000", meses=6, cnpj="11111111000111"),
        _informe("Apto SP", "18000", meses=6, cnpj="22222222000122"),
    ]
    payload = populate_real_estate(
        workspace_id="ws1",
        e5_data=_e5(),
        irpf_payload=None,
        db=db,
        informe_payloads=informes,
    )
    im = payload["imoveis"][0]
    assert im["aluguel_mensal_bruto"] == pytest.approx(2500.0, abs=0.5)
    assert im["origem_aluguel"] == "informe"


def test_informe_sem_match_endereco_cai_para_proximo_fallback(db):
    """Informe cujo endereço não match property → cai para IRPF/E4."""
    _seed_rates(db)
    _seed_property(db, "ws1", "pA", "Apto Vila Madalena", "locado")
    payload = populate_real_estate(
        workspace_id="ws1",
        e5_data=_e5(),
        irpf_payload=_irpf_carne_leao("Apto Vila Madalena", "24000"),
        baseline_payload={
            "imoveis_consolidados": [{"property_id": "pA", "valores_31_12": {"2024": 1000000.0}}]
        },
        db=db,
        informe_payloads=[_informe("Imóvel inexistente em outra cidade", "60000")],
    )
    im = payload["imoveis"][0]
    assert im["origem_aluguel"] == "irpf"
    assert im["aluguel_mensal_bruto"] == pytest.approx(2000.0, abs=0.5)
