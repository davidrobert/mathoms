"""Pipeline CLI (E0–E7) — paths do workspace via ``MATHOMS_WORKSPACE_ROOT``.

:mod:`scripts.pipeline_common` inicializa ``PROJECT_DIR``, ``DATA_DIR``, … a
partir da variável de ambiente **MATHOMS_WORKSPACE_ROOT** (directório com ``config/``,
``data/``, ``inbox/``, …). Não há default silencioso para ``./data/`` na raiz do
git: defina o tenant (ex.: ``export MATHOMS_WORKSPACE_ROOT="$PWD/storage/<ws_id>"``)
ou use ``python -m pipeline.run_dev --root …`` (define a variável antes dos
stages). Em testes e no arranque da API, o repositório faz ``setdefault`` para
a raiz do repo só para carregar configs partilhados.

A aplicação web usa :class:`pipeline.context.WorkspaceContext` por tenant; o
worker Celery define ``MATHOMS_WORKSPACE_ROOT`` para a raiz do tenant em cada run.

Não importe modelos ``Document`` daqui — operações sobre uploads vivem em
``backend.app``. Ferramentas de desenvolvimento (commit, hooks, codegen) estão
em :mod:`dev`.
"""
