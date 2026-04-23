"""Padrão de retorno para operações do console interno."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OpResult:
    """Resultado de uma operação destrutiva/sensível.

    `ok=False` sempre tem `error`; `ok=True` pode ter `details` com metadados
    relevantes para audit (id do recurso, contagem afetada, etc).
    """

    ok: bool
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(cls, **details: Any) -> "OpResult":
        return cls(ok=True, details=dict(details))

    @classmethod
    def failure(cls, error: str, **details: Any) -> "OpResult":
        return cls(ok=False, error=error, details=dict(details))
