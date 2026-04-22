"""Use cases do agregado ``AuditLog`` (ADR-101 R15 · ADR-072).

Audit logs são imutáveis por definição (integridade). Não há use case
de delete/update — apenas leitura paginada.
"""

from backend.app.application.audit.list_audit_logs import list_audit_logs

__all__ = ["list_audit_logs"]
