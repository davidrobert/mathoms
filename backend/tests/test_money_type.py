"""Tests for `backend.app.schemas.money.MoneyBRL` / `MoneyUSD` (A6g.3b slice 1)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from backend.app.schemas.money import MoneyBRL, MoneyUSD


class _Wallet(BaseModel):
    amount: MoneyBRL
    total_usd: MoneyUSD = Decimal("0")


class TestMoneyBRLInput:
    """Construtor Pydantic aceita int/float/str/Decimal e retorna Decimal."""

    def test_accepts_int(self) -> None:
        w = _Wallet(amount=100)
        assert w.amount == Decimal("100")
        assert isinstance(w.amount, Decimal)

    def test_accepts_float_via_str_coercion(self) -> None:
        w = _Wallet(amount=1234.56)
        # `Decimal(str(1234.56))` == Decimal("1234.56") — evita representação
        # binária inexata que float(0.1) teria.
        assert w.amount == Decimal("1234.56")

    def test_accepts_string(self) -> None:
        w = _Wallet(amount="9876.54")
        assert w.amount == Decimal("9876.54")

    def test_accepts_decimal(self) -> None:
        d = Decimal("42.42")
        w = _Wallet(amount=d)
        assert w.amount == d

    def test_rejects_list(self) -> None:
        with pytest.raises(ValidationError):
            _Wallet(amount=[1, 2, 3])  # type: ignore[arg-type]

    def test_rejects_dict(self) -> None:
        with pytest.raises(ValidationError):
            _Wallet(amount={"x": 1})  # type: ignore[arg-type]


class TestMoneyBRLOutput:
    """Serialização: JSON emite number, Python mantém Decimal."""

    def test_json_emits_number(self) -> None:
        w = _Wallet(amount=Decimal("1234.56"))
        json_str = w.model_dump_json()
        # Deve conter número literal, não string "1234.56"
        assert '"amount":1234.56' in json_str
        assert '"amount":"1234.56"' not in json_str

    def test_model_dump_preserves_decimal(self) -> None:
        w = _Wallet(amount=Decimal("1234.56"))
        dumped = w.model_dump()
        assert dumped["amount"] == Decimal("1234.56")
        assert isinstance(dumped["amount"], Decimal)

    def test_json_roundtrip_via_float(self) -> None:
        """Decimal → float no JSON → Decimal na re-leitura.
        Precisão preservada para valores típicos BRL (2 casas)."""
        original = Decimal("98765.43")
        w = _Wallet(amount=original)
        json_str = w.model_dump_json()
        w2 = _Wallet.model_validate_json(json_str)
        # Igualdade garantida até casas decimais típicas (2 para BRL)
        assert w2.amount == original


class TestMoneyUSDEquivalence:
    """MoneyUSD é equivalente em comportamento — distinção é semântica."""

    def test_usd_accepts_same_inputs(self) -> None:
        w = _Wallet(amount=Decimal("100"), total_usd="250.75")
        assert w.total_usd == Decimal("250.75")
        assert isinstance(w.total_usd, Decimal)

    def test_usd_serializes_as_number(self) -> None:
        w = _Wallet(amount=Decimal("100"), total_usd=Decimal("250.75"))
        assert '"total_usd":250.75' in w.model_dump_json()
