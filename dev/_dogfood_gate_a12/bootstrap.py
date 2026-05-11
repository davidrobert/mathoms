"""Bootstrap de env vars + paths — chamado ANTES de importar backend."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRATCH = _REPO_ROOT / "_scratch"
_TEST_FERNET = "NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA="


def _add_repo_to_sys_path() -> None:
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))


def _ensure_scratch() -> None:
    _SCRATCH.mkdir(exist_ok=True)


def _silence_sqlalchemy_logger() -> None:
    """SQL echo + WARNING level — MATHOMS_GATE_DEBUG=1 reativa."""
    if os.environ.get("MATHOMS_GATE_DEBUG") == "1":
        return
    os.environ["MATHOMS_DEBUG"] = "0"
    import logging

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def _reset_db_file(db_file: Path) -> None:
    db_file.unlink(missing_ok=True)


def _set_env_vars(db_file: Path, storage_root: Path) -> None:
    os.environ["MATHOMS_FERNET_KEY"] = os.environ.get("MATHOMS_FERNET_KEY", _TEST_FERNET)
    os.environ["MATHOMS_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_file}"
    os.environ["MATHOMS_WORKSPACE_ROOT"] = str(_REPO_ROOT)
    os.environ["MATHOMS_STORAGE_ROOT"] = str(storage_root)


def bootstrap() -> tuple[Path, Path, Path]:
    """Idempotente: drop DB, configura env vars, silencia logs. Retorna paths."""
    _ensure_scratch()
    db_file = _SCRATCH / "dogfood_gate_a12.db"
    _reset_db_file(db_file)
    storage_root = _SCRATCH / "dogfood_gate_a12_storage"
    storage_root.mkdir(exist_ok=True)
    _set_env_vars(db_file, storage_root)
    _silence_sqlalchemy_logger()
    _add_repo_to_sys_path()
    return _SCRATCH, db_file, storage_root


__all__ = ["bootstrap"]
