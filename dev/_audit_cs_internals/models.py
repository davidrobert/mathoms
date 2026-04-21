"""Dataclasses e constantes do audit (A6g.1)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SEVERITY_RANK = {"critical": 0, "high": 1, "med": 2, "low": 3, "info": 4}

PY_INCLUDE_DIRS = ("pipeline", "scripts", "backend/app", "backend/tests", "tests", "dev")
TS_INCLUDE_DIR = "frontend/src"

EXCLUDE_PY_PATH_PREFIXES = (
    "frontend/src/generated/",
    "backend/app/generated/",
)
EXCLUDE_TS_PATH_PREFIXES = ("frontend/src/generated/",)

EXCLUDE_DIR_NAMES = frozenset({
    "__pycache__", "node_modules", ".venv", "venv", "dist", "build",
    ".next", "_scratch", "_archive", "storage", "data", "inbox",
    "inbox_processed", ".git",
})

FORBIDDEN_IDENTIFIERS = frozenset({"data", "handler", "Manager", "Helper", "Helpers", "Utils", "Service"})

FORBIDDEN_TS_FILENAMES = frozenset({
    "data.ts", "helpers.ts", "utils.ts", "manager.ts", "service.ts",
    "data.tsx", "helpers.tsx", "utils.tsx", "manager.tsx", "service.tsx",
})

MONEY_NAME_PATTERN = re.compile(r"(amount|valor|brl|price|cost|saldo|money|total)", re.IGNORECASE)

WHAT_COMMENT_PATTERNS = (
    re.compile(r"^\s*#\s*(increment|set|get|add|remove|return|check|update|delete)\s+\w", re.IGNORECASE),
    re.compile(r"^\s*#\s*used by\b", re.IGNORECASE),
    re.compile(r"^\s*#\s*added for\b", re.IGNORECASE),
    re.compile(r"^\s*#\s*removed in\b", re.IGNORECASE),
)

TS_ANY_PATTERN = re.compile(r":\s*any\b|\bas\s+any\b")
TS_FUNC_PATTERN = re.compile(
    r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*[<(]"
    r"|^(?:export\s+)?const\s+(\w+)\s*(?::\s*[^=]+)?=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[^=]+)?=>",
    re.MULTILINE,
)
TS_HEX_PATTERN = re.compile(r"#[0-9a-fA-F]{3,8}\b")


@dataclass(frozen=True)
class AuditConfig:
    output_dir: Path
    date: str
    format: str
    categories: frozenset[str]
    severities: frozenset[str]
    strict: bool
    path: Path | None


@dataclass(frozen=True)
class Offender:
    id: str
    category: str
    severity: str
    file: str
    line_start: int
    line_end: int
    length: int
    identifier: str
    message: str
    allowlisted: bool = False


@dataclass
class Summary:
    files_scanned_python: int = 0
    files_scanned_typescript: int = 0
    offenders_by_category: dict[str, int] = field(default_factory=dict)
    offenders_by_severity: dict[str, int] = field(default_factory=dict)
    offenders_by_directory: dict[str, dict[str, int]] = field(default_factory=dict)
