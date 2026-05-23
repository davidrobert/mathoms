"""Value objects ``Money`` e ``Transaction`` (Fase 5 · ADR-090).

``Money`` usa ``Decimal`` com precisão por moeda (``CURRENCY_PRECISION``).
Construtor rejeita ``float`` com ``TypeError`` — desenvolvedores com float devem
converter conscientemente via ``Decimal(str(value))``.

``Transaction`` é frozen dataclass; "modificar" produz um novo objeto via
``dataclasses.replace``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Union

# Precisão decimal por moeda. Expandir quando suportarmos multi-moeda de fato.
CURRENCY_PRECISION: dict[str, int] = {
    "BRL": 2,
    "USD": 2,
    "EUR": 2,
    "JPY": 0,
}


@dataclass(frozen=True)
class Money:
    """Valor monetário com precisão exata. Nunca ``float``.

    Construtor rejeita ``float`` para evitar erros como
    ``Decimal(str(0.1 + 0.2)) → Decimal("0.30000000000000004")``. Se você tem
    um ``float``, converta explicitamente via ``Decimal(str(v))`` no call-site.
    """

    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError(
                f"Money.amount deve ser Decimal, recebeu {type(self.amount).__name__}. "
                f"Converta explicitamente via Decimal(str(value)) se você entende "
                f"os riscos de precisão."
            )
        if self.currency not in CURRENCY_PRECISION:
            raise ValueError(f"Currency '{self.currency}' não registrada em CURRENCY_PRECISION")

    # -- Operadores --

    def __add__(self, other: "Money") -> "Money":
        self._assert_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        return self + (-other)

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def __mul__(self, factor: Union[int, Decimal]) -> "Money":
        if isinstance(factor, float):
            raise TypeError("Money * float não é permitido — use Decimal ou int")
        return Money(self.amount * Decimal(factor), self.currency)

    __rmul__ = __mul__

    def __lt__(self, other: "Money") -> bool:
        self._assert_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        self._assert_same_currency(other)
        return self.amount <= other.amount

    def _assert_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError(f"Moedas incompatíveis: {self.currency} vs {other.currency}")

    # -- Factories --

    @classmethod
    def of(cls, value: Union[str, Decimal, int], currency: str = "BRL") -> "Money":
        """Factory canônica. Aceita ``str``, ``Decimal``, ``int`` — nunca ``float``."""
        if isinstance(value, float):
            raise TypeError(
                "Money.of() não aceita float. Converta explicitamente via "
                "Decimal(str(v)) se você entende os riscos de precisão."
            )
        if currency not in CURRENCY_PRECISION:
            raise ValueError(f"Currency '{currency}' não registrada em CURRENCY_PRECISION")
        precision = CURRENCY_PRECISION[currency]
        quantum = Decimal(10) ** -precision
        return cls(Decimal(value).quantize(quantum), currency)

    @classmethod
    def brl(cls, value: Union[str, Decimal, int]) -> "Money":
        return cls.of(value, "BRL")

    @classmethod
    def zero(cls, currency: str = "BRL") -> "Money":
        return cls.of(0, currency)

    # -- Serialização --

    def to_float(self) -> float:
        """Para serialização JSON legado. Não usar em cálculos de domínio."""
        return float(self.amount)

    def to_dict(self) -> dict:
        return {"amount": str(self.amount), "currency": self.currency}

    @classmethod
    def from_dict(cls, d: dict) -> "Money":
        return cls.of(d["amount"], d.get("currency", "BRL"))


@dataclass(frozen=True)
class Transaction:
    """Transação bancária: data, descrição, valor (``Money``).

    ``amount`` positivo = crédito; negativo = débito.
    """

    date: date
    description: str
    amount: Money
    category: str | None = None
    member_key: str | None = None
    source_document: str | None = None
    transaction_hash: str | None = None
    is_transfer: bool = False
    # ADR-242 — hint do LLM (categoria_sugerida no dict E2-llm). Preserva
    # através do reconciler E3 para o classifier E4 consumir
    # (`info_fiscal_anual` skipa cedo; demais hints viram fallback hierárquico).
    category_hint: str | None = None

    def with_category(self, category: str) -> "Transaction":
        """Retorna cópia com ``category`` preenchida (nunca muta o original)."""
        return replace(self, category=category)

    def to_dict(self) -> dict:
        """Compatível com schemas JSON legados (E2/E3/E4)."""
        d: dict = {
            "data": self.date.isoformat(),
            "descricao": self.description,
            "valor": self.amount.to_float(),
            "moeda": self.amount.currency,
            "categoria": self.category,
            "membro": self.member_key,
            "is_transfer": self.is_transfer,
        }
        if self.category_hint is not None:
            d["categoria_sugerida"] = self.category_hint
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Transaction":
        return cls(
            date=date.fromisoformat(d["data"]) if isinstance(d.get("data"), str) else d["data"],
            description=d.get("descricao", ""),
            amount=Money.of(str(d.get("valor", 0)), d.get("moeda", "BRL")),
            category=d.get("categoria"),
            member_key=d.get("membro"),
            source_document=d.get("source_document") or d.get("origem"),
            transaction_hash=d.get("hash") or d.get("transaction_hash"),
            is_transfer=bool(d.get("is_transfer", False)),
            category_hint=d.get("categoria_sugerida") or d.get("category_hint"),
        )
