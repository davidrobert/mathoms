"""
Fin Pipeline — package para execução programática do pipeline financeiro.

Uso via CLI (retrocompatível):
    python scripts/e_reset.py

Uso via Python (novo):
    from pipeline.context import WorkspaceContext
    from pipeline.stages import e3

    ctx = WorkspaceContext.default()
    result = e3.run(ctx)
"""

__version__ = "0.1.0"
