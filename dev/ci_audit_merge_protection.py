#!/usr/bin/env python3
"""Audita a proteção de main (ADR-415): o SHA que ENTROU foi gateado? Modos:
`--sha <sha>` (pós-merge), `--sweep` (bypasses do período), `--backfill <json>`."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

GATE_CHECK = "All checks green"
AUDIT_LABEL = "merge-protection"
AUDIT_ISSUE_TITLE = "CI: merge sem gate em main — auditoria da proteção (ADR-415)"
SWEEP_PERIOD = "week"
SWEEP_MAX_PAGES = 8

GATED = "gated"
LATE = "late"
RED = "red"
ABSENT = "absent"
UNKNOWN = "unknown"
UNGATED = frozenset({LATE, RED, ABSENT, UNKNOWN})

Runner = Callable[[list[str]], str]


def _gh(args: list[str]) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])}: {proc.stderr.strip()[:200]}")
    return proc.stdout


def _api(run: Runner, path: str, jq: str | None = None) -> Any:
    args = ["api", path]
    if jq:
        args += ["--jq", jq]
    out = run(args).strip()
    return json.loads(out) if out else None


def _ts(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


@dataclass(frozen=True)
class MergeVerdict:
    """Veredito sobre um SHA de `main`. `gated` exige o required check verde
    **e concluído antes do merge** — verde que chega depois não gateou nada."""

    sha: str
    pr: int | None
    verdict: str
    detail: str

    @property
    def is_ungated(self) -> bool:
        return self.verdict in UNGATED


def classify(check: dict[str, Any] | None, merged_at: str | None) -> tuple[str, str]:
    """Veredito e motivo a partir do check-run do head e do instante do merge."""
    if check is None:
        return ABSENT, f"nenhum check-run `{GATE_CHECK}` no head do PR"
    conclusion = check.get("conclusion") or "pendente"
    if conclusion != "success":
        return RED, f"`{GATE_CHECK}` = {conclusion} no head"
    done, merged = _ts(check.get("completed_at")), _ts(merged_at)
    if done is None or merged is None:
        return UNKNOWN, "check-run ou merge sem timestamp — não dá para ordenar"
    if done > merged:
        atraso = int((done - merged).total_seconds())
        return LATE, f"`{GATE_CHECK}` só concluiu {atraso}s DEPOIS do merge"
    return GATED, f"`{GATE_CHECK}` verde {int((merged - done).total_seconds())}s antes do merge"


def _pull_for(run: Runner, sha: str) -> dict[str, Any] | None:
    """PR que trouxe o SHA. O squash cria commit novo em main e os check-runs
    ficam no head do PR — ler check-runs do SHA de main devolve sempre vazio."""
    pulls = _api(run, f"repos/{{owner}}/{{repo}}/commits/{sha}/pulls") or []
    return pulls[0] if pulls else None


def _gate_check_of(run: Runner, head_sha: str) -> dict[str, Any] | None:
    runs = _api(run, f"repos/{{owner}}/{{repo}}/commits/{head_sha}/check-runs") or {}
    matches = [c for c in runs.get("check_runs", []) if c.get("name") == GATE_CHECK]
    return matches[0] if matches else None


def verdict_for_sha(run: Runner, sha: str) -> MergeVerdict:
    """Veredito do SHA de main, resolvendo PR → head → check-run."""
    pull = _pull_for(run, sha)
    if pull is None:
        return MergeVerdict(sha, None, UNKNOWN, "nenhum PR associado ao SHA em main")
    check = _gate_check_of(run, pull["head"]["sha"])
    verdict, detail = classify(check, pull.get("merged_at"))
    return MergeVerdict(sha, pull.get("number"), verdict, detail)


def bypass_index(run: Runner, period: str = SWEEP_PERIOD) -> dict[str, str]:
    """SHA → ator dos merges com `result: bypass`. Pagina até esgotar: o default
    da API é `time_period=day` e uma página só — foi assim que uma leitura viu
    2 de 64 bypasses em 2026-08-25 (ADR-415 §D4)."""
    found: dict[str, str] = {}
    for page in range(1, SWEEP_MAX_PAGES + 1):
        query = f"per_page=100&time_period={period}&page={page}"
        suites = _api(run, f"repos/{{owner}}/{{repo}}/rulesets/rule-suites?{query}") or []
        if not suites:
            break
        for suite in suites:
            if suite.get("result") == "bypass":
                found[suite["after_sha"]] = suite.get("actor_name") or "?"
    return found


def _safe_bypass_index(
    run: Runner, period: str = SWEEP_PERIOD
) -> tuple[dict[str, str], str | None]:
    """Índice de bypass, ou o motivo de não ter lido. Ler rule-suites exige
    permissão de administração, que o `GITHUB_TOKEN` não tem — a ausência é
    declarada, nunca silenciosa."""
    try:
        return bypass_index(run, period), None
    except RuntimeError as exc:
        return {}, str(exc)


def _describe(verdict: MergeVerdict, bypass_actor: str | None) -> str:
    pr = f"PR #{verdict.pr}" if verdict.pr else "sem PR"
    origem = f" · bypass do Ruleset por `{bypass_actor}`" if bypass_actor else ""
    return f"`{verdict.sha[:8]}` ({pr}) — **{verdict.verdict}**: {verdict.detail}{origem}"


def _issue_body(lines: list[str], note: str | None) -> str:
    corpo = [
        f"Merges em `main` cujo required check `{GATE_CHECK}` **não gateou o SHA que entrou**.",
        "",
        "O predicado é o veredito *no momento do merge*: check ausente, vermelho,",
        "ou concluído depois do merge. Verde que chega depois não protegeu nada.",
        "",
        *[f"- {line}" for line in lines],
    ]
    if note:
        corpo += ["", f"> Enriquecimento de bypass indisponível: {note}"]
    corpo += ["", "_Mantida por `dev/ci_audit_merge_protection.py` (ADR-415)._"]
    return "\n".join(corpo)


def _find_issue(run: Runner) -> int | None:
    out = run(["issue", "list", "--state", "open", "--label", AUDIT_LABEL, "--json", "number"])
    issues = json.loads(out or "[]")
    return issues[0]["number"] if issues else None


def _write_issue(run: Runner, number: int | None, body: str) -> None:
    if number is None:
        args = ["issue", "create", "--title", AUDIT_ISSUE_TITLE, "--label", AUDIT_LABEL]
        run([*args, "--body", body])
        return
    run(["issue", "edit", str(number), "--body", body])


def upsert_issue(run: Runner, lines: list[str], note: str | None, dry_run: bool) -> None:
    body = _issue_body(lines, note)
    number = _find_issue(run)
    if dry_run:
        print(f"[dry-run] issue {'edit ' + str(number) if number else 'create'}:\n{body}")
        return
    _write_issue(run, number, body)


def audit_shas(
    run: Runner, shas: list[str], period: str = SWEEP_PERIOD
) -> tuple[list[str], str | None]:
    """Linhas de relatório dos SHAs NÃO gateados, e o motivo se o bypass não pôde
    ser lido. O índice de bypass é preguiçoso: no caminho feliz (push que gateou)
    ele custaria até 8 páginas de API por merge para enriquecer lista vazia."""
    ungated = [v for v in (verdict_for_sha(run, sha) for sha in shas) if v.is_ungated]
    if not ungated:
        return [], None
    bypasses, note = _safe_bypass_index(run, period)
    return [_describe(v, bypasses.get(v.sha)) for v in ungated], note


def _sweep_shas(run: Runner, period: str) -> tuple[list[str], str | None]:
    bypasses, note = _safe_bypass_index(run, period)
    return list(bypasses), note


def _run_sha_mode(run: Runner, sha: str, dry_run: bool) -> int:
    lines, note = audit_shas(run, [sha])
    if not lines:
        print(f"gate ok: {sha[:8]} entrou com `{GATE_CHECK}` verde antes do merge")
        return 0
    print("\n".join(lines))
    upsert_issue(run, lines, note, dry_run)
    return 0


def _run_sweep_mode(run: Runner, period: str, dry_run: bool) -> int:
    shas, note = _sweep_shas(run, period)
    if note:
        print(f"rule-suites indisponível: {note}", file=sys.stderr)
    print(f"sweep {period}: {len(shas)} merge(s) com bypass do Ruleset")
    lines, _ = audit_shas(run, shas, period) if shas else ([], None)
    if lines:
        upsert_issue(run, lines, note, dry_run)
    return 0


def _backfill_shas(path: str) -> list[str]:
    data = json.loads(open(path, encoding="utf-8").read())
    return [b["after_sha"] for b in data.get("bypasses", [])]


def _run_backfill_mode(run: Runner, path: str, period: str) -> int:
    """Inventário único sobre a evidência capturada — a API já não os retém."""
    shas = _backfill_shas(path)
    lines, note = audit_shas(run, shas, period)
    print(f"backfill: {len(shas)} SHA(s) de bypass, {len(lines)} sem gate")
    print("\n".join(lines) if lines else "(nenhum sem gate)")
    if note:
        print(f"nota: {note}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sha", help="veredito de um SHA de main (modo pós-merge)")
    group.add_argument("--sweep", action="store_true", help="bypasses do período")
    group.add_argument("--backfill", help="JSON de evidência com a lista de bypasses")
    parser.add_argument(
        "--period", default=SWEEP_PERIOD, help="janela do índice de bypass (day|week|month)"
    )
    parser.add_argument("--dry-run", action="store_true", help="não escreve Issue")
    return parser


def main(argv: list[str] | None = None, run: Runner = _gh) -> int:
    args = build_parser().parse_args(argv)
    if args.sha:
        return _run_sha_mode(run, args.sha, args.dry_run)
    if args.backfill:
        return _run_backfill_mode(run, args.backfill, args.period)
    return _run_sweep_mode(run, args.period, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
