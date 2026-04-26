"""DTOs dos blobs de config do workspace (Pipeline, Institution, ReportLayout, Transfer).

Re-exports convenientes — prefira estes imports ao invés de alcançar módulos
internos, para manter o pacote como fronteira do slice.

Os 4 blobs compartilham pacote porque (a) são estruturalmente análogos no
DB (ver ``models/config_blob.py``) e (b) o caller típico (router de config)
os usa juntos no import/export. Pipeline e Transfer têm sub-schemas tipados;
Institution e ReportLayout são wrappers opacos.
"""

from backend.app.schemas.dto.config_blob.command import (
    InstitutionConfigUpdateCommand,
    PipelineConfigUpdateCommand,
    ReportLayoutUpdateCommand,
    TransferConfigUpdateCommand,
)
from backend.app.schemas.dto.config_blob.mapper import (
    deep_merge,
    institution_blob_to_response,
    pipeline_blob_to_response,
    report_layout_to_response,
    transfer_blob_to_response,
)
from backend.app.schemas.dto.config_blob.response import (
    FileLimitsSchema,
    InstitutionConfigResponse,
    LLMConfigSchema,
    PipelineConfigResponse,
    QAThresholdsSchema,
    ReconciliationTolerancesSchema,
    ReportLayoutResponse,
    TransferConfigResponse,
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
    "TransferConfigResponse",
    # Command DTOs
    "InstitutionConfigUpdateCommand",
    "PipelineConfigUpdateCommand",
    "ReportLayoutUpdateCommand",
    "TransferConfigUpdateCommand",
    # Mappers + helpers
    "deep_merge",
    "institution_blob_to_response",
    "pipeline_blob_to_response",
    "report_layout_to_response",
    "transfer_blob_to_response",
]
