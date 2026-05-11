"""Repository thin de ``CategorizationRule`` (ADR-186 §D3 · ADR-097 D3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.models.categorization_rule import CategorizationRule


class CategorizationRuleRepository:
    """CRUD básico de ``categorization_rules``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, *, rule_id: str) -> Optional[CategorizationRule]:
        return self._session.get(CategorizationRule, rule_id)

    def list_for_workspace(
        self,
        *,
        workspace_id: str,
        enabled_only: bool = True,
    ) -> list[CategorizationRule]:
        """Lista regras ordenadas por (priority desc, len(keyword) desc, created_at asc)."""
        stmt = select(CategorizationRule).where(CategorizationRule.workspace_id == workspace_id)
        if enabled_only:
            stmt = stmt.where(CategorizationRule.enabled.is_(True))
        rows = self._session.execute(stmt).scalars().all()
        # SQLite não tem suporte robusto a ORDER BY length(); ordenamos em Python.
        return sorted(
            rows,
            key=lambda r: (-r.priority, -len(r.keyword), r.created_at),
        )

    def create(self, rule: CategorizationRule) -> CategorizationRule:
        """Persiste regra nova; ``flush`` para popular ``id`` sem fechar tx."""
        self._session.add(rule)
        self._session.flush()
        return rule

    def disable(self, *, rule_id: str) -> None:
        """Soft-disable: ``enabled = False``. Mantém linha para auditoria."""
        self._session.execute(
            update(CategorizationRule)
            .where(CategorizationRule.id == rule_id)
            .values(enabled=False, updated_at=datetime.now(timezone.utc))
        )

    def bump_applied_count(self, *, rule_id: str, delta: int = 1) -> None:
        """Incrementa ``applied_count`` (telemetria de saúde — D6 da ADR-186)."""
        self._session.execute(
            update(CategorizationRule)
            .where(CategorizationRule.id == rule_id)
            .values(
                applied_count=CategorizationRule.applied_count + delta,
                updated_at=datetime.now(timezone.utc),
            )
        )

    def bump_revert_count_manual_edit(self, *, rule_id: str, delta: int = 1) -> None:
        """KPI "regra ruim" (§D3): override 'rule' virou 'manual' com categoria diferente."""
        self._session.execute(
            update(CategorizationRule)
            .where(CategorizationRule.id == rule_id)
            .values(
                revert_count_manual_edit=(CategorizationRule.revert_count_manual_edit + delta),
                updated_at=datetime.now(timezone.utc),
            )
        )

    def bump_revert_count_rule_disabled(self, *, rule_id: str, delta: int = 1) -> None:
        """Sinal FRACO de abandono (§D3): ``DELETE /rules/{id}`` (soft-delete)."""
        self._session.execute(
            update(CategorizationRule)
            .where(CategorizationRule.id == rule_id)
            .values(
                revert_count_rule_disabled=(CategorizationRule.revert_count_rule_disabled + delta),
                updated_at=datetime.now(timezone.utc),
            )
        )
