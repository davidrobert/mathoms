#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline Common — shared utilities for all pipeline stages (E0–E7).

Consolidates config loading, path resolution, JSON I/O, and logging
that was previously duplicated across each eN_*.py script.

Usage:
    from scripts.pipeline_common import (
        PROJECT_DIR, CONFIG_DIR, DATA_DIR, PROCESSED_DIR, LOGS_DIR,
        INBOX_DIR, INBOX_PROCESSED_DIR, MEMBERS_DIR, OUTPUT_DIR,
        load_json_config, read_json, write_json, safe_float, log_stage,
    )
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


# =============================================================================
# Paths — re-inicializáveis via _init_config()
# =============================================================================
_DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent

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


_init_config(_DEFAULT_BASE_DIR)


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


# =============================================================================
# Schema validation
# =============================================================================

def validate_artifact(path: Path, schema_name: str) -> bool:
    """Validate JSON file against a schema in config/schemas/.

    Returns True if valid, validation disabled, or schema/jsonschema missing.
    In 'warn' mode (default), logs warning but returns True.
    In 'strict' mode, returns False on validation failure.
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

    try:
        jsonschema.validate(data, schema)
        return True
    except jsonschema.ValidationError as e:
        msg = f"Schema validation falhou para {path.name}: {e.message}"
        if sv.get("mode", "warn") == "warn":
            log_stage("WARN", msg)
            return True  # don't block pipeline
        log_stage("ERROR", msg)
        return False


# =============================================================================
# Numeric helpers
# =============================================================================

def safe_float(val: Any, default: float = 0.0) -> float:
    """Convert a value to float safely. Handles Brazilian BRL format."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return default
        try:
            return float(s)
        except ValueError:
            pass
        # Brazilian format: 1.234,56 → 1234.56
        try:
            return float(s.replace(".", "").replace(",", "."))
        except ValueError:
            log_stage("WARN", f"safe_float: não conseguiu converter '{s}' — usando {default}")
            return default
    return default


# =============================================================================
# Logging
# =============================================================================

def log_stage(stage: str, message: str) -> None:
    """Print a timestamped progress message to stderr."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {stage}: {message}", file=sys.stderr)
