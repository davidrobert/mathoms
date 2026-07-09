"""`InMemoryPropertySupersessionWriter` — fake nomeado para testes (ADR-324)."""

from __future__ import annotations

from typing import Mapping

from pipeline.domain.types.property_supersession import SupersessionOutcome


class InMemoryPropertySupersessionWriter:
    """Registra chamadas de reconcile sem tocar DB (testes do E1.5c step 3b)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def reconcile_supersession(
        self, workspace_id: str, winner_by_pid: Mapping[str, str]
    ) -> SupersessionOutcome:
        self.calls.append((workspace_id, dict(winner_by_pid)))
        return SupersessionOutcome(0, 0, 0, 0)


__all__ = ["InMemoryPropertySupersessionWriter"]
