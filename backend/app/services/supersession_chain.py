"""Travessia da cadeia de supersessão de `PropertyIdentity` (ADR-375)."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Optional

# id → (superseded_at, superseded_by_id). Espelha as 2 colunas de estado da
# ADR-324: linhagem e estado são distintas, e o ponteiro pode ficar órfão
# porque a FK é ON DELETE SET NULL.
SupersessionLinks = Mapping[str, tuple[Optional[datetime], Optional[str]]]

MAX_CHAIN_DEPTH = 5


# Devolve None — "pule este candidato" — em três casos que não podem virar
# identidade: ponteiro órfão (vencedora deletada por ON DELETE SET NULL, cuja
# row está morta sem apontar ninguém; devolvê-la seria ressuscitar, a classe da
# ADR-282 §5), ciclo, e cadeia mais funda que o cap.
def resolve_supersession_chain(
    start_id: str,
    links: SupersessionLinks,
    max_depth: int = MAX_CHAIN_DEPTH,
) -> Optional[str]:
    """Id da row viva ao fim da cadeia; `None` quando o candidato deve ser pulado."""
    seen: set[str] = set()
    current: Optional[str] = start_id
    while current is not None and current not in seen and len(seen) <= max_depth:
        seen.add(current)
        entry = links.get(current)
        if entry is None:
            return None
        superseded_at, superseded_by_id = entry
        if superseded_at is None:
            return current
        current = superseded_by_id
    return None


__all__ = ["resolve_supersession_chain", "SupersessionLinks", "MAX_CHAIN_DEPTH"]
