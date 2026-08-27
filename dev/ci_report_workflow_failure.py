#!/usr/bin/env python3
"""Canal de falha de workflow agendado (ADR-210 §camada 4): registra a falha
numa Issue rotulada. Uso: `--workflow <arquivo> --label <label>`."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Callable

Runner = Callable[[list[str]], str]
BODY_LIMIT = 60_000


def _gh(args: list[str]) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])}: {proc.stderr.strip()[:200]}")
    return proc.stdout


def run_url() -> str:
    """URL do run que falhou, ou '' fora do Actions."""
    server = os.environ.get("GITHUB_SERVER_URL", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    return f"{server}/{repo}/actions/runs/{run_id}" if all((server, repo, run_id)) else ""


def title_for(workflow: str) -> str:
    return f"[ops-watchdog] `{workflow}` falhou — compensador sem cobertura"


def occurrence(workflow: str) -> str:
    """Uma ocorrência. Cada falha ACRESCENTA: silenciar a nova por causa de uma
    Issue velha é o defeito da #642, que ficou 46 dias mascarando falhas novas."""
    url = run_url() or "(run local)"
    return f"- `{workflow}` falhou em {os.environ.get('GITHUB_RUN_STARTED_AT', 'agora')} — {url}"


_CONTEXTO = (
    "> O `S2` mede run **iniciado**, não bem-sucedido — um compensador que "
    "inicia e falha todo run é invisível para ele. Em 2026-08-17 o "
    "`auto-update-prs` falhou 10× em ~5h, a fila de merge parou, e nada no "
    "repositório percebeu."
)
_RODAPE = (
    "_Aberta por `dev/ci_report_workflow_failure.py`; rot cobrada pelo `S3` da "
    "entrada `%s` em `.github/scheduled-workflows.yml`. Fecha por triagem "
    "humana — o workflow voltar a passar não a fecha sozinha, de propósito: o "
    "que precisa de decisão é a causa._"
)


def first_body(workflow: str, label: str) -> str:
    abertura = (
        f"O workflow agendado `{workflow}` **falhou**. Ele é um compensador: o "
        "manifesto o declara como cobertura viva, e falha sem canal é a classe "
        "que a [[ADR-210]] §camada 4 existe para matar."
    )
    partes = [abertura, "", _CONTEXTO, "", "## Ocorrências", "", occurrence(workflow), ""]
    return "\n".join([*partes, _RODAPE % label])


def ensure_label(run: Runner, label: str) -> None:
    """`gh issue create --label X` ABORTA se X não existe, e o `gh` não a cria.
    Como este caminho só é alcançado quando o compensador falha, a ausência
    ficaria latente e explodiria no primeiro incidente — foi exatamente o que
    aconteceu com `merge-protection` no run 32887693308 (ADR-415)."""
    run(["label", "create", label, "--force", "--color", "D93F0B",
         "--description", "Compensador agendado falhou (ADR-210 §camada 4)"])  # fmt: skip


def find_issue(run: Runner, label: str) -> int | None:
    out = run(["issue", "list", "--state", "open", "--label", label, "--json", "number"])
    issues = json.loads(out or "[]")
    return issues[0]["number"] if issues else None


def report(run: Runner, workflow: str, label: str, dry_run: bool) -> int:
    """Abre a Issue, ou acrescenta ocorrência à que já existe."""
    number = find_issue(run, label)
    if dry_run:
        print(
            f"[dry-run] {'comment ' + str(number) if number else 'create'}: {occurrence(workflow)}"
        )
        return 0
    if number is None:
        ensure_label(run, label)
        run(["issue", "create", "--title", title_for(workflow), "--label", label,
             "--body", first_body(workflow, label)])  # fmt: skip
        print(f"issue aberta para `{workflow}` (label `{label}`)")
        return 0
    run(["issue", "comment", str(number), "--body", occurrence(workflow)])
    print(f"ocorrência acrescentada à issue #{number} (label `{label}`)")
    return 0


def main(argv: list[str] | None = None, run: Runner = _gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True, help="arquivo do workflow que falhou")
    parser.add_argument("--label", required=True, help="label declarada em `alerts:` no manifesto")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    return report(run, args.workflow, args.label, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
