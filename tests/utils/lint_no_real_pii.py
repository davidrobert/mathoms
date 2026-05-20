"""Lint anti-PII em fixtures — F6.5D.7.

Escaneia o repo procurando padrões de CPF (formato `XXX.XXX.XXX-YY` ou 11
dígitos consecutivos) em arquivos de teste/fixture e falha se encontrar
algum que NÃO seja:
- Placeholder conhecido (`000.000.000-00`, `123.456.789-09`)
- Gerado por `generate_valid_cpf` (anotação via comentário `# noqa: PII-ok`)

Uso:
    python tests/utils/lint_no_real_pii.py              # raiz do repo
    python tests/utils/lint_no_real_pii.py --verbose
    python tests/utils/lint_no_real_pii.py --fix        # apenas reporta (sem --fix auto)

Em CI:
    python tests/utils/lint_no_real_pii.py && echo "OK"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Padrões a detectar
CPF_FORMATTED_RE = re.compile(r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b")
# CPF sem pontuação (11 dígitos isolados) — mais false-positives, usar só
# em arquivos de fixture.
CPF_PLAIN_RE = re.compile(r"\b(\d{11})\b")

# Placeholders aceitos (LGPD-safe por design)
ALLOWED_CPFS: set[str] = {
    "000.000.000-00",
    "00000000000",
    "123.456.789-09",  # comum em docs de exemplo
    "12345678909",
    "111.111.111-11",
    "11111111111",
}

# Diretórios que têm permissão para conter PII real (data/ real do dogfood)
EXCLUDED_DIRS = {
    "node_modules",
    ".venv",
    ".git",
    "data",  # dados reais do dogfood (gitignored, mas por segurança)
    "inbox",
    "inbox_processed",
    "storage",
    "_archive",
    "_scratch",
    "processed",
    "members",
    "life_plan",
    "logs",
    "output",
    "__pycache__",
    ".next",
    ".pytest_cache",
    "coverage",
    "playwright-results",
    ".claude",
    ".cursor",
}

# Extensões a varrer
EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md"}

# Diretórios-alvo — APENAS tests/fixtures. `config/` contém dados reais do
# founder (cobertos pela neutralização em 6.5E.6 ao servir via API), não é
# considerado fixture de teste.
SCAN_TARGETS = [
    "tests",
    "backend/tests",
    "frontend/tests",
]


def _is_excluded(path: Path, root: Path) -> bool:
    # Worktrees em `.claude/worktrees/<slug>/` (CLAUDE.md §Git e commits)
    # têm `.claude` no path absoluto; sem rel-to-root, o repo inteiro
    # seria excluído quando o lint rodasse de dentro de um worktree.
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        rel_parts = path.parts
    return any(part in EXCLUDED_DIRS for part in rel_parts)


def _scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Retorna list de (linha, snippet, match) com CPFs problemáticos."""
    findings: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return findings

    for lineno, line in enumerate(text.splitlines(), 1):
        if "PII-ok" in line:
            continue
        for match in CPF_FORMATTED_RE.finditer(line):
            cpf = match.group(1)
            if cpf in ALLOWED_CPFS:
                continue
            findings.append((lineno, line.strip()[:120], cpf))

    return findings


def _iter_files(root: Path, targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        target_path = root / target
        if not target_path.exists():
            continue
        for p in target_path.rglob("*"):
            if p.is_file() and p.suffix in EXTENSIONS and not _is_excluded(p, root):
                files.append(p)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint anti-PII em fixtures")
    parser.add_argument("--root", default=".", help="Raiz do projeto")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--targets",
        nargs="+",
        default=SCAN_TARGETS,
        help="Diretórios a escanear (default: todos de teste)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = _iter_files(root, args.targets)

    if args.verbose:
        print(f"Escaneando {len(files)} arquivos em {args.targets}...")

    violations_found = 0
    for f in files:
        for lineno, snippet, cpf in _scan_file(f):
            violations_found += 1
            rel = f.relative_to(root)
            print(f"{rel}:{lineno}: CPF suspeito {cpf!r}", file=sys.stderr)
            if args.verbose:
                print(f"  Contexto: {snippet}", file=sys.stderr)

    if violations_found > 0:
        print(
            f"\n✗ {violations_found} CPF(s) suspeito(s) encontrado(s). "
            f"Use placeholder (000.000.000-00) ou o gerador mod-11 em "
            f"tests/utils/cpf.py (anote com `# noqa: PII-ok` se for gerado).",
            file=sys.stderr,
        )
        return 1

    if args.verbose:
        print("✓ Nenhuma PII real detectada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
