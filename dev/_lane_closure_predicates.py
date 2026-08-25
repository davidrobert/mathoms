"""Predicados estruturais de fechamento de lane, compartilhados por dois consumidores."""
# A skill `lane-closeout` (`check_closure.py`) os aplica DEPOIS do merge, partindo de
# um PR; o gate `check_lane_transition.py` os aplica ANTES do commit, partindo do diff
# staged. Só os PREDICADOS são comuns — a resolução não é: no sentido pre-commit não
# existe PR de onde resolver (A40.l59 §Ataque §7).

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# `shipped`/`cancelled` — os únicos estados que declaram a lane encerrada.
TERMINAL_STATUS: frozenset[str] = frozenset({"shipped", "cancelled"})

# Primeira célula de linha de tabela: `| [[A40.l7]] | …`. A §Lanes é a tabela cuja
# 1ª coluna carrega o id — não basta o id aparecer no `_README` (A40.l59 §Ataque §6:
# a A40.l77 era citada numa tabela de ROTEAMENTO e seguia fora da §Lanes).
_TABLE_ID_RE = re.compile(r"^\|\s*(?:\*\*)?\[\[([A-Za-z0-9.\-]+)\]\]")

_FRONTMATTER_END = "\n---\n"


def frontmatter(text: str) -> dict[str, Any]:
    """Frontmatter YAML de uma nota; `{}` quando ausente ou inválido."""
    if not text.startswith("---\n"):
        return {}
    end = text.find(_FRONTMATTER_END, 4)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return {}


def sprint_record(docs_root: Path, sprint: str) -> str:
    # Exigir só o `_README` puniria o `split_sprint_history.py`, que o CLAUDE.md manda
    # rodar: 24 PRs da A40 vivem apenas no `_HISTORY` (A40.l59 §Ataque §3).
    """`_README` ∪ `_HISTORY` da sprint — o registro é os DOIS arquivos."""
    folder = docs_root / "sprint" / sprint
    parts = [
        (folder / name).read_text(encoding="utf-8")
        for name in ("_README.md", "_HISTORY.md")
        if (folder / name).exists()
    ]
    return "\n".join(parts)


def pr_is_cited(docs_root: Path, sprint: str, pr: int) -> bool:
    """`#<pr>` aparece no registro da sprint."""
    return re.search(rf"#{pr}\b", sprint_record(docs_root, sprint)) is not None


def lane_ids_with_table_row(docs_root: Path, sprint: str) -> set[str]:
    """Ids que têm LINHA em alguma tabela do `_README` (1ª célula)."""
    readme = docs_root / "sprint" / sprint / "_README.md"
    if not readme.exists():
        return set()
    found = (_TABLE_ID_RE.match(line) for line in readme.read_text(encoding="utf-8").splitlines())
    return {match.group(1) for match in found if match}


def merged_pr_numbers(limit: int = 4000) -> set[int]:
    # Casa o SUFIXO do assunto, nunca a mensagem inteira: PR que cita `#1265` no corpo
    # sequestrava a resolução (mesma armadilha documentada em `check_closure._merge_sha`).
    """PRs cujo squash-merge está em `origin/main`, lidos do git — sem rede."""
    done = subprocess.run(
        ["git", "log", "--format=%s", f"--max-count={limit}", "origin/main"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        return set()
    matches = (re.search(r"\(#(\d+)\)$", line) for line in done.stdout.splitlines())
    return {int(match.group(1)) for match in matches if match}


def is_terminal(front: dict[str, Any]) -> bool:
    return str(front.get("status", "")) in TERMINAL_STATUS
