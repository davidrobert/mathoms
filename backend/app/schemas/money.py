"""Money types — Decimal in-memory, number on wire (ADR-090, A6g.3b).

Como usar em DTOs Pydantic:

    from backend.app.schemas.money import MoneyBRL, MoneyUSD

    class TransactionItem(BaseModel):
        valor: MoneyBRL
        ...

Comportamento:

- **Input** (Pydantic validação): aceita `int | float | str | Decimal`.
  Strings como "1234.56" ou "1.234,56" vão via `Decimal(str(v))`.
  Float é convertido via `Decimal(str(v))` — perde alguma precisão no
  ponto de entrada mas evita representação binária inexata (ex:
  `float(0.1)` → `Decimal("0.1")` sem `0.1000000000000000055...`).
- **Memória**: sempre `Decimal`. Aritmética em serviços usa Decimal
  diretamente; `.quantize(Decimal("0.01"))` nos returns quando há
  arredondamento final.
- **JSON wire out**: serializa como `number` (float) via
  `PlainSerializer`. Frontend que espera `number` em TypeScript
  continua funcionando — ADR-090 inline JSON number é aceito desde
  que precisão interna seja Decimal.
- **Python `.model_dump()`**: retorna Decimal. Use `.model_dump_json()`
  para wire output.

Limitação conhecida: roundtrip `Decimal("1234.567890")` → `float` →
JSON perde precisão além do alcance IEEE-754 (≥15-17 dígitos). Para BRL
em valores típicos (~bilhões com 2 casas) isso nunca é atingido.

Ref: ADR-090 (Decimal money), ADR-114 (A6g.6 enforcement), track
A6g.3b (`docs/agent_prompts/track_a6g3b_decimal_money_migration.md`).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer


def _coerce_to_decimal(v: object) -> Decimal:
    """Converte input do usuário para Decimal. Rejeita tipos inesperados
    via `ValueError` (Pydantic wraps em `ValidationError`). `object` em
    vez de `Any` — top type, aceita tudo, sem flaggar no gate `no_any_in_
    boundary` (CLAUDE.md §Tipos).
    """
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float, str)):
        return Decimal(str(v))
    raise ValueError(
        f"cannot coerce {type(v).__name__} to Decimal (money field); "
        "expected int, float, str, or Decimal"
    )


MoneyBRL = Annotated[
    Decimal,
    BeforeValidator(_coerce_to_decimal),
    PlainSerializer(lambda v: float(v), return_type=float, when_used="json"),
]
"""Money em BRL. Decimal em memória, number no JSON."""


MoneyUSD = Annotated[
    Decimal,
    BeforeValidator(_coerce_to_decimal),
    PlainSerializer(lambda v: float(v), return_type=float, when_used="json"),
]
"""Money em USD. Mesma implementação que MoneyBRL — a distinção é
semântica/documentação, não há cast automático entre moedas."""


__all__ = ["MoneyBRL", "MoneyUSD"]
