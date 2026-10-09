"""Registro de incidentes de proteção de `main`: uma issue por incidente
(ADR-448), idempotente por marcador no corpo."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable

AUDIT_LABEL = "merge-protection"
PAGE_SIZE = 100
MAX_PAGES = 20
_MARKER = re.compile(r"<!-- merge-audit:([a-z-]+)=([0-9A-Za-z._:+-]+) -->")

Runner = Callable[[list[str]], str]


@dataclass(frozen=True)
class IssueRef:
    number: int
    state: str


def marker(kind: str, value: str) -> str:
    """Chave de idempotência gravada no corpo. Invisível no render; é ela, e
    não o título, que identifica o incidente — título se edita na triagem."""
    return f"<!-- merge-audit:{kind}={value} -->"


def _issues_page(run: Runner, page: int) -> list[dict]:
    query = f"labels={AUDIT_LABEL}&state=all&per_page={PAGE_SIZE}&page={page}"
    out = run(["api", f"repos/{{owner}}/{{repo}}/issues?{query}"]).strip()
    return json.loads(out) if out else []


def registry(run: Runner) -> dict[str, IssueRef]:
    """Chave `tipo=valor` → issue que a registrou, aberta OU fechada. Lê a
    listagem REST, que é consistente: o `gh issue list --label` usa a search
    API, que indexa com atraso, e um sweep logo depois do push duplicaria a
    issue. Teto com páginas cheias é truncagem — erro, nunca 'não registrado'."""
    found: dict[str, IssueRef] = {}
    for page in range(1, MAX_PAGES + 1):
        issues = _issues_page(run, page)
        for issue in issues:
            ref = IssueRef(issue["number"], issue.get("state", "open"))
            found |= {f"{k}={v}": ref for k, v in _MARKER.findall(issue.get("body") or "")}
        if len(issues) < PAGE_SIZE:
            return found
    raise RuntimeError(f"issues `{AUDIT_LABEL}`: {MAX_PAGES} páginas cheias — leitura truncada")


def open_issue(run: Runner, title: str, body: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] issue create: {title}\n{body}")
        return
    created = run(["issue", "create", "--title", title, "--label", AUDIT_LABEL, "--body", body])
    print(f"issue aberta: {created.strip()}")


def raise_live_alarm(run: Runner, key: str, issue: tuple[str, str], dry_run: bool) -> None:
    """Alarme de condição VIVA: fechar a issue com a condição de pé não pode
    silenciá-lo, então issue fechada é reaberta. SHA mergeado é passado e não
    passa por aqui — para ele, fechada é registrada."""
    ref = registry(run).get(key)
    if ref is None:
        open_issue(run, *issue, dry_run)
        return
    if ref.state == "open":
        print(f"alarme já aberto em #{ref.number}")
        return
    note = "Reaberta pelo detector: a condição continua de pé (ADR-448)."
    if dry_run:
        print(f"[dry-run] issue reopen #{ref.number}: {note}")
        return
    run(["issue", "reopen", str(ref.number), "--comment", note])
    print(f"issue reaberta: #{ref.number}")
