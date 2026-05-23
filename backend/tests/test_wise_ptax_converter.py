"""Unit tests A17 L3 P3 — WisePtaxConverter (graceful raise→None over MarketRateRepository)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from backend.app.services.wise_ptax_converter import WisePtaxConverter


def test_get_rate_or_none_brl_retorna_1():
    """BRL → 1 (sem hit em repo). Otimização: não consulta DB."""
    repo = MagicMock()
    conv = WisePtaxConverter(repo)
    assert conv.get_rate_or_none("BRL", 2024) == Decimal("1")
    repo.get_latest_on_or_before.assert_not_called()


def test_get_rate_or_none_usd_chama_repo_com_data_31_12():
    """USD → consulta `USD/BRL` em 31/12 do ano_base."""
    repo = MagicMock()
    repo.get_latest_on_or_before.return_value = MagicMock(rate=Decimal("5.20"))
    conv = WisePtaxConverter(repo)
    result = conv.get_rate_or_none("USD", 2024)
    assert result == Decimal("5.20")
    repo.get_latest_on_or_before.assert_called_once_with("USD/BRL", date(2024, 12, 31))


def test_get_rate_or_none_quando_repo_retorna_none_propaga_none():
    """Repo retorna None (sem cotação) → conv retorna None (graceful, sem raise)."""
    repo = MagicMock()
    repo.get_latest_on_or_before.return_value = None
    conv = WisePtaxConverter(repo)
    assert conv.get_rate_or_none("USD", 2024) is None


def test_get_rate_or_none_eur_pair_correto():
    repo = MagicMock()
    repo.get_latest_on_or_before.return_value = MagicMock(rate=Decimal("5.60"))
    conv = WisePtaxConverter(repo)
    conv.get_rate_or_none("EUR", 2023)
    repo.get_latest_on_or_before.assert_called_once_with("EUR/BRL", date(2023, 12, 31))


def test_get_rate_or_none_gbp_pair_correto():
    repo = MagicMock()
    repo.get_latest_on_or_before.return_value = MagicMock(rate=Decimal("6.80"))
    conv = WisePtaxConverter(repo)
    assert conv.get_rate_or_none("GBP", 2024) == Decimal("6.80")
    repo.get_latest_on_or_before.assert_called_once_with("GBP/BRL", date(2024, 12, 31))
