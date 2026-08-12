"""`InMemoryPropertySupersessionWriter` — fake nomeado para testes (ADR-324, ADR-386)."""

from __future__ import annotations

from pipeline.domain.types.property_supersession import (
    SupersessionOutcome,
    SupersessionScope,
)


class InMemoryPropertySupersessionWriter:
    """Registra chamadas de reconcile sem tocar DB (testes do E1.5c step 3b)."""

    def __init__(self) -> None:
        self.calls: list[SupersessionScope] = []

    def reconcile_supersession(self, scope: SupersessionScope) -> SupersessionOutcome:
        self.calls.append(scope)
        return SupersessionOutcome(0, 0, 0, 0)


__all__ = ["InMemoryPropertySupersessionWriter"]
