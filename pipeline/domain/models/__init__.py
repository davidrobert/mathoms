"""Domain models (Fase 5) — value objects tipados, imutáveis."""

from pipeline.domain.models.bank import (
    BankCanonicalizer,
    canonicalize_bank,
)
from pipeline.domain.models.document import (
    BankStatement,
    BaselinePatrimonial,
    Investment,
    InvestmentStatement,
)
from pipeline.domain.models.transaction import (
    CURRENCY_PRECISION,
    Money,
    Transaction,
)

__all__ = [
    "BankCanonicalizer",
    "canonicalize_bank",
    "CURRENCY_PRECISION",
    "Money",
    "Transaction",
    "BankStatement",
    "BaselinePatrimonial",
    "Investment",
    "InvestmentStatement",
]
