"""Dual-read transitório do match de ``TransactionOverride`` (ADR-282 slice 4):
sob ``override_natural_key_v2_enabled`` (flag por workspace) o match tenta o
``natural_key_hash`` v2 — recomputado da linha E4 via adapters de
``override_identity`` — e cai para o ``transaction_hash`` v1 legado quando o v2
não casa (override ainda não backfillado); flag off ⇒ match byte-idêntico ao
legado. Cada fallback emite log estruturado ``mathoms.categorization.dualread``
— gate empírico da M2 destrutiva."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from backend.app.core.logging import get_logger
from backend.app.models.transaction_override import TransactionOverride

OVERRIDE_NATURAL_KEY_V2_FLAG = "override_natural_key_v2_enabled"

logger = get_logger("categorization.dualread")


def log_v1_fallback(workspace_id: str, *, fallback_count: int = 1) -> None:
    """Match caiu para o v1 sob flag-ON — sinal de override não-backfillado."""
    logger.info(
        "override match caiu para transaction_hash v1 sob flag-ON (ADR-282)",
        extra={
            "event": "v1_fallback",
            "workspace_id": workspace_id,
            "v1_fallback_count": fallback_count,
        },
    )


@dataclass
class OverrideMatchIndex:
    """Índice de match por linha E4 — v2 primeiro, fallback v1 (ADR-282)."""

    workspace_id: str
    v2_enabled: bool
    by_natural_key: dict[str, TransactionOverride] = field(default_factory=dict)
    by_legacy_hash: dict[str, TransactionOverride] = field(default_factory=dict)
    v1_fallback_count: int = 0

    @classmethod
    def from_overrides(
        cls,
        overrides: Iterable[TransactionOverride],
        *,
        workspace_id: str,
        v2_enabled: bool,
    ) -> "OverrideMatchIndex":
        index = cls(workspace_id=workspace_id, v2_enabled=v2_enabled)
        for override in overrides:
            index.add(override)
        return index

    def add(self, override: TransactionOverride) -> None:
        self.by_legacy_hash[override.transaction_hash] = override
        if self.v2_enabled and override.natural_key_hash:
            self.by_natural_key[override.natural_key_hash] = override

    def match(
        self,
        *,
        natural_key_hash: Optional[str],
        legacy_hash: str,
    ) -> Optional[TransactionOverride]:
        if not self.v2_enabled:
            return self.by_legacy_hash.get(legacy_hash)
        if natural_key_hash is not None:
            via_v2 = self.by_natural_key.get(natural_key_hash)
            if via_v2 is not None:
                return via_v2
        via_v1 = self.by_legacy_hash.get(legacy_hash)
        if via_v1 is not None:
            self.v1_fallback_count += 1
            log_v1_fallback(self.workspace_id, fallback_count=self.v1_fallback_count)
        return via_v1
