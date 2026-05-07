#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline Common — shared utilities for all pipeline stages (E0–E7).

Consolidates config loading, path resolution, JSON I/O, and logging
that was previously duplicated across each eN_*.py script.

**Layout de paths (Fase 2 — strict):** a raiz do workspace **não** é mais
implícita na raiz do repositório. É obrigatório definir a variável de ambiente
``MATHOMS_WORKSPACE_ROOT`` para um diretório que contenha ``config/``, ``data/``,
``inbox/``, etc. (tipicamente ``storage/<workspace_id>/``). Os pontos de entrada
(``backend.app.main``, workers, ``pytest`` conftests, ``pipeline.run_dev``)
fazem ``setdefault`` para a raiz do repo **apenas** para carregar configs
partilhados em desenvolvimento; para pipeline sobre um tenant real, use
``export`` ou ``--root`` (ver docs/reference/SETUP.md).

Usage:
    from scripts.pipeline_common import (
        PROJECT_DIR, CONFIG_DIR, DATA_DIR, PROCESSED_DIR, LOGS_DIR,
        INBOX_DIR, INBOX_PROCESSED_DIR, MEMBERS_DIR, OUTPUT_DIR,
        load_json_config, read_json, write_json, write_json_atomic,
        safe_float, log_stage,
    )
"""

import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# =============================================================================
# Structured logging — all pipeline scripts should use this logger
# =============================================================================

_logger = logging.getLogger("fin.pipeline")

if not _logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(name)s.%(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    _logger.addHandler(_handler)
    _logger.setLevel(logging.DEBUG)


# =============================================================================
# Paths — re-inicializáveis via _init_config()
# =============================================================================
_REPO_ROOT = Path(__file__).resolve().parent.parent
# Alias legado (testes, restore): raiz do repositório — não usar como tenant.
_DEFAULT_BASE_DIR = _REPO_ROOT

# =============================================================================
# Config loading
# =============================================================================

_config_cache: Dict[str, dict] = {}


def _init_config(base_dir: Path) -> None:
    """(Re-)inicializa paths globais e limpa cache de config."""
    global PROJECT_DIR, CONFIG_DIR, DATA_DIR, PROCESSED_DIR, LOGS_DIR
    global E2_DIR, E3_DIR, E4_DIR, E5_DIR, E7_DIR
    global INBOX_DIR, INBOX_PROCESSED_DIR, MEMBERS_DIR, OUTPUT_DIR
    PROJECT_DIR = base_dir
    CONFIG_DIR = PROJECT_DIR / "config"
    DATA_DIR = PROJECT_DIR / "data"
    PROCESSED_DIR = PROJECT_DIR / "processed"
    LOGS_DIR = PROJECT_DIR / "logs"
    E2_DIR = PROCESSED_DIR / "E2_extracts"
    E3_DIR = PROCESSED_DIR / "E3_reconciled"
    E4_DIR = PROCESSED_DIR / "E4_unified"
    E5_DIR = PROCESSED_DIR / "E5_analysis"
    E7_DIR = PROCESSED_DIR / "E7_review"
    INBOX_DIR = PROJECT_DIR / "inbox"
    INBOX_PROCESSED_DIR = PROJECT_DIR / "inbox_processed"
    MEMBERS_DIR = PROJECT_DIR / "members"
    OUTPUT_DIR = PROJECT_DIR / "output"
    _config_cache.clear()


_MATHOMS_WORKSPACE_ROOT_ERR = """\
error: MATHOMS_WORKSPACE_ROOT is not set.

It must point to a workspace (tenant) root containing config/, data/, inbox/, …
Example:
  export MATHOMS_WORKSPACE_ROOT="$PWD/storage/<workspace_id>"

Offline runner:
  python -m pipeline.run_dev --root /path/to/tenant

See docs/reference/SETUP.md (MATHOMS_WORKSPACE_ROOT).
"""


def init_workspace_paths_from_env(*, strict: bool = True) -> None:
    """Initialise ``PROJECT_DIR`` / ``DATA_DIR`` / … from ``MATHOMS_WORKSPACE_ROOT``.

    Args:
        strict: quando ``True`` (default para CLI) encerra o processo com
            ``exit(2)`` se a env var estiver ausente ou inválida. Quando
            ``False`` (import-time, testes, wrappers web) apenas faz fallback
            para ``_DEFAULT_BASE_DIR`` silenciosamente — os wrappers de stage
            reinicializam via ``_init_config(ctx.root)`` antes de rodar.
    """
    raw = (os.environ.get("MATHOMS_WORKSPACE_ROOT") or "").strip()
    if not raw:
        if strict:
            sys.stderr.write(_MATHOMS_WORKSPACE_ROOT_ERR)
            raise SystemExit(2)
        _init_config(_DEFAULT_BASE_DIR)
        return
    p = Path(raw).expanduser().resolve()
    if not p.is_dir():
        if strict:
            sys.stderr.write(f"error: MATHOMS_WORKSPACE_ROOT is not a directory: {p}\n")
            raise SystemExit(2)
        _init_config(_DEFAULT_BASE_DIR)
        return
    _init_config(p)


# Fase 1.5.4: inicialização no import NUNCA é estrita. Scripts invocados
# diretamente (``python scripts/e2_extract.py``) devem chamar
# ``init_workspace_paths_from_env(strict=True)`` no seu bloco
# ``if __name__ == "__main__"`` para preservar a semântica fail-fast.
# Wrappers de stage (``pipeline/stages/*.py``) reinicializam via
# ``_init_config(ctx.root)``, portanto o estado inicial só importa se algum
# chamador usar os globals antes de passar por um wrapper.
init_workspace_paths_from_env(strict=False)


def load_json_config(name: str, *, required: bool = False) -> dict:
    """Load a JSON config file from config/ directory.

    Caches results so repeated calls don't re-read from disk.
    If required=True, raises FileNotFoundError instead of returning {}.
    """
    if name in _config_cache:
        return _config_cache[name]

    path = CONFIG_DIR / name
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required config not found: {path}")
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _config_cache[name] = data
        return data
    except (json.JSONDecodeError, OSError) as e:
        if required:
            raise
        print(f"  [WARN] Error loading {name}: {e}", file=sys.stderr)
        return {}


# =============================================================================
# JSON I/O
# =============================================================================


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Safely read a JSON file. Returns None on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log_stage("ERROR", f"Failed to read {path.name}: {e}")
        return None


def write_json(path: Path, data: Dict[str, Any], *, indent: int = 2) -> bool:
    """Write JSON with proper formatting. Returns True on success."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except (OSError, TypeError) as e:
        log_stage("ERROR", f"Failed to write {path.name}: {e}")
        return False


def write_json_atomic(
    path: Path, data: Dict[str, Any], *, indent: int = 2, fsync: bool = False
) -> bool:
    """Write JSON atomically via temp file + rename.

    Prevents partial writes on crash: the file is either fully written
    or not modified at all. Use ``fsync=True`` for critical artifacts
    (e.g. E5 analysis) where durability matters.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp", prefix=f".{path.stem}_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
                if fsync:
                    f.flush()
                    os.fsync(f.fileno())
            os.replace(tmp, str(path))
            return True
        except BaseException:
            # Clean up temp file on any error (including KeyboardInterrupt)
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except (OSError, TypeError) as e:
        log_stage("ERROR", f"Failed to write (atomic) {path.name}: {e}")
        return False


# =============================================================================
# Schema validation
# =============================================================================


def _effective_schema_validation_mode() -> str:
    """Return ``strict`` or ``warn``.

    ``MATHOMS_PIPELINE_SCHEMA_MODE`` overrides ``pipeline.json`` (for CI / local gates).
    """
    env = os.environ.get("MATHOMS_PIPELINE_SCHEMA_MODE", "").strip().lower()
    if env in ("strict", "warn"):
        return env
    config = load_json_config("pipeline.json")
    sv = config.get("schema_validation", {})
    return sv.get("mode", "warn")


def validate_artifact(path: Path, schema_name: str) -> bool:
    """Validate JSON file against a schema in config/schemas/.

    Returns True if valid, validation disabled, or schema/jsonschema missing.
    In 'warn' mode (default), logs warning but returns True.
    In 'strict' mode, returns False on validation failure.

    Set ``MATHOMS_PIPELINE_SCHEMA_MODE=strict`` to force strict without editing
    ``pipeline.json`` (recommended for CI jobs).
    """
    config = load_json_config("pipeline.json")
    sv = config.get("schema_validation", {})
    if not sv.get("enabled", False):
        return True

    try:
        import jsonschema
    except ImportError:
        log_stage("WARN", "jsonschema não instalado — validação de schema pulada")
        return True

    schema_path = CONFIG_DIR / "schemas" / schema_name
    if not schema_path.exists():
        return True

    schema = read_json(schema_path)
    data = read_json(path)
    if data is None or schema is None:
        return False

    mode = _effective_schema_validation_mode()
    try:
        jsonschema.validate(data, schema)
        return True
    except jsonschema.ValidationError as e:
        msg = f"Schema validation falhou para {path.name}: {e.message}"
        if mode == "warn":
            log_stage("WARN", msg)
            return True  # don't block pipeline
        log_stage("ERROR", msg)
        return False


# =============================================================================
# Numeric helpers
# =============================================================================


def safe_float(val: Any, default: float = 0.0, locale: str = "BRL") -> float:
    """Convert a value to float safely, respecting currency locale.

    Args:
        val: Value to convert.
        default: Fallback if conversion fails.
        locale: Currency locale — determines thousands/decimal separators.
            "BRL" (default): 1.234,56 → 1234.56 (dot=thousands, comma=decimal)
            "USD" / "EUR": 1,234.56 → 1234.56 (comma=thousands, dot=decimal)
    """
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return default
        # Strip currency symbols and whitespace
        for sym in ("R$", "US$", "€", "$", "£"):
            s = s.replace(sym, "").strip()
        try:
            return float(s)
        except ValueError:
            pass
        if locale in ("USD", "EUR"):
            # US/EU format: 1,234.56 → 1234.56
            try:
                return float(s.replace(",", ""))
            except ValueError:
                pass
        else:
            # Brazilian format: 1.234,56 → 1234.56
            try:
                return float(s.replace(".", "").replace(",", "."))
            except ValueError:
                pass
        log_stage(
            "WARN",
            f"safe_float: não conseguiu converter '{s}' (locale={locale}) — usando {default}",
        )
        return default
    return default


# =============================================================================
# Logging
# =============================================================================


def log_stage(stage: str, message: str) -> None:
    """Log a timestamped progress message via structured logger.

    Maps stage prefixes to log levels:
      ERROR → logging.ERROR
      WARN  → logging.WARNING
      otherwise → logging.INFO
    """
    stage_upper = stage.upper()
    if "ERROR" in stage_upper or "FATAL" in stage_upper:
        _logger.error("%s: %s", stage, message)
    elif "WARN" in stage_upper:
        _logger.warning("%s: %s", stage, message)
    else:
        _logger.info("%s: %s", stage, message)
