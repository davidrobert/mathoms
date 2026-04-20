"""Tests — ``scripts.pipeline_common`` é importável sem ``MATHOMS_WORKSPACE_ROOT``.

Fase 1.5.4: ``import scripts.pipeline_common`` não pode levantar ``SystemExit``.
Wrappers de stage reinicializam via ``_init_config(ctx.root)`` — o estado
inicial é apenas um fallback para ``_DEFAULT_BASE_DIR`` (repo root).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_import_without_workspace_root_does_not_exit(tmp_path):
    """Importar o módulo num subprocesso sem ``MATHOMS_WORKSPACE_ROOT`` retorna 0."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"MATHOMS_WORKSPACE_ROOT"}
    }
    env["PYTHONPATH"] = str(REPO_ROOT)
    result = subprocess.run(
        [sys.executable, "-c", "import scripts.pipeline_common"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"import failed — stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )


def test_strict_mode_still_fails_without_env(tmp_path):
    """``init_workspace_paths_from_env(strict=True)`` ainda sai com 2 sem env."""
    env = {k: v for k, v in os.environ.items() if k != "MATHOMS_WORKSPACE_ROOT"}
    env["PYTHONPATH"] = str(REPO_ROOT)
    code = (
        "from scripts.pipeline_common import init_workspace_paths_from_env;"
        "init_workspace_paths_from_env(strict=True)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 2
