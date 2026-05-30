"""ADR-275 D5 (l8) — purge de retenção: ``purge_expired_audit_logs`` apaga SÓ audit de leitura >365d, preserva leitura recente E todo audit de mutação (Art.16), e grava 1 meta-linha ``audit.purge`` (sem PII) que sobrevive a purges futuros."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_log import AuditLog
from backend.app.services.audit import READ_ACCESS_ACTIONS


def _audit(action: str, *, age_days: int) -> AuditLog:
    return AuditLog(
        action=action,
        resource_type="report",
        created_at=datetime.now(timezone.utc) - timedelta(days=age_days),
    )


@pytest.mark.asyncio
async def test_purge_removes_only_expired_read_audit(db: AsyncSession) -> None:
    db.add_all(
        [
            _audit("report.read", age_days=400),  # purgado
            _audit("transactions.export", age_days=370),  # purgado
            _audit("report.read", age_days=10),  # recente — sobrevive
            _audit("document.upload", age_days=400),  # mutação — sobrevive
            _audit("workspace.purge", age_days=999),  # mutação — sobrevive
        ]
    )
    await db.commit()

    from backend.app.tasks.periodic_tasks import purge_expired_audit_logs

    result = purge_expired_audit_logs.run()
    assert result["deleted"] == 2

    await db.rollback()
    remaining = (await db.execute(select(AuditLog.action))).scalars().all()
    # 2 read expirados apagados; 3 sobreviventes + 1 meta-linha audit.purge.
    assert "audit.purge" in remaining
    survivors = [a for a in remaining if a != "audit.purge"]
    assert sorted(survivors) == ["document.upload", "report.read", "workspace.purge"]
    # nenhum audit de mutação está no conjunto purgável
    assert "document.upload" not in READ_ACCESS_ACTIONS
    assert "workspace.purge" not in READ_ACCESS_ACTIONS


@pytest.mark.asyncio
async def test_purge_meta_row_has_no_pii(db: AsyncSession) -> None:
    db.add(_audit("report.read", age_days=400))
    await db.commit()

    from backend.app.tasks.periodic_tasks import purge_expired_audit_logs

    purge_expired_audit_logs.run()

    await db.rollback()
    meta = (
        (await db.execute(select(AuditLog).where(AuditLog.action == "audit.purge"))).scalars().one()
    )
    assert meta.details["deleted_count"] == 1
    assert "cutoff_date" in meta.details
    # meta-linha não é purgável (action fora de READ_ACCESS_ACTIONS).
    assert meta.action not in READ_ACCESS_ACTIONS
    assert meta.resource_type == "audit_log"


@pytest.mark.asyncio
async def test_purge_noop_when_nothing_expired(db: AsyncSession) -> None:
    db.add(_audit("report.read", age_days=10))
    await db.commit()

    from backend.app.tasks.periodic_tasks import purge_expired_audit_logs

    result = purge_expired_audit_logs.run()
    assert result["deleted"] == 0

    await db.rollback()
    actions = (await db.execute(select(AuditLog.action))).scalars().all()
    # nenhuma meta-linha quando nada foi purgado
    assert "audit.purge" not in actions
    assert actions == ["report.read"]
