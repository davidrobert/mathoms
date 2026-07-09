"""Outcome tipado do reconcile de supersessão de `PropertyIdentity` (ADR-324)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SupersessionOutcome:
    """Contadores do reconcile — consumidos por log/print do E1.5c step 3b."""

    superseded: int
    cleared: int
    overrides_repointed: int
    overrides_merged: int

    @property
    def changed(self) -> bool:
        return bool(
            self.superseded or self.cleared or self.overrides_repointed or self.overrides_merged
        )


__all__ = ["SupersessionOutcome"]
