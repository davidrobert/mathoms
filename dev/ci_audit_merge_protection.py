#!/usr/bin/env python3
"""Audita a proteção de main (ADR-415 · ADR-448): o SHA que ENTROU foi gateado?
Modos: `--sha <sha>` (pós-merge), `--ruleset` (tripwire sem admin), `--sweep`
(com admin: history do ruleset + bypasses do período), `--backfill <json>`.
Cada incidente vira UMA issue própria."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.merge_incident_issues import (  # noqa: E402
    AUDIT_LABEL,
    marker,
    open_issue,
    registry,
)
from dev.ruleset_bypass_alarm import (  # noqa: E402
    ADR_448_APPLIED,
    check_ruleset,
    ruleset_tripwire,
)

__all__ = ["AUDIT_LABEL"]

GATE_CHECK = "All checks green"
MAIN_REF = "refs/heads/main"
SWEEP_PERIOD = "week"
SWEEP_MAX_PAGES = 8
PAGE_SIZE = 100

GATED = "gated"
LATE = "late"
RED = "red"
ABSENT = "absent"
UNKNOWN = "unknown"
UNGATED = frozenset({LATE, RED, ABSENT, UNKNOWN})

TRIAGE = (
    "**Triagem:** uso sancionado do break-glass — rollback de gate brickado ou "
    "indisponibilidade da plataforma (ADR-415 D2, mantidos pela ADR-448 D2)? "
    "Feche com o motivo. Fora disso é incidente: `red` pede revert; nos outros "
    "vereditos, confirme o CI de `main` depois do merge. Quem fecha é a "
    "triagem humana — o detector não fecha nem reabre."
)

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


@dataclass(frozen=True)
class BypassRecord:
    """Avaliação `bypass` do Ruleset para um push em `main` (rule-suites)."""

    actor: str
    suite_id: int | None
    pushed_at: datetime | None = None


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
    """Filtra pelo NOME na própria query: o default é `per_page=30` e um head
    real já traz 20 check-runs — passar de 30 empurraria o gate para fora da
    página e produziria `absent` falso, que é o veredito mais alarmante."""
    query = f"per_page=100&check_name={quote(GATE_CHECK)}"
    runs = _api(run, f"repos/{{owner}}/{{repo}}/commits/{head_sha}/check-runs?{query}") or {}
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


def bypass_index(run: Runner, period: str = SWEEP_PERIOD) -> dict[str, BypassRecord]:
    """SHA → registro dos pushes em main com `result: bypass`. Pagina até
    esgotar: o default da API é `time_period=day` e uma página só — foi assim
    que uma leitura viu 2 de 64 bypasses em 2026-08-25 (ADR-415 §D4). O filtro
    `rule_suite_result` encolhe a leitura (24 de 93 avaliações em 2026-10-09);
    sair pelo teto é truncagem silenciosa, a classe que a ADR denuncia: erro."""
    found: dict[str, BypassRecord] = {}
    for page in range(1, SWEEP_MAX_PAGES + 1):
        suites = (
            _api(
                run, f"repos/{{owner}}/{{repo}}/rulesets/rule-suites?{_suites_query(period, page)}"
            )
            or []
        )
        found |= _bypass_records(suites)
        if len(suites) < PAGE_SIZE:
            return found  # página parcial (ou vazia) = fim real da leitura
    raise RuntimeError(
        f"rule-suites: {SWEEP_MAX_PAGES} páginas cheias em `{period}` — leitura truncada"
    )


def _suites_query(period: str, page: int) -> str:
    return (
        f"ref={MAIN_REF}&rule_suite_result=bypass&per_page={PAGE_SIZE}"
        f"&time_period={period}&page={page}"
    )


def _bypass_records(suites: list[dict[str, Any]]) -> dict[str, BypassRecord]:
    """O filtro do servidor não é confiado sozinho: só `result: bypass` entra."""
    return {
        s["after_sha"]: BypassRecord(
            s.get("actor_name") or "?", s.get("id"), _ts(s.get("pushed_at"))
        )
        for s in suites
        if s.get("result") == "bypass"
    }


def _safe_bypass_index(
    run: Runner, period: str = SWEEP_PERIOD
) -> tuple[dict[str, BypassRecord], str | None]:
    """Índice de bypass, ou o motivo de não ter lido. Ler rule-suites exige
    permissão de administração, que o `GITHUB_TOKEN` não tem — a ausência é
    declarada, nunca silenciosa."""
    try:
        return bypass_index(run, period), None
    except RuntimeError as exc:
        return {}, str(exc)


def merged_by(run: Runner, pr: int | None) -> str | None:
    """Quem mergeou, pelo PR. Legível com o `GITHUB_TOKEN`, ao contrário do
    ator do rule-suite — é o que a issue tem quando o rule-suite dá 403."""
    if pr is None:
        return None
    pull = _api(run, f"repos/{{owner}}/{{repo}}/pulls/{pr}") or {}
    return (pull.get("merged_by") or {}).get("login")


def _describe(verdict: MergeVerdict, bypass: BypassRecord | None) -> str:
    pr = f"PR #{verdict.pr}" if verdict.pr else "sem PR"
    origem = f" · bypass do Ruleset por `{bypass.actor}`" if bypass else ""
    return f"`{verdict.sha[:8]}` ({pr}) — **{verdict.verdict}**: {verdict.detail}{origem}"


def incident_title(verdict: MergeVerdict) -> str:
    pr = f"PR #{verdict.pr}" if verdict.pr else "sem PR"
    if verdict.is_ungated:
        return f"CI: {verdict.sha[:8]} ({pr}) entrou em main sem gate — {verdict.verdict}"
    return f"CI: {verdict.sha[:8]} ({pr}) entrou em main por bypass do Ruleset"


def _rule_suite_line(bypass: BypassRecord | None, note: str | None, period: str) -> str:
    if bypass:
        return f"`bypass` por `{bypass.actor}` (rule-suite {bypass.suite_id})"
    if note:
        return f"não lido — {note}"
    return f"nenhum `bypass` para este SHA em `time_period={period}`"


@dataclass(frozen=True)
class IncidentContext:
    """O que enriquece o veredito: o bypass (ou a lacuna) e quem mergeou."""

    bypass: BypassRecord | None
    note: str | None
    merger: str | None
    period: str = SWEEP_PERIOD


def incident_body(verdict: MergeVerdict, ctx: IncidentContext) -> str:
    pr = f"#{verdict.pr}" if verdict.pr else "nenhum"
    por = f" · mergeado por `{ctx.merger}` (`merged_by` do PR)" if ctx.merger else ""
    return "\n".join(
        [
            marker("sha", verdict.sha),
            "Merge em `main` fora do gate — um incidente, uma issue (ADR-448).",
            "",
            f"- **Commit:** {verdict.sha}",
            f"- **PR:** {pr}{por}",
            f"- **`{GATE_CHECK}` no momento do merge:** **{verdict.verdict}** — {verdict.detail}",
            f"- **Rule-suite:** {_rule_suite_line(ctx.bypass, ctx.note, ctx.period)}",
            "",
            TRIAGE,
            "",
            "_Aberta por `dev/ci_audit_merge_protection.py` (ADR-415 D3 · ADR-448)._",
        ]
    )


def file_incidents(
    run: Runner,
    verdicts: list[MergeVerdict],
    index: tuple[dict[str, BypassRecord], str | None],
    dry_run: bool,
    period: str = SWEEP_PERIOD,
) -> int:
    """Uma issue por SHA ainda não registrado; devolve quantas abriu. Rodar de
    novo (re-run do job, sweep da mesma janela) não duplica."""
    bypasses, note = index
    keys = registry(run)
    abertas = 0
    for verdict in verdicts:
        if f"sha={verdict.sha}" in keys:
            print(f"já registrado: {verdict.sha[:8]} — nenhuma issue nova")
            continue
        ctx = IncidentContext(bypasses.get(verdict.sha), note, merged_by(run, verdict.pr), period)
        open_issue(run, incident_title(verdict), incident_body(verdict, ctx), dry_run)
        abertas += 1
    return abertas


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


def _run_sha_mode(run: Runner, sha: str, dry_run: bool) -> int:
    verdict = verdict_for_sha(run, sha)
    if not verdict.is_ungated:
        print(f"gate ok: {sha[:8]} entrou com `{GATE_CHECK}` verde antes do merge")
        return 0
    print(_describe(verdict, None))
    file_incidents(run, [verdict], _safe_bypass_index(run), dry_run)
    return 0


def _not_measured(what: str, note: str) -> int:
    """Sem leitura, não há contagem. Imprimir `0 bypasses` depois de um 403
    seria o instrumento cometendo a falta que ele existe para denunciar — e
    `rulesets/rule-suites` exige Administration:read, que o `GITHUB_TOKEN` não
    pode receber (não existe na chave `permissions:`), então esse 403 é o caso
    esperado, não o excepcional. Sai != 0 para o run ficar vermelho."""
    print(f"NÃO MEDIDO: {what} — {note}", file=sys.stderr)
    print(f"sweep abortado: sem leitura de {what} não há contagem a afirmar")
    return 2


def _run_sweep_mode(run: Runner, period: str, dry_run: bool, now: datetime) -> int:
    """Todo `bypass` vira incidente, mesmo com veredito `gated`: em 2026-10-09,
    3 dos 24 tinham o check verde no head e base desatualizada sob `strict`."""
    ruleset_note = check_ruleset(run, now, dry_run)
    if ruleset_note:
        return _not_measured("ruleset", ruleset_note)
    bypasses, note = _safe_bypass_index(run, period)
    if note:
        return _not_measured("rule-suites", note)
    novos = _since_adr_448(bypasses)
    antigos = len(bypasses) - len(novos)
    print(f"sweep {period}: {len(bypasses)} merge(s) com bypass ({antigos} anteriores à ADR-448)")
    verdicts = [verdict_for_sha(run, sha) for sha in novos]
    file_incidents(run, verdicts, (novos, None), dry_run, period)
    return 0


def _since_adr_448(bypasses: dict[str, BypassRecord]) -> dict[str, BypassRecord]:
    """Bypass anterior à aplicação da ADR-448 era o regime da ADR-415 D2 e tem
    registro próprio (a #1728, triada e fechada): reabri-lo aqui viraria 24
    issues de uma vez sobre a rajada de 2026-10-09. Sem `pushed_at`, conta."""
    return {
        sha: r
        for sha, r in bypasses.items()
        if r.pushed_at is None or r.pushed_at >= ADR_448_APPLIED
    }


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
    group.add_argument("--ruleset", action="store_true", help="tripwire do ruleset (sem admin)")
    group.add_argument("--sweep", action="store_true", help="ruleset + bypasses do período")
    group.add_argument("--backfill", help="JSON de evidência com a lista de bypasses")
    parser.add_argument(
        "--period", default=SWEEP_PERIOD, help="janela do índice de bypass (day|week|month)"
    )
    parser.add_argument("--dry-run", action="store_true", help="não escreve issue")
    return parser


def main(argv: list[str] | None = None, run: Runner = _gh, now: datetime | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.sha:
        return _run_sha_mode(run, args.sha, args.dry_run)
    if args.backfill:
        return _run_backfill_mode(run, args.backfill, args.period)
    if args.ruleset:
        return ruleset_tripwire(run, args.dry_run)
    return _run_sweep_mode(run, args.period, args.dry_run, now or datetime.now(timezone.utc))


if __name__ == "__main__":
    sys.exit(main())
