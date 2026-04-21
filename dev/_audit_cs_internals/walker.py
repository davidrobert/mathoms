"""File discovery com exclusões (A6g.1)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from dev._audit_cs_internals.models import (
    AuditConfig,
    EXCLUDE_DIR_NAMES,
    EXCLUDE_PY_PATH_PREFIXES,
    EXCLUDE_TS_PATH_PREFIXES,
    PY_INCLUDE_DIRS,
    REPO_ROOT,
    TS_INCLUDE_DIR,
)


def _iter_files(root: Path, suffixes: tuple[str, ...], exclude_prefixes: tuple[str, ...]) -> Iterable[Path]:
    """Yield files under root matching suffixes, honoring excludes."""
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(rel.startswith(p) for p in exclude_prefixes):
            continue
        if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
            continue
        yield path


def collect_python_files(config: AuditConfig) -> list[Path]:
    """Coleta .py sob PY_INCLUDE_DIRS respeitando --path."""
    if config.path and config.path.is_file():
        return [config.path] if config.path.suffix == ".py" else []
    if config.path and config.path.is_dir():
        return _collect_in_dir(config.path, (".py",), EXCLUDE_PY_PATH_PREFIXES)
    out: list[Path] = []
    for rel_dir in PY_INCLUDE_DIRS:
        dir_path = REPO_ROOT / rel_dir
        if dir_path.is_dir():
            out.extend(_iter_files(dir_path, (".py",), EXCLUDE_PY_PATH_PREFIXES))
    return sorted(set(out))


def collect_ts_files(config: AuditConfig) -> list[Path]:
    """Coleta .ts/.tsx sob frontend/src/ respeitando --path."""
    if config.path and config.path.is_file():
        return [config.path] if config.path.suffix in (".ts", ".tsx") else []
    base = REPO_ROOT / TS_INCLUDE_DIR
    if not base.is_dir():
        return []
    if config.path and config.path.is_dir():
        return _collect_in_dir(config.path, (".ts", ".tsx"), EXCLUDE_TS_PATH_PREFIXES)
    return sorted(_iter_files(base, (".ts", ".tsx"), EXCLUDE_TS_PATH_PREFIXES))


def _collect_in_dir(dir_path: Path, suffixes: tuple[str, ...], excludes: tuple[str, ...]) -> list[Path]:
    return sorted(_iter_files(dir_path, suffixes, excludes))
