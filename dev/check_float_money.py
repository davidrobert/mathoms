#!/usr/bin/env python3
"""A6g.6 slice 3 · ADR-114 — bloqueia `: float` em campo monetário (ADR-090).

Regra: dinheiro nunca é float. Use Money.brl(...)/Decimal em Python;
int64 cents em Go; string decimal no wire.

Detecção: linhas ADICIONADAS em `git diff --cached` que declaram um
campo com nome contendo amount|valor|brl|saldo|money|total|price|cost
e anotação `: float`. Legado (79 ofensores em A6g.1) fica fora — só
blocamos código NOVO.

Skip explícito: docstring/comentário inline dizendo "percentage", "rate",
"tolerance" ou "tolerância" desqualifica (não é money, é razão/threshold).

Chamado via pre-commit `pass_filenames: true`; exit 0 se não há staged
ou nenhum viola. Exit 1 mostrando arquivo + linha ofensora.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# ADR-283 — full-scan de colunas SQLAlchemy ``Float`` em models/.
# Detecção ESTRUTURAL (mapped_column(Float)/Column(Float)), não regex de nome:
# o vetor de drift irreversível é a coluna persistida, não o nome do campo.
# Allowlist NOMINAL ``(path_rel, coluna) -> motivo`` — Float legítimo (não-money)
# ou legado com drop rastreado. Heurística de nome erra; allowlist explícita não.
MODELS_FLOAT_ALLOWLIST: dict[tuple[str, str], str] = {
    ("backend/app/models/report.py", "score"): "índice 0–100, não monetário",
    ("backend/app/models/llm_config.py", "temperature"): "parâmetro LLM, não monetário",
    (
        "backend/app/models/document.py",
        "classification_confidence",
    ): "confidence 0–1, não monetário",
    (
        "backend/app/models/llm_call_log.py",
        "confidence",
    ): "confidence 0–1 do output LLM (ADR-260 · A20.l12), não monetário",
}
# ``<nome>: Mapped[...] = mapped_column(`` ou ``<nome> = mapped_column(`` / ``Column(``.
_MODEL_COLUMN = re.compile(
    r"^\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*(?::\s*Mapped\[[^=]*\])?\s*=\s*"
    r"(?:mapped_column|sa\.Column|Column)\("
)
_FLOAT_TYPE = re.compile(r"\b(?:sa\.)?Float\b")

# Tokens monetários — case-insensitive match no nome do campo.
MONEY_TOKENS = re.compile(
    r"(amount|valor|brl|saldo|money|total|price|cost|despesa|receita|"
    r"aporte|patrimonio|capital|dinheiro|preco)",
    re.IGNORECASE,
)
# Campo tipado com float puro (não list[float]/tuple[float,...]).
FIELD_FLOAT = re.compile(r"^\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*:\s*float\b(?!\s*\|)")
# Exceções (tolerâncias, taxas, percentuais) — skip se linha contém esses tokens.
SKIP_TOKENS = re.compile(
    r"(percentage|percentual|rate|taxa|tolerance|tolera|threshold|limite|" r"ratio|fator|factor)",
    re.IGNORECASE,
)


def _is_rename(file_path: str) -> bool:
    """True se o arquivo foi renomeado (status R) — git vê todas as linhas
    como 'adicionadas' e o hook pega false positive em campos legados.
    """
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-status", "--find-renames=90%"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return False
    for line in out.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3 and parts[2] == file_path:
            return True
    return False


def get_added_lines_for(file_path: str) -> list[tuple[int, str]]:
    """Return [(line_no_new, content)] for lines ADDED in staged diff."""
    if _is_rename(file_path):
        return []
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "-U0", "--", file_path],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return []
    added: list[tuple[int, str]] = []
    new_ln = 0
    hunk_header = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    for line in out.splitlines():
        m = hunk_header.match(line)
        if m:
            new_ln = int(m.group(1))
            continue
        if line.startswith("+++"):
            continue
        if line.startswith("+"):
            added.append((new_ln, line[1:]))
            new_ln += 1
        elif not line.startswith("-"):
            new_ln += 1
    return added


def check_file(file_path: str) -> list[tuple[int, str, str]]:
    """Return [(line_no, field_name, content)] of money-float offenders in staged diff."""
    offenders: list[tuple[int, str, str]] = []
    for line_no, content in get_added_lines_for(file_path):
        if SKIP_TOKENS.search(content):
            continue
        m = FIELD_FLOAT.match(content)
        if not m:
            continue
        field_name = m.group(1)
        if MONEY_TOKENS.search(field_name):
            offenders.append((line_no, field_name, content.rstrip()))
    return offenders


def _repo_rel(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def _float_column_on_line(line: str) -> str | None:
    """Nome da coluna se a linha declara um SQLAlchemy ``Float``, senão ``None``."""
    if not _FLOAT_TYPE.search(line):
        return None
    m = _MODEL_COLUMN.match(line)
    return m.group(1) if m else None


def _model_float_offenders(py: Path) -> list[tuple[str, int, str]]:
    rel = _repo_rel(py)
    out: list[tuple[str, int, str]] = []
    for line_no, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
        column = _float_column_on_line(line)
        if column and (rel, column) not in MODELS_FLOAT_ALLOWLIST:
            out.append((rel, line_no, column))
    return out


def scan_models_float_columns(models_dir: str) -> list[tuple[str, int, str]]:
    """Return [(path_rel, line_no, column)] de colunas Float fora da allowlist."""
    offenders: list[tuple[str, int, str]] = []
    for py in sorted(Path(models_dir).rglob("*.py")):
        offenders.extend(_model_float_offenders(py))
    return offenders


def _run_models_scan(models_dir: str) -> int:
    offenders = scan_models_float_columns(models_dir)
    if not offenders:
        return 0
    print(
        "ERRO: coluna SQLAlchemy `Float` monetária em models — violação do ADR-090:",
        file=sys.stderr,
    )
    for rel, line_no, column in offenders:
        print(f"  {rel}:{line_no} — {column}", file=sys.stderr)
    print(
        "\nADR-090: dinheiro nunca é float. Use `Numeric(18, 2)` na coluna.\n"
        "Se a coluna NÃO é monetária (índice/ratio/parâmetro) ou é legado com\n"
        "drop rastreado, adicione (path, coluna) a MODELS_FLOAT_ALLOWLIST com motivo.",
        file=sys.stderr,
    )
    return 1


def _collect_diff_offenders(argv: list[str]) -> list[tuple[str, int, str, str]]:
    out: list[tuple[str, int, str, str]] = []
    for arg in argv:
        if Path(arg).suffix != ".py":
            continue
        for line_no, name, content in check_file(arg):
            out.append((arg, line_no, name, content))
    return out


def _report_diff_offenders(offenders: list[tuple[str, int, str, str]]) -> int:
    if not offenders:
        return 0
    print("ERRO: `: float` em campo monetário — violação do ADR-090:", file=sys.stderr)
    for file_path, line_no, name, content in offenders:
        print(f"  {file_path}:{line_no} — {name}", file=sys.stderr)
        print(f"    {content.strip()}", file=sys.stderr)
    print(
        "\nRegra ADR-090: dinheiro nunca é float.\n"
        "  Python:  use Money.brl(...)  ou  Decimal(str(v))\n"
        "  Wire:    string decimal\n"
        "  Go:      int64 cents\n"
        "Se for tolerância/taxa/razão (não money), renomeie ou adicione\n"
        "comentário com 'rate|percentage|tolerance' na mesma linha.",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--scan-models":
        models_dir = argv[1] if len(argv) > 1 else "backend/app/models"
        return _run_models_scan(models_dir)
    return _report_diff_offenders(_collect_diff_offenders(argv))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
