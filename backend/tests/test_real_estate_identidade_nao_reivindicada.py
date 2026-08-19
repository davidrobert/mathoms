"""DE-6 / RV6-13 — identidade fóssil não vira imóvel pendente de rótulo ([[ADR-396]] D3).

`_load_identities` projeta **toda** row viva de `property_identity` como imóvel,
sem consultar o baseline do run. Identidade mintada por run antigo — inclusive a
que nasceu de item da ficha `dividas_onus` antes da [[ADR-392]] — segue chegando
a `excluded_properties` com `classification: "desconhecido"` e CTA "rotular em
Configurações". Rotular põe um passivo no patrimônio bruto como ativo.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.models.market_rate import MarketRate
from backend.app.models.property_identity import PropertyIdentity, WorkspacePropertyOverride
from backend.app.services.real_estate_e5_integration import populate_real_estate

WS = "ws-de6-read"


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    MarketRate.__table__.create(engine, checkfirst=True)
    PropertyIdentity.__table__.create(engine, checkfirst=True)
    WorkspacePropertyOverride.__table__.create(engine, checkfirst=True)
    Local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_rates(db) -> None:
    for pair, rate in (("CDI", "10.90"), ("NTNB_REAL_10Y", "6.50"), ("IFIX_YIELD_12M", "9.20")):
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


def _seed_identity(db, property_id: str, *, canonical: str | None, classification: str | None):
    db.add(
        PropertyIdentity(
            id=property_id,
            workspace_id=WS,
            titular_key="titular",
            codigo_rfb="11",
            endereco_canonical=canonical,
            first_seen_year=2024,
            descricao_sample=canonical or "sem canonical",
            low_confidence=canonical is None,
        )
    )
    if classification:
        db.add(_override(property_id, classification))
    db.commit()


def _override(property_id: str, classification: str) -> WorkspacePropertyOverride:
    return WorkspacePropertyOverride(
        id=f"o-{property_id}",
        workspace_id=WS,
        property_id=property_id,
        classification=classification,
        override_source="user_manual",
    )


def _e5_data() -> dict:
    return {
        "patrimonio": {"liquido": 5000000.0},
        "fluxo_caixa": {
            "receitas_por_fonte": {},
            "receita_despesa_mensal_detalhado": {"labels": []},
        },
    }


def _baseline_com(*property_ids: str) -> dict:
    return {
        "imoveis_consolidados": [
            {"property_id": pid, "codigo_rfb": "11", "valores_31_12": {"2024": 600000.0}}
            for pid in property_ids
        ]
    }


def _payload(db) -> dict:
    out = populate_real_estate(
        workspace_id=WS,
        e5_data=_e5_data(),
        irpf_payload=None,
        baseline_payload=_baseline_com("p-vivo"),
        db=db,
    )
    assert out is not None
    return out


def test_fossil_sem_override_nao_pede_rotulo(db) -> None:
    """A identidade que nenhum baseline vivo reivindica sai da lista de CTA."""
    _seed_rates(db)
    _seed_identity(db, "p-vivo", canonical="exemplo 100", classification="locado")
    _seed_identity(db, "p-fossil-divida", canonical=None, classification=None)
    payload = _payload(db)

    assert [im["property_id"] for im in payload["imoveis"]] == ["p-vivo"]
    assert [e["property_id"] for e in payload["excluded_properties"]] == []


def test_identidade_rotulada_pelo_dono_sobrevive_mesmo_sem_baseline(db) -> None:
    """Rótulo do dono é fato do usuário — o filtro não pode apagá-lo."""
    _seed_rates(db)
    _seed_identity(db, "p-vivo", canonical="exemplo 100", classification="locado")
    _seed_identity(db, "p-nu", canonical="exemplo 200", classification="nu_proprietario")
    _seed_identity(db, "p-fossil-divida", canonical=None, classification=None)
    payload = _payload(db)

    assert [e["property_id"] for e in payload["excluded_properties"]] == ["p-nu"]


def test_sem_baseline_o_filtro_e_inerte(db) -> None:
    """Sem autoridade para comparar, não se poda: o filtro falha para o lado seguro."""
    _seed_rates(db)
    _seed_identity(db, "p-vivo", canonical="exemplo 100", classification="locado")
    _seed_identity(db, "p-fossil-divida", canonical=None, classification=None)
    payload = populate_real_estate(
        workspace_id=WS,
        e5_data=_e5_data(),
        irpf_payload=None,
        baseline_payload=None,
        db=db,
    )

    assert payload is not None
    assert [e["property_id"] for e in payload["excluded_properties"]] == ["p-fossil-divida"]


def test_filtro_nao_move_valor_do_portfolio(db) -> None:
    """O fóssil nunca teve valor no baseline — podá-lo não pode mexer no total."""
    _seed_rates(db)
    _seed_identity(db, "p-vivo", canonical="exemplo 100", classification="locado")
    _seed_identity(db, "p-fossil-divida", canonical=None, classification=None)
    com_fossil = _payload(db)
    db.query(PropertyIdentity).filter(PropertyIdentity.id == "p-fossil-divida").delete()
    db.commit()
    sem_fossil = _payload(db)

    assert com_fossil["valor_total_imoveis"] == sem_fossil["valor_total_imoveis"]
    assert com_fossil["cap_rate_liquido_pct"] == sem_fossil["cap_rate_liquido_pct"]
