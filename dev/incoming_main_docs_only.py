#!/usr/bin/env python3
"""Skip-class de jobs pesados quando o `update-branch` do trem só trouxe doc (ADR-322).

O invariante, e não uma heurística de frescor: pular é seguro sse (a) o merge não
alterou nada fora do conjunto de doc inerte — logo a árvore de código do head da
branch é idêntica à do SHA anterior — e (b) aquele SHA anterior fechou
`All checks green: success`. (b) encadeia por indução até o SHA em que os jobs
pesados rodaram de fato, então não há cadeia a capar nem janela a expirar.

Fail-closed em tudo: qualquer predicado indeterminado devolve `false` (roda a
suíte). Falha de I/O nunca CONCEDE skip — é isso, e não "zero API", que a versão
anterior perdia ao inferir frescor do Nightly.

A âncora é `HEAD^2`, não `HEAD`: sob evento `pull_request` o checkout é o
merge-ref sintético, onde `HEAD^1` é a base e `HEAD^2` é o head do PR — que num
repo squash-only NUNCA é ancestral de main. Predicado ancorado em `HEAD` é
constante `false`, que foi como a versão anterior nasceu inerte sem ninguém ver.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# `docs/**` NÃO é uniformemente inerte: estes paths são INPUT de gate, lidos do
# disco por teste que vive em job skipável. Cada linha nomeia o consumidor —
# sem isso a lista apodrece e vira fail-open silencioso no caminho de merge.
DOCS_GATE_INPUTS = (
    "docs/reference/api/",  # backend/tests/test_openapi_snapshot.py
    "docs/reference/DB_SCHEMA_REFERENCE.md",  # backend/tests/test_db_schema_reference_snapshot.py
)
# `docs/adr/**` NÃO entra aqui de propósito: é a maior parte do churn de doc, e
# excetuá-lo comeria quase todo o ganho. Ele é coberto mantendo `pipeline-tests`
# FORA do skip set (`dev/check_lineage_refs.py` roda lá).
REQUIRED_AGGREGATE = "All checks green"


def is_inert_doc_path(path: str) -> bool:
    """True se o path é vault/markdown que nenhum job skipável lê."""
    normalized = path.replace("\\", "/").lstrip("./")
    if not normalized or normalized.endswith("/"):
        return False
    if any(normalized.startswith(prefix) for prefix in DOCS_GATE_INPUTS):
        return False
    if normalized.startswith("docs/"):
        return True
    return "/" not in normalized and normalized.endswith(".md")


def paths_are_inert_docs(paths: Sequence[str]) -> bool:
    """False se a lista é vazia (não sei o que mudou) ou tem qualquer não-doc."""
    if not paths:
        return False
    return all(is_inert_doc_path(p) for p in paths)


def should_skip(
    *,
    head_matches_event: bool,
    branch_parents: Sequence[str],
    merged_commit_on_base: bool,
    incoming_paths: Sequence[str],
    previous_run_green: bool,
) -> tuple[bool, str]:
    """(skip?, predicado que bloqueou). O motivo alimenta o step summary — sem
    ele "por que a suíte rodou" é irrespondível post-hoc."""
    for satisfeito, motivo in (
        (head_matches_event, "merge-ref obsoleto: HEAD^2 != pull_request.head.sha"),
        (len(branch_parents) == 2, f"head da branch tem {len(branch_parents)} parents, esperado 2"),
        (merged_commit_on_base, "2º parent do head da branch não está na base"),
        (paths_are_inert_docs(incoming_paths), "delta do merge não é 100% doc inerte"),
        (previous_run_green, f"SHA anterior não fechou `{REQUIRED_AGGREGATE}: success`"),
    ):
        if not satisfeito:
            return False, motivo
    return True, ""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)


def _rev(repo: Path, spec: str) -> str:
    proc = _git(repo, "rev-parse", "--verify", "--quiet", spec)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _parents(repo: Path, spec: str) -> tuple[str, ...]:
    proc = _git(repo, "rev-list", "--parents", "-n", "1", spec)
    if proc.returncode != 0 or not proc.stdout.strip():
        return ()
    return tuple(proc.stdout.split()[1:])


def _is_ancestor(repo: Path, older: str, newer: str) -> bool:
    if not older or not newer:
        return False
    return _git(repo, "merge-base", "--is-ancestor", older, newer).returncode == 0


def _incoming_paths(repo: Path, before: str, after: str) -> tuple[str, ...]:
    """O que o merge trouxe para a branch — `before` é o tip anterior dela."""
    proc = _git(repo, "diff", "--name-only", "-z", before, after)
    if proc.returncode != 0 or not proc.stdout:
        return ()
    return tuple(p for p in proc.stdout.split("\0") if p)


def aggregate_is_green(sha: str, repo_slug: str) -> bool:
    """`All checks green: success` no SHA. Erro de I/O devolve False: falha de
    leitura NEGA o skip, nunca o concede."""
    if not sha or not repo_slug:
        return False
    proc = subprocess.run(
        ["gh", "api", f"repos/{repo_slug}/commits/{sha}/check-runs?per_page=100"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if proc.returncode != 0:
        return False
    return _has_green_aggregate(proc.stdout)


def _has_green_aggregate(payload: str) -> bool:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return False
    runs = data.get("check_runs") if isinstance(data, dict) else None
    if not isinstance(runs, list):
        return False
    return any(
        r.get("name") == REQUIRED_AGGREGATE and r.get("conclusion") == "success" for r in runs
    )


def _merged_from_base(repo: Path, parents: Sequence[str]) -> bool:
    """Base é `HEAD^1`, não `origin/main`: é o commit contra o qual o GitHub
    calculou o merge-ref, então dispensa fetch e não depende de ref fresca."""
    if len(parents) != 2:
        return False
    return _is_ancestor(repo, parents[1], _rev(repo, "HEAD^1"))


def decide(repo: Path, *, event_head_sha: str, repo_slug: str) -> tuple[bool, str]:
    """Avalia os 5 predicados sobre `HEAD^2` — ver §âncora no docstring do módulo."""
    branch_head = _rev(repo, "HEAD^2")
    if not branch_head:
        return False, "sem HEAD^2 — o checkout não é o merge-ref de um pull_request"
    parents = _parents(repo, branch_head)
    entrou = _incoming_paths(repo, parents[0], branch_head) if len(parents) == 2 else ()
    return should_skip(
        head_matches_event=bool(event_head_sha) and branch_head == event_head_sha,
        branch_parents=parents,
        merged_commit_on_base=_merged_from_base(repo, parents),
        incoming_paths=entrou,
        previous_run_green=aggregate_is_green(parents[0] if parents else "", repo_slug),
    )


def _emit(skip: bool, reason: str) -> None:
    """Output para o job + summary. O summary é o que torna a taxa de hit
    auditável; sem ele a estimativa de 39,5% nunca é confrontada."""
    _append(
        os.environ.get("GITHUB_OUTPUT"), f"incoming_main_docs_only={'true' if skip else 'false'}\n"
    )
    verdict = "pula jobs pesados" if skip else f"roda tudo — {reason}"
    _append(os.environ.get("GITHUB_STEP_SUMMARY"), f"skip-class (ADR-322): **{verdict}**\n")


def _append(target: str | None, line: str) -> None:
    if not target:
        print(line, end="")
        return
    with Path(target).open("a", encoding="utf-8") as fh:
        fh.write(line)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", type=Path)
    parser.add_argument("--emit", action="store_true")
    args = parser.parse_args()
    try:
        skip, reason = decide(
            args.repo.resolve(),
            event_head_sha=os.environ.get("PR_HEAD_SHA", ""),
            repo_slug=os.environ.get("GITHUB_REPOSITORY", ""),
        )
    except Exception as exc:  # noqa: BLE001 — nunca reprovar o step que decide
        print(f"skip-class indeterminado ({type(exc).__name__}: {exc})", file=sys.stderr)
        skip, reason = False, "erro ao decidir"
    if args.emit:
        _emit(skip, reason)
    else:
        print("true" if skip else f"false ({reason})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
