"""`PropertySupersessionWriter` — port de poda por supersessão de imóveis (ADR-324)."""

from __future__ import annotations

from typing import Mapping, Protocol, runtime_checkable

from pipeline.domain.types.property_supersession import SupersessionOutcome


@runtime_checkable
class PropertySupersessionWriter(Protocol):
    """Boundary de escrita da supersessão de `PropertyIdentity` órfãs."""

    def reconcile_supersession(
        self,
        workspace_id: str,
        winner_by_pid: Mapping[str, str],
    ) -> SupersessionOutcome:
        # ADR-324: estado superseded = função pura do dedup corrente — seta
        # nas perdedoras, limpa nas que deixaram de perder (flip-safe) e
        # re-aponta overrides da perdedora para o vencedor.
        ...
