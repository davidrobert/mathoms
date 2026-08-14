#!/usr/bin/env python3
"""Sprint grande tem de separar histórico: `_README` > teto exige `_HISTORY.md`."""
# Por que NÃO é um teto puro de linhas: o conteúdo que governa decisão numa
# sprint grande custa o que custa. Medido na A40 em 2026-08-14, só as seções
# vivas (tabela de lanes, gate de saída, predicado de status, fora-do-sprint)
# somam ~530 linhas. Um teto de 500 reprovaria uma sprint bem organizada e
# seria contornado inflando `_HISTORY` — Goodhart imediato.
#
# O que este gate mede é a PATOLOGIA: `_README` grande SEM histórico separado.
# Isso é sempre o mesmo defeito — snapshot datado, pendência resolvida e painel
# encerrado acumulando no arquivo que todo mundo lê para decidir o que fazer.
#
# Calibração (medida em 37 sprints, 2026-08-14): mediana 137 linhas, p90 315,
# maior sprint sem patologia 423. O teto de 800 dá folga de 2,5x sobre o p90 e
# teria disparado na A40 em 2026-08-05, quando ela saltou de 251 para 888
# linhas em dois dias — 9 dias antes de alguém notar, e só notou porque o custo
# de token de uma sessão ficou alto.
#
# S2 é advisory de propósito: contar bloco datado é heurística de regex, e
# heurística que bloqueia commit vira `# noqa` na primeira falsa acusação.

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPRINT_DIR = REPO_ROOT / "docs" / "sprint"

MAX_README_LINES_WITHOUT_HISTORY = 800

# Marcadores de registro fechado — a prosa que o próprio repo usa quando um
# bloco vira evidência datada em vez de instrução. Levantados da A40 viva.
HISTORICAL_MARKERS = (
    "não o reescreva",
    "não os reescreva",
    "não a reescreva",
    "fica como registro",
    "é medição datada",
    "o diagnóstico abaixo fica como registro",
)
DATED_SNAPSHOT_RE = re.compile(r"^>?\s*\*{0,2}(Estado|Delta|Liberação)\b.*\b20\d\d-\d\d-\d\d", re.M)
ADVISORY_SNAPSHOT_LIMIT = 12


def _readme_line_count(readme: Path) -> int:
    return len(readme.read_text(encoding="utf-8").splitlines())


def count_historical_blocks(text: str) -> int:
    """Blocos que se declaram registro fechado — marcador textual ou snapshot datado."""
    lowered = text.lower()
    marker_hits = sum(lowered.count(marker) for marker in HISTORICAL_MARKERS)
    return marker_hits + len(DATED_SNAPSHOT_RE.findall(text))


def _sprint_readmes(sprint_dir: Path) -> list[Path]:
    return sorted(sprint_dir.glob("*/_README.md"))


def _violation_for(readme: Path) -> str | None:
    """S1: README acima do teto sem `_HISTORY.md` irmão. Hard-fail."""
    lines = _readme_line_count(readme)
    if lines <= MAX_README_LINES_WITHOUT_HISTORY:
        return None
    if (readme.parent / "_HISTORY.md").is_file():
        return None
    sprint = readme.parent.name
    return (
        f"docs/sprint/{sprint}/_README.md: {lines} linhas (teto "
        f"{MAX_README_LINES_WITHOUT_HISTORY}) e não existe `_HISTORY.md`. "
        f"Separe o registro fechado: python3 dev/split_sprint_history.py "
        f"--sprint {sprint} --dry-run"
    )


def _advisory_for(readme: Path) -> str | None:
    """S2: muitos blocos datados ainda no README. Só avisa."""
    blocks = count_historical_blocks(readme.read_text(encoding="utf-8"))
    if blocks <= ADVISORY_SNAPSHOT_LIMIT:
        return None
    sprint = readme.parent.name
    return (
        f"docs/sprint/{sprint}/_README.md: {blocks} blocos se declaram registro "
        f"fechado — candidatos a `_HISTORY.md`."
    )


def scan(sprint_dir: Path = SPRINT_DIR) -> tuple[list[str], list[str]]:
    """(violações hard, avisos) sobre todas as sprints do vault."""
    violations: list[str] = []
    advisories: list[str] = []
    for readme in _sprint_readmes(sprint_dir):
        violation = _violation_for(readme)
        if violation:
            violations.append(violation)
        advisory = _advisory_for(readme)
        if advisory:
            advisories.append(advisory)
    return violations, advisories


def main() -> int:
    violations, advisories = scan()
    for advisory in advisories:
        print(f"  aviso: {advisory}", file=sys.stderr)
    if not violations:
        return 0
    print("\n`_README` de sprint grande sem histórico separado:\n", file=sys.stderr)
    for violation in violations:
        print(f"  - {violation}", file=sys.stderr)
    print(
        "\nO custo é real: o `_README` da A40 chegou a ~40k tokens, e toda\n"
        "pergunta sobre a sprint pagava o arquivo inteiro. Separar preserva o\n"
        "histórico — `_HISTORY.md` não se apaga nem se reescreve.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
