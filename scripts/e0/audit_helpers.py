"""Helpers compartilhados pelos checks de ``scripts/e0_audit`` (A6g.2 — T1.c).

Extraído do módulo monolítico de 948 linhas. Centraliza:
- Globais de path (``PROJECT_DIR``, ``DATA_DIR``, ``E2_DIR``, ``INBOX_LOG``)
  inicializados via ``init_config()`` — ``scripts.e0_audit.main`` chama isso
  quando ``root_dir`` é passado (uso em ``pipeline/stages/e0_audit.py``).
- Parser de filenames (``parse_data_filename``, ``parse_e2_filename``).
- Normalização de strings (``normalize``).
- Mapeamentos canônicos do ``config/institutions.json``
  (``BANCO_CANONICAL``, ``TIPO_ALIASES``).

Convenção: outros módulos fazem ``from scripts.e0 import audit_helpers as _h``
e leem ``_h.DATA_DIR`` no call-time — garante que ``init_config(new_root)``
propague para todos os checks.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import scripts.pipeline_common as _pc

_DEFAULT_BASE_DIR = _pc._DEFAULT_BASE_DIR
load_json_config = _pc.load_json_config
log_stage = _pc.log_stage

# Paths re-inicializados por init_config().
SCRIPTS_DIR: Path = _DEFAULT_BASE_DIR / "scripts"
PROJECT_DIR: Path = _pc.PROJECT_DIR
DATA_DIR: Path = _pc.DATA_DIR
E2_DIR: Path = _pc.E2_DIR
INBOX_LOG: Path = _pc.LOGS_DIR / "inbox_log.md"


def init_config(base_dir: Path) -> None:
    """(Re-)inicializa paths globais a partir de ``base_dir``."""
    global SCRIPTS_DIR, PROJECT_DIR, DATA_DIR, E2_DIR, INBOX_LOG
    _pc._init_config(base_dir)
    SCRIPTS_DIR = base_dir / "scripts"
    PROJECT_DIR = _pc.PROJECT_DIR
    DATA_DIR = _pc.DATA_DIR
    E2_DIR = _pc.E2_DIR
    INBOX_LOG = _pc.LOGS_DIR / "inbox_log.md"


init_config(_pc.PROJECT_DIR)


# Load institution mappings from config/institutions.json — comportamento
# legado: leitura única no import (não re-lê em init_config subsequente).
_INSTITUTIONS = load_json_config("institutions.json")
BANCO_CANONICAL: dict[str, str] = _INSTITUTIONS.get("banco_canonical", {})
TIPO_ALIASES: dict[str, list[str]] = _INSTITUTIONS.get("tipo_aliases", {})


def normalize(s: str) -> str:
    """Lowercase, strip accents, replace spaces/hyphens with underscore."""
    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[\s\-]+", "_", s)
    return s


def parse_data_filename(filename: str) -> dict[str, str]:
    """Parse a data/ filename like 'bradesco_extratoconta_202501_202512-0_original.pdf'
    into components: banco, tipo, periodo_raw."""
    # Remove -0_original suffix and extension
    stem = re.sub(r"-0_original$", "", Path(filename).stem)
    parts = stem.split("_")

    if len(parts) < 2:
        return {"banco": parts[0] if parts else "", "tipo": "", "periodo_raw": ""}

    banco = parts[0]
    # tipo is everything between banco and the first date-like segment
    tipo_parts = []
    periodo_parts = []
    for p in parts[1:]:
        if re.match(r"^\d{6}", p) and tipo_parts:
            periodo_parts.append(p)
        elif periodo_parts:
            # Already collecting period, this is an anomaly
            periodo_parts.append(p)
        else:
            tipo_parts.append(p)

    # If no period found, try again: tipo might be just parts[1]
    if not periodo_parts and len(parts) > 2:
        for i, p in enumerate(parts[1:], 1):
            if re.match(r"^\d{6}", p):
                tipo_parts = parts[1:i]
                periodo_parts = parts[i:]
                break

    tipo = "_".join(tipo_parts) if tipo_parts else ""
    periodo_raw = "_".join(periodo_parts) if periodo_parts else ""

    return {"banco": banco, "tipo": tipo, "periodo_raw": periodo_raw}


def parse_e2_filename(filename: str) -> dict[str, str]:
    """Parse an E2 filename like 'bradesco_extratoconta_202501_202512-2_extract.json'."""
    stem = re.sub(r"-2_extract$", "", Path(filename).stem)
    # Also handle -0_original-2_extract (Itaú files with double suffix)
    stem = re.sub(r"-0_original$", "", stem)
    parts = stem.split("_")

    if len(parts) < 2:
        return {"banco": parts[0] if parts else "", "tipo": "", "periodo_raw": ""}

    banco = parts[0]
    tipo_parts = []
    periodo_parts = []
    for p in parts[1:]:
        if re.match(r"^\d{6}", p):
            periodo_parts.append(p)
        elif periodo_parts:
            periodo_parts.append(p)
        else:
            tipo_parts.append(p)

    if not periodo_parts and len(parts) > 2:
        for i, p in enumerate(parts[1:], 1):
            if re.match(r"^\d{6}", p):
                tipo_parts = parts[1:i]
                periodo_parts = parts[i:]
                break

    tipo = "_".join(tipo_parts) if tipo_parts else ""
    periodo_raw = "_".join(periodo_parts) if periodo_parts else ""

    return {"banco": banco, "tipo": tipo, "periodo_raw": periodo_raw}


__all__ = [
    "BANCO_CANONICAL",
    "DATA_DIR",
    "E2_DIR",
    "INBOX_LOG",
    "PROJECT_DIR",
    "SCRIPTS_DIR",
    "TIPO_ALIASES",
    "init_config",
    "load_json_config",
    "log_stage",
    "normalize",
    "parse_data_filename",
    "parse_e2_filename",
]
