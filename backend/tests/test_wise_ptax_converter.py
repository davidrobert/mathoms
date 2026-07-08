"""A17 L3 P3 + A33.l2 — WisePtaxConverter: quote 31/12 + guard anti-bootstrap (emenda ADR-135).

Regressão exigida pelo co-design data-engineer 2026-07-07: o seed A7.2b
bootstrapa 2024-01-01 com cotação de 2026; ``get_latest_on_or_before``
retornaria essa row silenciosamente para lookups de 31/12. O converter só
aceita cotação observada em dezembro do ano-base — senão ``None`` (merger
emite ``PtaxMissingWarning``). DB real (SQLite), nunca mock.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models.market_rate import MarketRate
from backend.app.repositories.market_rate_repository import MarketRateRepository
from backend.app.services.wise_ptax_converter import WisePtaxConverter


@pytest.fixture
def sync_db(tmp_path):
    """Sync engine isolado por teste — repo consome Session sync."""
    db_file = tmp_path / "test_ptax.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _rate(pair: str, observed_at: date, rate: str, source: str = "test") -> MarketRate:
    return MarketRate(
        id=str(uuid.uuid4()),
        pair=pair,
        rate=Decimal(rate),
        observed_at=observed_at,
        source=source,
        created_at=datetime.now(timezone.utc),
    )


def _converter(session) -> WisePtaxConverter:
    return WisePtaxConverter(MarketRateRepository(session))


def test_brl_retorna_quote_1_sem_consultar_db(sync_db):
    with sync_db() as session:
        quote = _converter(session).get_quote_or_none("BRL", 2024)
    assert quote is not None
    assert quote.rate == Decimal("1")
    assert quote.observed_at == date(2024, 12, 31)


def test_usd_com_row_31_12_retorna_quote(sync_db):
    with sync_db() as session:
        session.add(_rate("USD/BRL", date(2024, 12, 31), "6.1917"))
        session.commit()
        quote = _converter(session).get_quote_or_none("USD", 2024)
    assert quote is not None
    assert quote.rate == Decimal("6.1917")
    assert quote.observed_at == date(2024, 12, 31)


def test_ultimo_dia_util_de_dezembro_aceito(sync_db):
    """31/12/2023 caiu fora de dia útil — fechamento 2023-12-29 é a PTAX válida."""
    with sync_db() as session:
        session.add(_rate("USD/BRL", date(2023, 12, 29), "4.8407"))
        session.commit()
        quote = _converter(session).get_quote_or_none("USD", 2023)
    assert quote is not None
    assert quote.observed_at == date(2023, 12, 29)


def test_guard_anti_bootstrap_row_de_janeiro_retorna_none(sync_db):
    """REGRESSÃO (co-design DE 2026-07-07): bootstrap 2024-01-01 com cotação de
    2026 NÃO pode converter snapshot 31/12/2024 — degrada para None."""
    with sync_db() as session:
        session.add(
            _rate(
                "USD/BRL",
                date(2024, 1, 1),
                "5.80",
                source="bootstrap A7.2b (cotação corrente replicada para histórico)",
            )
        )
        session.commit()
        assert _converter(session).get_quote_or_none("USD", 2024) is None


def test_guard_cotacao_de_ano_anterior_retorna_none(sync_db):
    """Row de dezembro de OUTRO ano-base não vale para o snapshot pedido."""
    with sync_db() as session:
        session.add(_rate("USD/BRL", date(2023, 12, 31), "4.8407"))
        session.commit()
        assert _converter(session).get_quote_or_none("USD", 2024) is None


def test_com_bootstrap_e_row_31_12_prefere_31_12(sync_db):
    """Seed novo (a33l2ptax3112) convive com bootstrap — 31/12 vence."""
    with sync_db() as session:
        session.add(_rate("USD/BRL", date(2024, 1, 1), "5.80", source="bootstrap"))
        session.add(_rate("USD/BRL", date(2024, 12, 31), "6.1917", source="BCB PTAX compra"))
        session.commit()
        quote = _converter(session).get_quote_or_none("USD", 2024)
    assert quote is not None
    assert quote.rate == Decimal("6.1917")


def test_sem_row_retorna_none(sync_db):
    with sync_db() as session:
        assert _converter(session).get_quote_or_none("USD", 2024) is None


def test_gbp_pair_correto(sync_db):
    with sync_db() as session:
        session.add(_rate("GBP/BRL", date(2024, 12, 31), "7.7570"))
        session.commit()
        quote = _converter(session).get_quote_or_none("GBP", 2024)
    assert quote is not None and quote.rate == Decimal("7.7570")


def test_get_rate_or_none_compat_aplica_mesmo_guard(sync_db):
    with sync_db() as session:
        session.add(_rate("USD/BRL", date(2024, 1, 1), "5.80"))
        session.add(_rate("EUR/BRL", date(2024, 12, 31), "6.4344"))
        session.commit()
        conv = _converter(session)
        assert conv.get_rate_or_none("USD", 2024) is None
        assert conv.get_rate_or_none("EUR", 2024) == Decimal("6.4344")
