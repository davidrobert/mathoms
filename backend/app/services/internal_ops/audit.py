"""Audit trail do console interno — persistido em ``internal_ops_audit`` (ADR-309).

Dois caminhos de escrita, ambos hard-fail (A30.l1):

- ``append_audit(record, db)`` — **default**: row na MESMA sessão da operação;
  o commit único do endpoint fecha mutação + audit ("audit existe ⟺ ação
  aconteceu"). Rollback da operação leva o audit junto — intencional (ADR-309
  D2; a semântica commit-separado do arquivo era limitação, não decisão).
- ``append_audit_autonomous(record)`` — exceção nomeada (ADR-309 D3) para
  eventos session-less (``ops.login``/``ops.login_failed``/``ops.logout``):
  transação própria curta; ``ops.login_failed`` precisa sobreviver ao 401.

Regras:
- Nunca persistir senha (nem mascarada) — ``_redact`` aplica blocklist.
- Nunca persistir conteúdo monetário total (ADR-110 masking).
- Retenção indefinida; nenhum purge job toca esta tabela (ADR-309 D5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.internal_ops_audit import InternalOpsAudit

_FORBIDDEN_KEYS = frozenset(
    {"password", "new_password", "hashed_password", "token", "jwt", "secret"}
)

_sink_log = logging.getLogger("mathoms.internal_ops.audit")


@dataclass(frozen=True)
class AuditRecord:
    """Evento imutável de audit interno."""

    action: str
    actor: str
    target_type: str | None = None
    target_id: str | None = None
    result: str = "ok"
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _redact(details: dict[str, Any]) -> dict[str, Any]:
    """Remove chaves sensíveis independentemente do caller."""
    return {k: v for k, v in details.items() if k.lower() not in _FORBIDDEN_KEYS}


def _to_row(record: AuditRecord) -> InternalOpsAudit:
    return InternalOpsAudit(
        action=record.action,
        actor=record.actor,
        target_type=record.target_type,
        target_id=record.target_id,
        result=record.result,
        details=_redact(record.details),
        created_at=datetime.fromisoformat(record.timestamp),
    )


def append_audit(record: AuditRecord, db: AsyncSession) -> None:
    """Adiciona o audit à sessão da operação — commit é do endpoint (ADR-309 D2)."""
    db.add(_to_row(record))


def append_audit_autonomous(record: AuditRecord) -> None:
    """Escrita autônoma para eventos session-less (ADR-309 D3). Hard-fail com CRITICAL."""
    from backend.app.core.database import SyncSessionLocal

    try:
        with SyncSessionLocal() as session:
            session.add(_to_row(record))
            session.commit()
    except Exception:
        _sink_log.critical(
            "internal_ops audit sink failure",
            extra={"action": record.action, "actor": record.actor, "result": record.result},
        )
        raise


def _entry_dict(row: InternalOpsAudit) -> dict[str, Any]:
    return {
        "action": row.action,
        "actor": row.actor,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "result": row.result,
        "details": dict(row.details or {}),
        "timestamp": row.created_at.isoformat(),
    }


async def read_audit(db: AsyncSession, *, limit: int | None = None) -> list[dict[str, Any]]:
    """Últimas ``limit`` entradas, mais recentes por último (paridade com o sink JSONL)."""
    stmt = select(InternalOpsAudit).order_by(InternalOpsAudit.created_at.desc())
    if limit is not None:
        stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [_entry_dict(r) for r in reversed(rows)]
