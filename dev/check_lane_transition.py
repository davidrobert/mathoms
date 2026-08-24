#!/usr/bin/env python3
"""Gate na TRANSIÇÃO de lane: o registro entra junto com o estado, não depois.

Classe medida (A40.l59): entre 2026-06 e 2026-08, ~2,5 PRs por semana em `main`
existiram só para corrigir doc de lane já entregue, porque a pergunta foi feita
DEPOIS do merge. Reproduzido contra a história da A40: **23 de 42** transições
para `shipped` seriam barradas — 13 sem `ship_pr` no commit do flip e 10 com o PR
não citado no registro da sprint (§Ataque §2).

Três checagens, duas sobre o diff staged e uma sobre o estado:

  T1 flip     — diff que vira `status:` para `shipped` exige `ship_pr` + `ship_date`
                no mesmo commit, E o PR citado no registro da sprint.
  T2 criação  — arquivo de lane NOVO exige linha na tabela do `_README`.
  C1 coerência— lane NÃO-terminal que declara `ship_pr` de PR já mergeado em
                `origin/main`. Não olha diff: olha estado. É o par do T1 —
                transição AUSENTE não produz diff nenhum (§Ataque §1).

LIMITE DECLARADO. O caso-bandeira da lane (l7/#1375) NÃO é alcançado por nenhuma
das três: no instante do defeito a lane não tinha `ship_pr` nem flip, e o único
vínculo entre o PR e a lane era o id no assunto do commit — sinal com 38/42 de
recall, mas que dispara falso em commit que apenas MENCIONA a lane (o #1643 diz
"abre a l77"). Fechar essa metade exige cruzar branch↔PR pela API, e gate
obrigatório que depende de rede pisca: `check_scheduled_workflows` travou o repo
em 2026-08-24 lendo réplica obsoleta com HTTP 200. Deferido com dono e condição no
§Deferimento da lane.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

try:  # script direto vs. import como `dev.*` (padrão de dev/build_doc_index.py)
    from _lane_closure_predicates import (  # noqa: E402
        frontmatter,
        is_terminal,
        lane_ids_with_table_row,
        merged_pr_numbers,
        pr_is_cited,
    )
except ModuleNotFoundError:  # pragma: no cover
    from dev._lane_closure_predicates import (  # noqa: E402
        frontmatter,
        is_terminal,
        lane_ids_with_table_row,
        merged_pr_numbers,
        pr_is_cited,
    )

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"

LANE_GLOB = "sprint/*/lanes/*.md"

_SEQUENCIA_SELF_CLOSING = (
    "Se o PR que fecha a lane é o PRÓPRIO PR do flip (6 das 42 transições da A40),\n"
    "  o número não existe no 1º commit — ele sai do `gh pr create`. A ordem é:\n"
    "  commite o trabalho → abra o PR → commite o flip com `ship_pr` → push."
)


def _git(args: list[str]) -> str:
    done = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    return done.stdout if done.returncode == 0 else ""


def staged_lane_changes() -> list[tuple[str, str]]:
    """`(status, path)` dos arquivos de lane staged — `A` novo, `M` modificado."""
    rows = _git(["diff", "--cached", "--name-status", "--find-renames=90%"]).splitlines()
    out: list[tuple[str, str]] = []
    for row in rows:
        parts = row.split("\t")
        if len(parts) < 2:
            continue
        path = parts[-1]
        if path.startswith("docs/sprint/") and "/lanes/" in path and path.endswith(".md"):
            out.append((parts[0][:1], path))
    return out


def _blob(ref: str, path: str) -> str:
    """Conteúdo do blob; `ref` vazio é o índice (staged)."""
    return _git(["show", f"{ref}:{path}"])


def _read(path: str) -> str:
    target = REPO_ROOT / path
    return target.read_text(encoding="utf-8") if target.exists() else ""


def _display_path(path: Path) -> str:
    # `relative_to` levanta fora do repo (mesma ressalva de check_lane_status_predicate).
    """Relativo ao repo quando aplicável; absoluto em vault sintética de teste."""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _sprint_of(front: dict[str, Any], path: str) -> str:
    return str(front.get("sprint") or Path(path).parts[2])


def check_flip(path: str, before: str, after_text: str, docs_root: Path) -> list[str]:
    # Recebe os DOIS lados como texto: o encanamento git fica em `find_violations`,
    # para que o predicado seja exercitável por fixture sem índice git.
    """T1 — o commit que vira a lane para `shipped` carrega o registro junto."""
    after = frontmatter(after_text)
    if str(after.get("status")) != "shipped":
        return []
    if str(frontmatter(before).get("status")) == "shipped":
        return []  # já era `shipped` — não é transição
    lane_id = str(after.get("id", path))
    missing = [key for key in ("ship_pr", "ship_date") if not after.get(key)]
    if missing:
        return [
            f"{path}: {lane_id} vira `shipped` sem {' e '.join(f'`{m}`' for m in missing)} "
            f"no mesmo commit.\n  {_SEQUENCIA_SELF_CLOSING}"
        ]
    pr = int(after["ship_pr"])
    sprint = _sprint_of(after, path)
    if pr_is_cited(docs_root, sprint, pr):
        return []
    return [
        f"{path}: {lane_id} vira `shipped` com `ship_pr: {pr}`, mas #{pr} não aparece "
        f"no registro da sprint {sprint} (`_README.md` ∪ `_HISTORY.md`). "
        f"Registre a entrega no mesmo commit."
    ]


def check_creation(path: str, after_text: str, docs_root: Path) -> list[str]:
    """T2 — lane nova nasce com linha na tabela do `_README`."""
    front = frontmatter(after_text)
    lane_id = str(front.get("id") or "")
    if not lane_id:
        return []
    sprint = _sprint_of(front, path)
    if lane_id in lane_ids_with_table_row(docs_root, sprint):
        return []
    return [
        f"{path}: {lane_id} é lane nova e não tem linha na tabela do "
        f"`docs/sprint/{sprint}/_README.md`. Lane fora da tabela é invisível ao "
        f"encerramento administrativo da sprint."
    ]


def check_coherence(docs_root: Path, merged: set[int]) -> list[str]:
    """C1 — lane não-terminal cujo `ship_pr` já está mergeado em `origin/main`."""
    problems: list[str] = []
    for path in sorted(docs_root.glob(LANE_GLOB)):
        front = frontmatter(path.read_text(encoding="utf-8"))
        pr = front.get("ship_pr")
        if front.get("type") != "lane" or not pr or is_terminal(front):
            continue
        if int(pr) not in merged:
            continue
        problems.append(
            f"{_display_path(path)}: {front.get('id')} está "
            f"`{front.get('status')}` e declara `ship_pr: {pr}`, que já está mergeado "
            f"em `origin/main`. Estado e entrega discordam."
        )
    return problems


def find_violations(docs_root: Path = DOCS) -> list[str]:
    """As três checagens; `[]` quando o commit está coerente."""
    problems: list[str] = []
    for change, path in staged_lane_changes():
        after_text = _blob("", path) or _read(path)
        if change == "A":
            problems += check_creation(path, after_text, docs_root)
        else:
            problems += check_flip(path, _blob("HEAD", path), after_text, docs_root)
    return problems + check_coherence(docs_root, merged_pr_numbers())


def main() -> int:
    violations = find_violations()
    if not violations:
        return 0
    print("Transição de lane sem o registro que ela exige:\n", file=sys.stderr)
    for violation in violations:
        print(f"  - {violation}", file=sys.stderr)
    print(
        "\nO gate roda na TRANSIÇÃO, não no PR: lane que vira 2 PRs daria verde falso.\n"
        "Corrija a causa — `--no-verify` é proibido pelo CLAUDE.md.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
