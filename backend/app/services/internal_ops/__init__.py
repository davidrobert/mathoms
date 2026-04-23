"""Internal operations service — camada de serviço do console interno (ADR-116).

Fonte de verdade de regras de negócio para /admin/* e CLI futuro. UI e CLI
consomem essas funções; nunca reimplementam.
"""

from backend.app.services.internal_ops.audit import (
    AuditRecord,
    append_audit,
    read_audit,
)
from backend.app.services.internal_ops.results import OpResult

__all__ = ["AuditRecord", "append_audit", "read_audit", "OpResult"]
