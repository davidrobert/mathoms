"""Response DTOs dos 3 blobs de config do workspace.

Wire shape retornado por ``GET /workspaces/{ws}/config/{pipeline,institutions,
report-layout}`` — mudanças aqui são **breaking** para o frontend.

**Pipeline** tem sub-schemas tipados (``LLMConfigSchema``, ``QAThresholdsSchema``
etc.) porque a superfície editada pelo usuário é pequena e bem definida.
**Institution** e **ReportLayout** são opaco (``config_json: dict[str, Any]``)
porque hospedam estrutura profunda/variável (padrões por banco, layout do
relatório E6) — tipá-los duplicaria o schema do disco sem ganho.

Compat binária: ``schemas.config`` re-exporta estes nomes como
``PipelineConfigSchema``, ``InstitutionConfigSchema``, ``ReportLayoutSchema``
durante a janela de transição A6e.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Pipeline — sub-schemas tipados (superfície editada pelo usuário)
# ---------------------------------------------------------------------------


class ReconciliationTolerancesSchema(BaseModel):
    """Tolerâncias numéricas para reconciliação E3.

    ``saldo_diff`` e ``baseline_irpf_diff`` são **tolerâncias de
    reconciliação**, não valores monetários: ADR-090 (Decimal money) não
    se aplica. Nome persistido em ``config/pipeline.json`` + schema —
    rename exigiria migração. Aceitos como ``P5_float_money=1`` no
    audit baseline (A6g.3b).
    """

    saldo_diff: float = Field(default=0.01, ge=0)
    temporal_gap_days: int = Field(default=2, ge=0)
    baseline_irpf_diff: float = Field(default=1.0, ge=0)


class QAThresholdsSchema(BaseModel):
    """Limiares de QA para cross-validation E7 (CV1-CV14)."""

    score_diff_max: float = Field(default=0.5, ge=0)
    patrimonio_composicao_diff_pct_max: float = Field(default=5, ge=0)
    cv_fluxo_diff_max: float = Field(default=100, ge=0)
    cv_taxa_poupanca_diff_pp_max: float = Field(default=5, ge=0)
    cv_if_monthly_diff_max: float = Field(default=500, ge=0)
    cv_if_progress_diff_pct_max: float = Field(default=2, ge=0)
    cv_endividamento_diff_pct_max: float = Field(default=1, ge=0)
    cv_reserva_cobertura_diff_max: float = Field(default=1, ge=0)
    qa_unidentified_target_pct: float = Field(default=10.0, ge=0, le=100)


class LLMConfigSchema(BaseModel):
    """Configuração do LLM usado em E0-route/E1/E1.5/E2-llm/E7-review."""

    model: str = Field(default="claude-sonnet-4-20250514", min_length=1)
    max_tokens: int = Field(default=500, ge=1, le=200000)
    confidence_threshold: float = Field(default=0.7, ge=0, le=1)


class FileLimitsSchema(BaseModel):
    """Limites de upload/preview por tipo de arquivo."""

    preview_max_chars: int = Field(default=2000, ge=100)
    preview_max_rows: int = Field(default=20, ge=1)
    min_pdf_bytes: int = Field(default=1024, ge=0)
    min_xls_bytes: int = Field(default=40000, ge=0)
    min_csv_bytes: int = Field(default=500, ge=0)


class PipelineConfigResponse(BaseModel):
    """Resposta do ``GET /config/pipeline``.

    Todos os campos são ``Optional`` para que blobs incompletos (novos ou
    migrados de versões antigas) continuem validando — o pipeline tem
    defaults próprios em ``pipeline_common.py`` para chaves ausentes.
    """

    llm: Optional[LLMConfigSchema] = None
    file_limits: Optional[FileLimitsSchema] = None
    reconciliation: Optional[dict[str, Any]] = None
    qa_thresholds: Optional[QAThresholdsSchema] = None
    artifact_names: Optional[dict[str, str]] = None
    log_files: Optional[dict[str, Any]] = None
    period_regex: Optional[dict[str, str]] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Institution — wrapper opaco (estrutura profunda por banco)
# ---------------------------------------------------------------------------


class InstitutionConfigResponse(BaseModel):
    """Resposta do ``GET /config/institutions``.

    ``config_json`` hospeda ``institutions.json`` inteiro: padrões regex por
    banco, mapeamento doc_type → parser, cartões, etc. Estrutura varia e
    cresce com novos bancos — tipar aqui seria retrabalho a cada parser novo.
    """

    config_json: dict[str, Any]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# ReportLayout — wrapper opaco (YAML com comentários)
# ---------------------------------------------------------------------------


class ReportLayoutResponse(BaseModel):
    """Resposta do ``GET /config/report-layout``.

    ``config_json`` é o conteúdo de ``report_layout.yaml`` convertido para
    dict (seções, cards, charts toggles do relatório E6). Único YAML do
    projeto — justificativa documentada em CLAUDE.md (preserva comentários
    inline extensos na edição).
    """

    config_json: dict[str, Any]

    model_config = {"from_attributes": True}
