"""Dual-read transitório do match de ``TransactionOverride`` (ADR-282 slice 4): sob
``override_natural_key_v2_enabled`` o match tenta o ``natural_key_hash`` v2 e cai para o
``transaction_hash`` v1 legado quando não casa; flag off ⇒ byte-idêntico ao legado.
Instrumenta o gate da M2 (ADR-282 §Emenda, A26.l4): conta ``v2_match`` (cobertura) e, sob
``override_dual_read_shadow_compare``, ``divergence`` (corretude — v2 casa a MESMA linha que
v1?); o gate de cobertura sozinho é cego a override grudado na linha errada. Contadores
per-request (ADR-111) drenados por ``persist_dualread_snapshot`` para ``AuditLog`` (fonte de
verdade do gate; não há log aggregator no stack)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.models.transaction_override import TransactionOverride
from backend.app.services.audit import AuditAction, audit_log_sync

OVERRIDE_NATURAL_KEY_V2_FLAG = "override_natural_key_v2_enabled"
OVERRIDE_DUAL_READ_SHADOW_COMPARE_FLAG = "override_dual_read_shadow_compare"

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


def log_v2_match(workspace_id: str, *, match_count: int = 1) -> None:
    """Match resolveu via natural_key v2 — prova de exercício real do v2 (gate cobertura)."""
    logger.info(
        "override match resolveu via natural_key v2 (ADR-282)",
        extra={
            "event": "v2_match",
            "workspace_id": workspace_id,
            "v2_match_count": match_count,
        },
    )


def log_divergence(workspace_id: str, *, divergence_count: int = 1) -> None:
    """Shadow-compare: v2 e v1 casaram linhas DIFERENTES — override sticky em risco."""
    logger.warning(
        "override shadow-compare: v2 diverge de v1 na mesma linha (ADR-282 §Emenda)",
        extra={
            "event": "divergence",
            "workspace_id": workspace_id,
            "divergence_count": divergence_count,
        },
    )


@dataclass
class OverrideMatchIndex:
    """Índice de match por linha E4 — v2 primeiro, fallback v1 (ADR-282)."""

    workspace_id: str
    v2_enabled: bool
    shadow_compare: bool = False
    by_natural_key: dict[str, TransactionOverride] = field(default_factory=dict)
    by_legacy_hash: dict[str, TransactionOverride] = field(default_factory=dict)
    v1_fallback_count: int = 0
    v2_match_count: int = 0
    divergence_count: int = 0

    @classmethod
    def from_overrides(
        cls,
        overrides: Iterable[TransactionOverride],
        *,
        workspace_id: str,
        v2_enabled: bool,
        shadow_compare: bool = False,
    ) -> "OverrideMatchIndex":
        index = cls(workspace_id=workspace_id, v2_enabled=v2_enabled, shadow_compare=shadow_compare)
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
        via_v2 = self.by_natural_key.get(natural_key_hash) if natural_key_hash else None
        if via_v2 is not None:
            self._record_v2_hit(via_v2, legacy_hash)
            return via_v2
        via_v1 = self.by_legacy_hash.get(legacy_hash)
        if via_v1 is not None:
            self.v1_fallback_count += 1
            log_v1_fallback(self.workspace_id, fallback_count=self.v1_fallback_count)
        return via_v1

    def _record_v2_hit(self, via_v2: TransactionOverride, legacy_hash: str) -> None:
        """Conta cobertura (v2_match) e, sob shadow_compare, divergência vs. o v1 (gate G2b)."""
        # Divergência = override migraria de transação sob o flip. NÃO altera o retorno
        # (v2 é a verdade em prod); só instrumenta o gate da M2 (ADR-282 §Emenda item 3).
        self.v2_match_count += 1
        log_v2_match(self.workspace_id, match_count=self.v2_match_count)
        if self.shadow_compare and via_v2 is not self.by_legacy_hash.get(legacy_hash):
            self.divergence_count += 1
            log_divergence(self.workspace_id, divergence_count=self.divergence_count)

    def snapshot(self) -> dict[str, int]:
        """Contadores per-request para o gate (drenados por ``persist_dualread_snapshot``)."""
        return {
            "v1_fallback": self.v1_fallback_count,
            "v2_match": self.v2_match_count,
            "divergence": self.divergence_count,
        }


def persist_dualread_snapshot(db: Session, index: OverrideMatchIndex) -> None:
    """Drena os contadores do índice para ``AuditLog`` no boundary do E4 (no-op se v2 não rodou; PII-zero)."""
    if not index.v2_enabled:
        return
    snap = index.snapshot()
    if snap["v2_match"] == 0 and snap["v1_fallback"] == 0:
        return
    audit_log_sync(
        db,
        action=AuditAction.override_v2_dualread_snapshot,
        resource_type="transaction_override",
        workspace_id=index.workspace_id,
        details=snap,
    )
