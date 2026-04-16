"""Pipeline CLI (E0–E7) — layout single-tenant na **raiz do repositório**.

Os scripts usam :mod:`scripts.pipeline_common` com ``PROJECT_DIR`` = raiz do repo:
``data/``, ``inbox/``, ``processed/``, etc. Isto é o fluxo **legado / local**
(documentado no manual e em ``CLAUDE.md``).

A aplicação web resolve o mesmo pipeline com
:class:`pipeline.context.WorkspaceContext` apontando para
``storage/<workspace_id>/`` (multi-tenant). Não importe modelos ``Document``
daqui — operações sobre uploads vivem em ``backend.app``.

Ferramentas de desenvolvimento (commit, hooks, codegen) estão em :mod:`dev`.
"""
