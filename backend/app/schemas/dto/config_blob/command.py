"""Command DTOs (inputs de write) dos 3 blobs de config.

**Semântica de update — diferença importante entre os 3**:

- ``PipelineConfigUpdateCommand`` → **partial merge** (deep merge). Só
  campos fornecidos são mesclados na config existente. Reflete a natureza
  tipada do pipeline (usuário ajusta 1-2 limiares, não reescreve tudo).

- ``InstitutionConfigUpdateCommand`` → **replace total**. Wrapper só aceita
  ``config_json`` inteiro porque a estrutura interna é profunda e
  heterogênea — merge parcial aqui seria ambíguo (o que significa "partial
  replace" no meio de um regex de banco?).

- ``ReportLayoutUpdateCommand`` → **replace total**. Mesmo raciocínio do
  Institution — o YAML inteiro é editado de uma vez.

Essa diferença está implementada no router (ver
``api/config.py::update_pipeline_config`` vs ``update_institution_config`` /
``update_report_layout``), não aqui. Os schemas só declaram o wire shape.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from backend.app.schemas.dto.config_blob.response import (
    FileLimitsSchema,
    LLMConfigSchema,
    QAThresholdsSchema,
)


class PipelineConfigUpdateCommand(BaseModel):
    """Input do ``PUT /config/pipeline`` — partial update (deep merge).

    Campos ausentes **não** são mesclados (preservam o valor atual).
    Campos presentes substituem o valor atual. Para dicts aninhados
    (``reconciliation``, ``log_files``, ``artifact_names``,
    ``period_regex``) o merge é **recursivo** (ver ``_deep_merge`` no
    router).
    """

    llm: Optional[LLMConfigSchema] = None
    file_limits: Optional[FileLimitsSchema] = None
    reconciliation: Optional[dict[str, Any]] = None
    qa_thresholds: Optional[QAThresholdsSchema] = None
    artifact_names: Optional[dict[str, str]] = None
    log_files: Optional[dict[str, Any]] = None
    period_regex: Optional[dict[str, str]] = None


class InstitutionConfigUpdateCommand(BaseModel):
    """Input do ``PUT /config/institutions`` — replace total.

    ``config_json`` inteiro substitui o existente. Para adicionar um banco
    novo, o caller envia o blob completo com o novo banco incluído.
    """

    config_json: dict[str, Any] = Field(
        ..., description="Conteúdo inteiro de institutions.json — substitui o atual."
    )


class ReportLayoutUpdateCommand(BaseModel):
    """Input do ``PUT /config/report-layout`` — replace total.

    ``config_json`` inteiro substitui o existente (seções, cards, charts
    toggles do relatório E6).
    """

    config_json: dict[str, Any] = Field(
        ..., description="Conteúdo inteiro de report_layout.yaml — substitui o atual."
    )


class TransferConfigUpdateCommand(BaseModel):
    """Input do ``PUT /config/transfer`` (ADR-130) — replace total das 4 listas/dict."""

    patterns_pix: list[str] = Field(default_factory=list)
    patterns_global: list[str] = Field(default_factory=list)
    patterns_bank_specific: dict[str, list[str]] = Field(default_factory=dict)
    recipients: list[str] = Field(default_factory=list)
