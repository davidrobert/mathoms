"""Pytest hooks for tests/ — must load before tests import ``scripts.*``."""

import os
from pathlib import Path

import pytest

# pipeline_common requires MATHOMS_WORKSPACE_ROOT (strict); default to repo root for suite.
_REPO_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("MATHOMS_WORKSPACE_ROOT", str(_REPO_ROOT))

# ADR-171: `resolve_fernet_keys` prefere FERNET_KEYS (rotação) a FERNET_KEY, então
# pinar só o singular é inerte em máquina com rotação ativa. O `.env` não passa por
# `os.environ` — `pop` não o alcança; só a env var VAZIA sobrepõe o arquivo. Sem as
# duas linhas, a key da suíte é a de dev da máquina e local diverge do CI (RV7-02).
# Vale para subprocess que herda `os.environ` (ex.: test_cli_run_stage).
_TEST_FERNET_KEY = "NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA="
os.environ.setdefault("MATHOMS_FERNET_KEY", _TEST_FERNET_KEY)
os.environ["MATHOMS_FERNET_KEYS"] = ""

# A40.l58 §Escopo 4 — a suíte valida contrato em `strict` por default, sem depender
# de o CI lembrar de exportar a env. Antes, `config/pipeline.json` deixava `tests/`
# em `warn`: payload que violava o schema logava-e-passava, e o único passo strict do
# CI cobria **1 arquivo**. Medido em 2026-08-24: com a chave virada a suíte dá o mesmo
# resultado (7391/7391), então o custo é zero e o ganho é prospectivo — 23 validações
# por run deixam de aceitar drift em silêncio.
# `setdefault` de propósito: quem quiser reproduzir produção roda com
# `MATHOMS_PIPELINE_SCHEMA_MODE=warn` e vence esta linha.
os.environ.setdefault("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")


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
