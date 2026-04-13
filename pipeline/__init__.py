"""
Fin Pipeline — package para execução programática do pipeline financeiro.

Uso via CLI (retrocompatível):
    python scripts/e_reset.py

Uso via Python (novo — API programática):
    from pipeline import run_pipeline, run_from, WorkspaceContext

    ctx = WorkspaceContext.default()
    result = run_pipeline(ctx)              # Pipeline determinístico completo
    result = run_from(ctx, "E5")            # De E5 em diante

    # Para web (multi-tenant):
    ctx = WorkspaceContext.for_tenant(tenant_root, config_overrides)
    result = run_pipeline(ctx)

Uso de stages individuais:
    from pipeline.stages import e3
    result = e3.run(ctx)
"""

__version__ = "0.2.0"

from pipeline.context import WorkspaceContext
from pipeline.orchestrator import (
    PipelineResult,
    StageResult,
    run_from,
    run_pipeline,
    run_stages,
)

__all__ = [
    "WorkspaceContext",
    "PipelineResult",
    "StageResult",
    "run_pipeline",
    "run_from",
    "run_stages",
]
