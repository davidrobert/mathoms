"""`PropertySupersessionWriter` — port de poda por supersessão de imóveis (ADR-324, ADR-386)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pipeline.domain.types.property_supersession import (
    SupersessionOutcome,
    SupersessionScope,
)


@runtime_checkable
class PropertySupersessionWriter(Protocol):
    """Boundary de escrita da supersessão de `PropertyIdentity` órfãs."""

    def reconcile_supersession(self, scope: SupersessionScope) -> SupersessionOutcome:
        # ADR-324: estado superseded = função pura do dedup corrente — seta
        # nas perdedoras, limpa nas que deixaram de perder (flip-safe) e
        # re-aponta overrides da perdedora para o vencedor.
        # ADR-386: tudo isso restrito a `scope.observed_pids`; row que o run não
        # observou não é tocada, nem para setar nem para limpar.
        ...
