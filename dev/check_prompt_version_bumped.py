#!/usr/bin/env python3
"""W2-T05 · ADR-233 — gate: exige bump de PROMPT_VERSION quando prompt LLM muda."""

# Como funciona — heurística intencionalmente simples (sem AST quebradiço):
#   - Para cada arquivo monitorado com PROMPT_VERSION, compara com origin/main:<path>.
#   - Arquivo novo / idêntico / bumpado → OK. Conteúdo diferente sem bump → falha.
#   - Valida formato canônico: regex CANONICAL_VERSION_RE (semver puro OU
#     <slug>-v<semver> legado).
# False positive aceito (refactor whitespace força bump) — preferível a false
# negative (mudança real sem bump invalida cache LLM em produção).
# Bypass de emergência: MATHOMS_SKIP_PROMPT_VERSION_CHECK=1.
# Uso: pre-commit via pass_filenames; CI smoke roda sem argv (varre tudo).

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

PROMPT_DIRS = (Path("pipeline/llm/prompts"), Path("pipeline/llm/schemas"))

# Captura ``PROMPT_VERSION = "X"`` (single ou double quote) no início da linha.
PROMPT_VERSION_RE = re.compile(
    r'^\s*PROMPT_VERSION\s*=\s*["\']([^"\']+)["\']',
    re.MULTILINE,
)

# Formato canônico (ADR-233): semver puro OU prefix-v<semver> legado.
CANONICAL_VERSION_RE = re.compile(r"^(\d+\.\d+\.\d+|[\w-]+-v\d+\.\d+\.\d+)$")

UPSTREAM_REF = os.environ.get("MATHOMS_PROMPT_VERSION_BASE", "origin/main")


def _run_git(args: list[str]) -> tuple[int, str]:
    """Roda git, retorna (returncode, stdout). stderr suprimido."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout


def _extract_version(content: str) -> str | None:
    """Devolve o valor da primeira ocorrência de PROMPT_VERSION, ou None."""
    m = PROMPT_VERSION_RE.search(content)
    return m.group(1) if m else None


def _read_local(path: Path) -> str | None:
    """Lê arquivo do working tree. None se não existir."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _read_upstream(path: Path) -> str | None:
    """Lê ``{UPSTREAM_REF}:<path>``. None se arquivo é novo ou ref ausente."""
    rc, out = _run_git(["show", f"{UPSTREAM_REF}:{path.as_posix()}"])
    if rc != 0:
        return None
    return out


def _is_prompt_module(path: Path) -> bool:
    """True se ``path`` declara ``PROMPT_VERSION = "..."`` no nível do módulo."""
    content = _read_local(path)
    return bool(content and PROMPT_VERSION_RE.search(content))


def _discover_prompts() -> list[Path]:
    """Auto-detect: todos os .py em PROMPT_DIRS que declaram PROMPT_VERSION."""
    found: list[Path] = []
    for d in PROMPT_DIRS:
        if not d.exists():
            continue
        found.extend(f for f in sorted(d.glob("*.py")) if _is_prompt_module(f))
    return found


def _check_format(path: Path, version: str) -> str | None:
    """Devolve mensagem de erro se formato inválido, None se OK."""
    if CANONICAL_VERSION_RE.match(version):
        return None
    return (
        f"{path}: PROMPT_VERSION={version!r} não casa com formato canônico "
        f"(ADR-233). Use semver puro 'X.Y.Z' (ex.: '1.0.0', '2.1.3') ou "
        f"o prefix legado '<slug>-v<semver>' (ex.: 'e16-v1.1.0')."
    )


def _check_bump(path: Path, local_content: str) -> str | None:
    """Devolve mensagem de erro se conteúdo mudou mas PROMPT_VERSION não."""
    upstream_content = _read_upstream(path)
    if upstream_content is None or upstream_content == local_content:
        return None
    local_version = _extract_version(local_content)
    upstream_version = _extract_version(upstream_content)
    if local_version is None:
        return (
            f"{path}: arquivo modificado e tem PROMPT_VERSION em "
            f"{UPSTREAM_REF}, mas constante foi removida — restaure-a."
        )
    if upstream_version is None or local_version != upstream_version:
        return None
    return (
        f"{path}: conteúdo mudou mas PROMPT_VERSION continua "
        f"{local_version!r}. Bump (ex.: '{local_version}' → "
        f"'{_suggest_bump(local_version)}') para invalidar cache LLM "
        f"(W2-T05, ADR-233)."
    )


def _suggest_bump(current: str) -> str:
    """Sugere próximo patch — ajuda mensagem de erro, não validação."""
    m = re.match(r"^(.*?)(\d+)\.(\d+)\.(\d+)$", current)
    if not m:
        return f"{current}+1"
    prefix, major, minor, patch = m.groups()
    return f"{prefix}{major}.{minor}.{int(patch) + 1}"


def _filter_to_prompt_files(argv: list[str]) -> list[Path]:
    """Filtra argv para apenas arquivos em PROMPT_DIRS com PROMPT_VERSION."""
    out: list[Path] = []
    for raw in argv:
        p = Path(raw)
        if not any(p.is_relative_to(d) for d in PROMPT_DIRS):
            continue
        content = _read_local(p)
        if not content or not PROMPT_VERSION_RE.search(content):
            continue
        out.append(p)
    return out


def _errors_for(path: Path) -> list[str]:
    """Coleta erros de formato + bump para um único arquivo."""
    content = _read_local(path)
    if content is None:
        return []
    version = _extract_version(content)
    if version is None:
        return []
    fmt_err = _check_format(path, version)
    if fmt_err:
        return [fmt_err]
    bump_err = _check_bump(path, content)
    return [bump_err] if bump_err else []


def main(argv: list[str]) -> int:
    if os.environ.get("MATHOMS_SKIP_PROMPT_VERSION_CHECK"):
        return 0
    files = _filter_to_prompt_files(argv) if argv else _discover_prompts()
    errors = [e for f in files for e in _errors_for(f)]
    if not errors:
        return 0
    print("ERRO: gate PROMPT_VERSION (W2-T05 · ADR-233) — falhou:", file=sys.stderr)
    for e in errors:
        print(f"  • {e}", file=sys.stderr)
    print(
        "\nVer docs/adr/233-prompt-version-format.md para o formato canônico.\n"
        "Bypass (raro): MATHOMS_SKIP_PROMPT_VERSION_CHECK=1.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
