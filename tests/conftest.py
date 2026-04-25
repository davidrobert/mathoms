"""Pytest hooks for tests/ — must load before tests import ``scripts.*``."""

import os
from pathlib import Path

import pytest

# pipeline_common requires MATHOMS_WORKSPACE_ROOT (strict); default to repo root for suite.
_REPO_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("MATHOMS_WORKSPACE_ROOT", str(_REPO_ROOT))


@pytest.fixture(autouse=True)
def _reset_pipeline_common_globals():
    """Restaura globals de ``pipeline_common`` ao default após cada teste.

    Stages legados rodam ``_init_config(workspace_root)`` em ``main_with_store``
    e mutam ``PROJECT_DIR``/``CONFIG_DIR``/etc. para o tmp_path. Sem reset,
    testes posteriores que dependem do default (ex.: ``load_json_config``)
    veem caminhos do tenant temporário e falham. Antes de A6c, o reset vinha
    no ``finally`` do ``main(root_dir)`` legado.
    """
    yield
    from scripts.pipeline_common import _DEFAULT_BASE_DIR, _init_config

    _init_config(_DEFAULT_BASE_DIR)
