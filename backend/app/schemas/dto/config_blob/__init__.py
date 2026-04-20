"""DTOs dos 3 blobs de config do workspace (Pipeline, Institution, ReportLayout).

Re-exports convenientes — prefira estes imports ao invés de alcançar módulos
internos, para manter o pacote como fronteira do slice.

Os 3 blobs compartilham pacote porque (a) são estruturalmente análogos no
DB (ver ``models/config_blob.py``) e (b) o caller típico (router de config)
os usa juntos no import/export. Pipeline tem sub-schemas tipados
(``LLMConfigSchema``, ``QAThresholdsSchema``...); os outros dois são
wrappers de ``config_json`` opaco.
"""

from backend.app.schemas.dto.config_blob.command import (
    InstitutionConfigUpdateCommand,
    PipelineConfigUpdateCommand,
    ReportLayoutUpdateCommand,
)
from backend.app.schemas.dto.config_blob.mapper import (
    deep_merge,
    institution_blob_to_response,
    pipeline_blob_to_response,
    report_layout_to_response,
)
from backend.app.schemas.dto.config_blob.response import (
    FileLimitsSchema,
    InstitutionConfigResponse,
    LLMConfigSchema,
    PipelineConfigResponse,
    QAThresholdsSchema,
    ReconciliationTolerancesSchema,
    ReportLayoutResponse,
)

__all__ = [
    # Response DTOs
    "FileLimitsSchema",
    "InstitutionConfigResponse",
    "LLMConfigSchema",
    "PipelineConfigResponse",
    "QAThresholdsSchema",
    "ReconciliationTolerancesSchema",
    "ReportLayoutResponse",
    # Command DTOs
    "InstitutionConfigUpdateCommand",
    "PipelineConfigUpdateCommand",
    "ReportLayoutUpdateCommand",
    # Mappers + helpers
    "deep_merge",
    "institution_blob_to_response",
    "pipeline_blob_to_response",
    "report_layout_to_response",
]
