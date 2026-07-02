"""
Fin Pipeline — package para execução programática do pipeline financeiro.

Pipeline roda exclusivamente via backend (Celery worker). Para debug
local: `make dev` + `POST /pipeline/run` (ADR-212).

Uso via Python (API programática):
    from pipeline import run_pipeline, run_from, WorkspaceContext

    ctx = WorkspaceContext.default()
    result = run_pipeline(ctx)              # Pipeline determinístico completo
    result = run_from(ctx, "analyze_finances")  # De E5 em diante

    # Para web (multi-tenant):
    ctx = WorkspaceContext.for_tenant(tenant_root, config_overrides)
    result = run_pipeline(ctx)

Uso de stages individuais:
    from pipeline.stages import reconcile_transactions
    result = reconcile_transactions.run(ctx)
"""

__version__ = "0.2.0"

__all__ = [
    "WorkspaceContext",
    "PipelineResult",
    "StageResult",
    "run_pipeline",
    "run_from",
    "run_stages",
]

_ORCHESTRATOR_EXPORTS = frozenset(__all__) - {"WorkspaceContext"}


def __getattr__(name: str):
    # Lazy re-export (PEP 562): `python -m pipeline.orchestrator` (CLI A3.cli)
    # exige que o package não pré-importe o módulo (double-import warning do
    # runpy contamina o stderr estruturado) e o cold start do subprocess não
    # deve pagar a árvore de domínio ao importar só o package.
    if name == "WorkspaceContext":
        from pipeline.context import WorkspaceContext

        return WorkspaceContext
    if name in _ORCHESTRATOR_EXPORTS:
        import importlib

        return getattr(importlib.import_module("pipeline.orchestrator"), name)
    raise AttributeError(f"module 'pipeline' has no attribute {name!r}")
