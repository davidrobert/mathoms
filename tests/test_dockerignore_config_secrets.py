"""O `.dockerignore` da raiz exclui o que o git proíbe, na profundidade do gate.

Os Dockerfiles (backend, frontend, pipeline-service) fazem `COPY config/`,
`COPY backend/`… com contexto na raiz. Um build a partir de checkout local com
`config/passwords.txt` (senhas de PDF), `config/internal_operators.yaml` (hashes
bcrypt, ADR-116) ou `backend/.env` (chaves Fernet) gravava os arquivos numa
layer da imagem e no cache do buildx. As listas de proibidos são importadas de
`dev/check_forbidden_paths.py`, nunca copiadas.
"""

from __future__ import annotations

import importlib.util
import posixpath
import re
import subprocess
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


# --- Proibidos em qualquer diretório: `.env`, denylist do dogfood, SQLite ---
#
# O gate do git bloqueia FORBIDDEN_BASENAMES/FORBIDDEN_SUFFIXES em qualquer
# profundidade, mas padrão sem `**/` no `.dockerignore` só casa a raiz do
# contexto: `backend/.env` (lido pelo `env_file` de backend/app/core/config.py)
# passava pelo `COPY backend/`, e `frontend/.env.production` ia para o
# `.next/standalone` da imagem final. FORBIDDEN_DIRS fica de fora de propósito:
# no gate eles também valem só na raiz.

_SQLITE_SIDECARS = ("-wal", "-shm", "-journal")
# Versionados fora do contexto de propósito: nenhum é input de build.
_EXCLUDED_ON_PURPOSE = (".github/", ".claude/")
_ENV_TEMPLATE = re.compile(r"\.env(?:\.[^/]+)?\.example")


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=_REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout
    return [p for p in out.split("\0") if p]


def _top_level_dirs() -> list[str]:
    return sorted({p.split("/", 1)[0] for p in _tracked_files() if "/" in p})


def _anywhere_forbidden_names() -> list[str]:
    dbs = [f"probe{suffix}" for suffix in cfp.FORBIDDEN_SUFFIXES]
    sidecars = [f"{db}{sidecar}" for db in dbs for sidecar in _SQLITE_SIDECARS]
    return [*cfp.FORBIDDEN_BASENAMES, *dbs, *sidecars]


def _uncovered_at_any_depth(names: Iterable[str], dockerignore_text: str) -> list[str]:
    rules = _parse_rules(dockerignore_text)
    dirs = [*_top_level_dirs(), "backend/app/core"]
    paths = [p for n in names for p in (n, *(f"{d}/{n}" for d in dirs))]
    return [p for p in paths if not _is_excluded(p, rules)]


def _is_excluded_on_purpose(path: str) -> bool:
    template = _ENV_TEMPLATE.fullmatch(posixpath.basename(path))
    return path.startswith(_EXCLUDED_ON_PURPOSE) or template is not None


def _excluded_tracked_files(dockerignore_text: str) -> list[str]:
    rules = _parse_rules(dockerignore_text)
    return [p for p in _tracked_files() if _is_excluded(p, rules)]


def test_dockerignore_excludes_anywhere_forbidden_names_at_any_depth() -> None:
    text = _DOCKERIGNORE.read_text(encoding="utf-8")
    assert _uncovered_at_any_depth(_anywhere_forbidden_names(), text) == []


def test_anywhere_forbidden_universe_is_not_vacuous() -> None:
    assert ".env" in cfp.FORBIDDEN_BASENAMES
    assert ".db" in cfp.FORBIDDEN_SUFFIXES
    assert {"backend", "config", "frontend", "pipeline"} <= set(_top_level_dirs())


def test_dockerignore_negative_control_detects_root_only_env() -> None:
    # A regressão de origem: `.env` sem `**/` só casa a raiz do contexto.
    lines = _DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
    root_only = [".env" if line.strip() == "**/.env" else line for line in lines]
    assert root_only != lines, "**/.env sumiu do .dockerignore"
    uncovered = _uncovered_at_any_depth([".env"], "\n".join(root_only))
    assert ".env" not in uncovered
    assert {"backend/.env", "frontend/.env", "backend/app/core/.env"} <= set(uncovered)


def test_dockerignore_excludes_no_tracked_build_input() -> None:
    # Glob largo demais tira fonte versionada do contexto calado: sem
    # `config/schemas/*.json` o build passa e a validação de artefato desliga.
    excluded = _excluded_tracked_files(_DOCKERIGNORE.read_text(encoding="utf-8"))
    assert [p for p in excluded if not _is_excluded_on_purpose(p)] == []


def test_every_on_purpose_exclusion_matches_a_tracked_file() -> None:
    # Exceção que não casa nada é allowlist morta: o teste acima passaria vazio.
    excluded = _excluded_tracked_files(_DOCKERIGNORE.read_text(encoding="utf-8"))
    for prefix in _EXCLUDED_ON_PURPOSE:
        assert any(p.startswith(prefix) for p in excluded), f"{prefix} não exclui nada"
    assert any(_ENV_TEMPLATE.fullmatch(posixpath.basename(p)) for p in excluded)


def test_dockerignore_negative_control_detects_over_broad_glob() -> None:
    text = _DOCKERIGNORE.read_text(encoding="utf-8") + "\n**/*.json\n"
    lost = [p for p in _excluded_tracked_files(text) if not _is_excluded_on_purpose(p)]
    assert "config/schemas/e5_analysis.schema.json" in lost
