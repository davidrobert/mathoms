"""O `.dockerignore` da raiz exclui todo `config/*` que o git proíbe.

Os Dockerfiles (backend, frontend, pipeline-service) fazem `COPY config/` com
contexto na raiz. Um build a partir de checkout local com `config/passwords.txt`
(senhas de PDF) ou `config/internal_operators.yaml` (hashes bcrypt, ADR-116)
gravava os arquivos numa layer da imagem e no cache do buildx. A lista de
proibidos é importada de `dev/check_forbidden_paths.py`, nunca copiada.
"""

from __future__ import annotations

import importlib.util
import posixpath
import re
from collections.abc import Iterable
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DOCKERIGNORE = _REPO_ROOT / ".dockerignore"
_MODULE_PATH = _REPO_ROOT / "dev" / "check_forbidden_paths.py"
_SPEC = importlib.util.spec_from_file_location("check_forbidden_paths", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
cfp = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cfp)

_Rule = tuple[bool, re.Pattern[str]]


def _pattern_regex(pattern: str) -> re.Pattern[str]:
    """Glob do `.dockerignore` → regex (semântica do moby/patternmatcher)."""
    if "[" in pattern or "\\" in pattern:
        raise ValueError(f"classe/escape de glob não suportado pelo matcher do teste: {pattern!r}")
    parts = re.split(r"(\*\*/|\*\*|\*|\?)", pattern)
    tokens = {"**/": "(?:.*/)?", "**": ".*", "*": "[^/]*", "?": "[^/]"}
    return re.compile("".join(tokens.get(p, re.escape(p)) for p in parts) + r"\Z")


def _parse_rules(text: str) -> list[_Rule]:
    rules: list[_Rule] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        pattern = posixpath.normpath(line.removeprefix("!").strip().lstrip("/"))
        rules.append((negated, _pattern_regex(pattern)))
    return rules


def _is_excluded(path: str, rules: list[_Rule]) -> bool:
    """Última regra que casa vence; regra que casa um diretório-pai exclui o filho."""
    parts = path.split("/")
    candidates = ["/".join(parts[: i + 1]) for i in range(len(parts))]
    excluded = False
    for negated, regex in rules:
        if any(regex.match(c) for c in candidates):
            excluded = not negated
    return excluded


def _uncovered_config_entries(forbidden: Iterable[str], dockerignore_text: str) -> list[str]:
    rules = _parse_rules(dockerignore_text)
    return [p for p in forbidden if p.startswith("config/") and not _is_excluded(p, rules)]


def _forbidden_config_files() -> list[str]:
    return [p for p in cfp.FORBIDDEN_FILES if p.startswith("config/")]


def test_dockerignore_covers_every_forbidden_config_file() -> None:
    text = _DOCKERIGNORE.read_text(encoding="utf-8")
    assert _uncovered_config_entries(cfp.FORBIDDEN_FILES, text) == []


def test_forbidden_list_carries_the_config_secrets() -> None:
    # Anti-vacuidade: se o recorte `config/` esvaziar, o teste acima passa sem medir nada.
    forbidden = _forbidden_config_files()
    assert "config/passwords.txt" in forbidden
    assert "config/internal_operators.yaml" in forbidden


def test_dockerignore_negative_control_detects_dropped_entry() -> None:
    lines = _DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if line.strip() != "config/passwords.txt"]
    assert len(kept) == len(lines) - 1, "config/passwords.txt sumiu do .dockerignore"
    dropped = "\n".join(kept)
    assert _uncovered_config_entries(cfp.FORBIDDEN_FILES, dropped) == ["config/passwords.txt"]


@pytest.mark.parametrize(
    "path",
    [
        "config/pipeline.json",
        "config/report_layout.yaml",
        "config/schemas/e5_analysis.schema.json",
        "config/internal_operators.example.yaml",
        ".env.example",
        "backend/app/main.py",
    ],
)
def test_dockerignore_keeps_build_inputs_in_context(path: str) -> None:
    # Excluir `config` inteiro "resolveria" o vazamento e quebraria o build.
    rules = _parse_rules(_DOCKERIGNORE.read_text(encoding="utf-8"))
    assert not _is_excluded(path, rules), f"{path} saiu do contexto de build"


@pytest.mark.parametrize(
    "path",
    [".env", ".env.local", "storage/ws/doc.pdf", "frontend/node_modules/x/index.js", "mathoms.db"],
)
def test_dockerignore_matcher_excludes_known_paths(path: str) -> None:
    rules = _parse_rules(_DOCKERIGNORE.read_text(encoding="utf-8"))
    assert _is_excluded(path, rules), f"matcher do teste não reproduz a exclusão de {path}"
