"""Internal operations service — camada de serviço do console interno (ADR-116).

Fonte de verdade de regras de negócio para /admin/* e CLI futuro. UI e CLI
consomem essas funções; nunca reimplementam.
"""

from backend.app.services.internal_ops.anonymize_user import anonymize_user
from backend.app.services.internal_ops.audit import (
    AuditRecord,
    append_audit,
    read_audit,
)
from backend.app.services.internal_ops.delete_document import delete_document
from backend.app.services.internal_ops.hard_delete_user import hard_delete_user
from backend.app.services.internal_ops.list_reports import (
    ListReportsFilter,
    ReportSummary,
    list_reports,
)
from backend.app.services.internal_ops.list_user_workspaces import (
    UserWorkspaceSummary,
    list_user_workspaces,
)
from backend.app.services.internal_ops.metrics import MetricsSnapshot, get_metrics
from backend.app.services.internal_ops.purge_documents import (
    PurgeScope,
    purge_documents,
)
from backend.app.services.internal_ops.reset_password import (
    generate_temp_password,
    reset_password,
)
from backend.app.services.internal_ops.results import OpResult
from backend.app.services.internal_ops.set_developer_flag import set_developer_flag
from backend.app.services.internal_ops.update_user_email import update_user_email
from backend.app.services.internal_ops.update_user_profile import update_user_profile

__all__ = [
    "AuditRecord",
    "append_audit",
    "read_audit",
    "OpResult",
    "anonymize_user",
    "hard_delete_user",
    "reset_password",
    "generate_temp_password",
    "set_developer_flag",
    "update_user_email",
    "update_user_profile",
    "delete_document",
    "purge_documents",
    "PurgeScope",
    "get_metrics",
    "MetricsSnapshot",
    "list_reports",
    "ListReportsFilter",
    "ReportSummary",
    "list_user_workspaces",
    "UserWorkspaceSummary",
]
