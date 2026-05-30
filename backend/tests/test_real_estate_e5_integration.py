"""Unit tests P-B (ADR-216) — populate_real_estate integra adapter + store + DB."""

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
    """In-memory SQLite com market_rates + property_identity + workspace_property_overrides."""
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


def _seed_market_rates(db, snapshot: date = date(2026, 5, 15)) -> None:
    for pair, rate in [
        ("CDI", Decimal("10.90")),
        ("NTNB_REAL_10Y", Decimal("6.50")),
        ("IFIX_YIELD_12M", Decimal("9.20")),
    ]:
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


def _seed_property(
    db,
    workspace_id: str,
    property_id: str,
    *,
    codigo_rfb: str = "11",
    titular_key: str = "t1",
    endereco: str = "Apto SP",
    classification: str | None = None,
) -> None:
    db.add(
        PropertyIdentity(
            id=property_id,
            workspace_id=workspace_id,
            titular_key=titular_key,
            codigo_rfb=codigo_rfb,
            endereco_canonical=endereco,
            first_seen_year=2024,
            descricao_sample=endereco,
            low_confidence=False,
        )
    )
    if classification:
        db.add(
            WorkspacePropertyOverride(
                id=f"o-{property_id}",
                workspace_id=workspace_id,
                property_id=property_id,
                classification=classification,
                override_source="user_manual",
            )
        )
    db.commit()


def _base_e5_data(patrimonio_liquido: str = "5000000") -> dict:
    return {
        "patrimonio": {"liquido": float(patrimonio_liquido)},
        "fluxo_caixa": {
            "receitas_por_fonte": {},
            "receita_despesa_mensal_detalhado": {"labels": []},
        },
    }


def _baseline(*valores_by_pid: tuple[str, str], ano: str = "2024") -> dict:
    """Baseline E1.5c sintético: valor-por-imóvel chaveado por property_id (ADR-246/274)."""
    return {
        "imoveis_consolidados": [
            {"property_id": pid, "codigo_rfb": "11", "valores_31_12": {ano: float(valor)}}
            for pid, valor in valores_by_pid
        ]
    }


# ────────────────────────── Empty states ──────────────────────────────────────


def test_returns_none_quando_workspace_sem_property_identity(db):
    _seed_market_rates(db)
    payload = populate_real_estate(
        workspace_id="ws-empty",
        e5_data=_base_e5_data(),
        irpf_payload=None,
        db=db,
    )
    assert payload is None


def test_returns_payload_quando_property_identity_existe(db):
    _seed_market_rates(db)
    _seed_property(db, "ws1", "p1", classification="locado", endereco="Apto SP")
    payload = populate_real_estate(
        workspace_id="ws1",
        e5_data=_base_e5_data(),
        irpf_payload=None,
        db=db,
    )
    assert payload is not None
    assert "cap_rate_liquido_pct" in payload
    assert "benchmarks" in payload
    assert "imoveis" in payload


# ────────────────────────── Cascade IRPF ──────────────────────────────────────


def test_irpf_pro_rata_carne_leao_distribui_aluguel(db):
    """IRPF rendimentos_pf entra como cascade fonte #2 (pro-rata pelo valor do baseline)."""
    _seed_market_rates(db)
    _seed_property(db, "ws1", "pA", codigo_rfb="11", endereco="Apto A", classification="locado")
    _seed_property(db, "ws1", "pB", codigo_rfb="11", endereco="Apto B", classification="locado")
    irpf = {
        "bens_direitos": [],
        "rendimentos_pf": [
            {
                "pagador_nome": "Inquilino X",
                "pagador_cpf_masked": None,
                "valor_brl": "60000",
                "ir_recolhido_brl": "16500",
            }
        ],
    }
    payload = populate_real_estate(
        workspace_id="ws1",
        e5_data=_base_e5_data(),
        irpf_payload=irpf,
        baseline_payload=_baseline(("pA", "2000000"), ("pB", "1000000")),
        db=db,
    )
    assert payload is not None
    imoveis = {im["property_id"]: im for im in payload["imoveis"]}
    # pA tem 2/3 do valor → recebe 2/3 do aluguel (40000); pB → 20000
    assert imoveis["pA"]["aluguel_mensal_bruto"] == pytest.approx(40000 / 12, rel=1e-3)
    assert imoveis["pB"]["aluguel_mensal_bruto"] == pytest.approx(20000 / 12, rel=1e-3)


def test_residencia_principal_vai_para_excluded(db):
    _seed_market_rates(db)
    _seed_property(db, "ws1", "pInv", classification="locado", endereco="Investimento")
    _seed_property(db, "ws1", "pRes", classification="residencia_principal", endereco="Casa")
    payload = populate_real_estate(
        workspace_id="ws1",
        e5_data=_base_e5_data(),
        irpf_payload=None,
        db=db,
    )
    assert payload is not None
    assert len(payload["imoveis"]) == 1
    assert payload["imoveis"][0]["property_id"] == "pInv"
    assert len(payload["excluded_properties"]) == 1
    assert payload["excluded_properties"][0]["property_id"] == "pRes"


def test_sem_override_classification_vira_desconhecido_e_excluido(db):
    """ADR-215: sem override em workspace_property_overrides → 'desconhecido' → excluded."""
    _seed_market_rates(db)
    _seed_property(db, "ws1", "pUnk")  # sem classification override
    payload = populate_real_estate(
        workspace_id="ws1",
        e5_data=_base_e5_data(),
        irpf_payload=None,
        db=db,
    )
    assert payload is not None
    assert payload["imoveis"] == []
    assert payload["excluded_properties"][0]["classification"] == "desconhecido"


# ────────────────────────── Cascade E4 ────────────────────────────────────────


def test_e4_receita_aluguel_usada_quando_irpf_sem_rendimentos_pf(db):
    """Cascade D9 #3: IRPF tem bens (valor) mas SEM rendimentos_pf → usa E4 agregado."""
    _seed_market_rates(db)
    _seed_property(db, "ws1", "pA", codigo_rfb="11", endereco="Apto A", classification="locado")
    e5 = _base_e5_data()
    e5["fluxo_caixa"]["receitas_por_fonte"]["receita_aluguel"] = 30000.0
    e5["fluxo_caixa"]["receita_despesa_mensal_detalhado"]["labels"] = [
        f"2024-{m:02d}" for m in range(1, 13)
    ]
    # Baseline popula valor_imovel; IRPF sem rendimentos_pf → cascade cai no E4.
    payload = populate_real_estate(
        workspace_id="ws1",
        e5_data=e5,
        irpf_payload={"bens_direitos": [], "rendimentos_pf": []},
        baseline_payload=_baseline(("pA", "1000000")),
        db=db,
    )
    assert payload is not None
    imovel = payload["imoveis"][0]
    # 30000 já é anual (12 meses) → 2500/mês
    assert imovel["aluguel_mensal_bruto"] == pytest.approx(2500.0, rel=1e-2)
    assert imovel["origem_aluguel"] == "e4"


# ────────────────────────── Benchmarks ────────────────────────────────────────


def test_benchmarks_propagados_quando_seed_existe(db):
    _seed_market_rates(db)
    _seed_property(db, "ws1", "p1", classification="locado")
    payload = populate_real_estate(
        workspace_id="ws1",
        e5_data=_base_e5_data(),
        irpf_payload=None,
        db=db,
    )
    assert payload is not None
    b = payload["benchmarks"]
    # CDI nominal 10.9 × (1 - 0.175) = 8.9925 → quantize 8.99
    assert b["cdi_liquido_pct"] == pytest.approx(8.99, abs=0.01)
    assert b["ntnb_liquido_pct"] == pytest.approx(5.52, abs=0.01)
    assert b["ifix_yield_pct"] == pytest.approx(9.20, abs=0.01)


def test_benchmarks_zero_quando_market_rates_sem_seed(db):
    """Degradação graceful — UI sinaliza."""
    _seed_property(db, "ws1", "p1", classification="locado")
    payload = populate_real_estate(
        workspace_id="ws1",
        e5_data=_base_e5_data(),
        irpf_payload=None,
        db=db,
    )
    assert payload is not None
    b = payload["benchmarks"]
    assert b["cdi_liquido_pct"] == 0.0
    assert b["ntnb_liquido_pct"] == 0.0
    assert b["ifix_yield_pct"] == 0.0


# ───────────────── Valor-por-imóvel vem do baseline E1.5c (não do IRPF cru) ─────


def test_valor_imovel_vem_do_baseline_por_property_id(db):
    """Valor do imóvel investido casa por property_id estável do baseline consolidado."""
    _seed_market_rates(db)
    _seed_property(db, "ws1", "pA", endereco="Apto Vila Madalena", classification="locado")
    payload = populate_real_estate(
        workspace_id="ws1",
        e5_data=_base_e5_data(),
        irpf_payload=None,
        baseline_payload=_baseline(("pA", "1500000")),
        db=db,
    )
    assert payload is not None
    assert payload["imoveis"][0]["valor_imovel"] == pytest.approx(1500000.0, abs=0.01)


def test_extract_irpf_full_shape_nao_zera_valor_regressao(db):
    """Regressão: shape REAL do extract_irpf_full (campo `codigo`, membro_key=role 'titular')
    não casava no matcher antigo → valor 0 → cap_rate None → card vazio. Agora valor vem do
    baseline por property_id, independente do shape do IRPF cru."""
    _seed_market_rates(db)
    _seed_property(db, "ws1", "pInv", titular_key="david_robert", classification="locado")
    # IRPF E1.6 real: `codigo` (não `codigo_rfb`) + `membro_key` é PAPEL, não slug.
    irpf = {
        "bens_direitos": [
            {"codigo": "11", "membro_key": "titular", "valor_brl": "800000", "descricao": "Apto"}
        ],
        "rendimentos_pf": [],
    }
    payload = populate_real_estate(
        workspace_id="ws1",
        e5_data=_base_e5_data(),
        irpf_payload=irpf,
        baseline_payload=_baseline(("pInv", "800000")),
        db=db,
    )
    assert payload is not None
    assert payload["imoveis"][0]["valor_imovel"] == pytest.approx(800000.0, abs=0.01)
    assert payload["cap_rate_liquido_pct"] is not None  # valor_total > 0 → cap_rate calcula


# Tests de cascade #1 (Informe) vivem em
# ``test_real_estate_e5_integration_cascade.py`` para isolar o stub de Informe
# e manter cada caso ≤20 linhas (CLAUDE.md §Code style).
