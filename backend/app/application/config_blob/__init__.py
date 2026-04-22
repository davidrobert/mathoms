"""Use cases do agregado ``ConfigBlob`` (ADR-101 R15).

Endpoints de ``/workspaces/{id}/config/{pipeline,institutions,report-layout}``
delegam aqui. O router mantém composições cross-aggregate (``/import``,
``/export``, ``/workspace`` settings) que não cabem em use case único —
ver ADR-112 (rollback criteria).
"""

from backend.app.application.config_blob.get_institution_config import (
    get_institution_config,
)
from backend.app.application.config_blob.get_pipeline_config import (
    get_pipeline_config,
)
from backend.app.application.config_blob.get_report_layout import (
    get_report_layout,
)
from backend.app.application.config_blob.update_institution_config import (
    update_institution_config,
)
from backend.app.application.config_blob.update_pipeline_config import (
    update_pipeline_config,
)
from backend.app.application.config_blob.update_report_layout import (
    update_report_layout,
)

__all__ = [
    "get_institution_config",
    "get_pipeline_config",
    "get_report_layout",
    "update_institution_config",
    "update_pipeline_config",
    "update_report_layout",
]
