"""Tipos do reconcile de supersessão de `PropertyIdentity` (ADR-324, ADR-376)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class SupersessionOutcome:
    """Contadores do reconcile — consumidos por log/print do E1.5c step 3b."""

    superseded: int
    cleared: int
    overrides_repointed: int
    overrides_merged: int
    # Vivas do workspace que o run não referenciou: detector de zumbi sem
    # segundo caminho de leitura (foi ter dois que fez forward-path e backfill
    # divergirem na primeira vez).
    unreferenced_live: int = 0

    @property
    def changed(self) -> bool:
        return bool(
            self.superseded or self.cleared or self.overrides_repointed or self.overrides_merged
        )


# `observed_pids` é o que torna a supersessão durável: fora dele o reconcile não
# seta NEM limpa. Antes, limpar toda row ausente do mapa de perdedoras revertia,
# a cada E1.5c, qualquer supersessão feita por sweep (ADR-376). A flip-safety da
# ADR-324 sobrevive porque o flip só ocorre entre rows que o run observou.
@dataclass(frozen=True)
class SupersessionScope:
    """Escopo observado por um run: fora dele, o estado de supersessão é absorvente."""

    workspace_id: str
    winner_by_pid: Mapping[str, str] = field(default_factory=dict)
    observed_pids: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        referenced = set(self.winner_by_pid) | set(self.winner_by_pid.values())
        fora = referenced - self.observed_pids
        if fora:
            raise ValueError(
                "winner_by_pid referencia pid fora de observed_pids: "
                f"esperado subconjunto de observed_pids ({len(self.observed_pids)} pids), "
                f"veio {sorted(fora)[:5]}"
            )


# Tripwire de fonte desconhecida: se uma 5ª era começar a produzir identidades
# que o run nunca referencia, isso aparece no log do E1.5c em vez de acumular
# em silêncio por meses, como aconteceu com o passivo que originou a ADR-376.
@dataclass(frozen=True)
class PropertyIdentityZombieWarning:
    """Identidades vivas que o run não referenciou."""

    workspace_id: str
    unreferenced_live: int

    def format(self) -> str:
        return (
            f"  [E1.5c] AVISO: {self.unreferenced_live} identidade(s) de imóvel viva(s) "
            f"não referenciada(s) por este run — rode o sweep de supersessão "
            f"(dev/backfill_property_supersession.py --dry-run) para inspecionar."
        )


__all__ = [
    "SupersessionOutcome",
    "SupersessionScope",
    "PropertyIdentityZombieWarning",
]
