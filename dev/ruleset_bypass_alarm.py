"""Estado do Ruleset de `main` (ADR-448). Dois braços: o tripwire do push lê,
sem admin, o que o GET devolve a qualquer um; o sweep, com admin, varre o
`history` atrás de janela fora do estado da ADR-448."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from dev.merge_incident_issues import marker, open_issue, raise_live_alarm, registry

RULESET_ID = 15884038
GATE_CHECK = "All checks green"
# Versão 52592012 do history: a ADR-448 aplicada. Antes dela, bypass do papel
# Admin era o regime sancionado da ADR-415 D2, registrado na #1728 — janela e
# bypass anteriores não são incidente deste formato.
ADR_448_APPLIED = datetime(2026, 10, 9, 15, 53, 41, tzinfo=timezone.utc)
# A concessão da ADR-448 D2 dura um `gh pr merge --admin` entre o PUT e o
# `trap` que revoga: o ensaio de 2026-10-09 ficou aberto 703 ms. 15 min cobrem
# o break-glass feito à mão, sem o trap, e rede lenta; acima disso não é mais
# "concessão para UM merge". Vale só para bypass: gate enfraquecido não tem janela.
BREAK_GLASS_TOLERANCE = timedelta(minutes=15)
HISTORY_PAGE_SIZE = 100
HISTORY_MAX_PAGES = 10
MISSING_KEY = f"ruleset-missing={RULESET_ID}"
NOT_VISIBLE = (
    "o GET do ruleset não trouxe `bypass_actors` — a API só devolve o campo a "
    "quem administra o ruleset, e ler a ausência como `0` seria o alarme mudo"
)
TRIAGE = (
    "**Triagem:** confira o `history` do ruleset e o runbook "
    "`docs/reference/runbooks/pipeline_rollback.md` §4.2. Merge feito na janela "
    "aparece como `bypass` no rule-suites e ganha issue própria no `--sweep`."
)

Runner = Callable[[list[str]], str]


@dataclass(frozen=True)
class Window:
    """Versões consecutivas do `history` fora do estado da ADR-448. A versão
    que a abriu é a chave do alarme: uma issue por janela."""

    version_id: int
    opened: datetime
    closed: datetime | None
    bypass_count: int
    problems: tuple[str, ...]

    def duration(self, now: datetime) -> timedelta:
        return (self.closed or now) - self.opened


def _api(run: Runner, path: str) -> Any:
    out = run(["api", path]).strip()
    return json.loads(out) if out else None


def _ts(value: str) -> datetime:
    """O ruleset devolve `Z` e o history, `-04:00`, com ~290 ms entre os dois
    para o mesmo evento: compare instantes parseados, nunca strings."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="milliseconds")


def _ruleset_path(suffix: str = "") -> str:
    return f"repos/{{owner}}/{{repo}}/rulesets/{RULESET_ID}{suffix}"


def read_ruleset(run: Runner) -> dict[str, Any] | None:
    """O ruleset, ou None se ele não existe: 404 é `main` sem proteção, alarme
    máximo, nunca 'não medido'. Outro erro sobe — não é veredito sobre ele."""
    try:
        return _api(run, _ruleset_path()) or {}
    except RuntimeError as exc:
        if "HTTP 404" in str(exc):
            return None
        raise


def _required_checks(ruleset: dict[str, Any]) -> dict[str, Any] | None:
    rules = [r for r in ruleset.get("rules") or [] if r.get("type") == "required_status_checks"]
    return (rules[0].get("parameters") or {}) if rules else None


def gate_problems(ruleset: dict[str, Any]) -> tuple[str, ...]:
    """O que o GET devolve a quem não administra e basta para dizer se o gate
    de `main` está de pé: `enforcement`, o required check e o `strict`."""
    problems = []
    if ruleset.get("enforcement") != "active":
        problems.append(f"`enforcement` = `{ruleset.get('enforcement')}`")
    params = _required_checks(ruleset)
    contexts = {c.get("context") for c in (params or {}).get("required_status_checks", [])}
    if GATE_CHECK not in contexts:
        problems.append(f"`{GATE_CHECK}` fora dos required checks")
    if params is not None and not params.get("strict_required_status_checks_policy"):
        problems.append("`strict` desligado")
    return tuple(problems)


def _missing_issue() -> tuple[str, str]:
    title = f"CI: Ruleset main-protection ({RULESET_ID}) não existe — main sem proteção"
    body = "\n".join(
        [
            marker(*MISSING_KEY.split("=")),
            f"`GET rulesets/{RULESET_ID}` respondeu 404: `main` não tem o gate da ADR-415.",
            "",
            "_Aberta por `dev/ci_audit_merge_protection.py` (ADR-448)._",
        ]
    )
    return title, body


def _changed_issue(key: str, changed: datetime, problems: tuple[str, ...]) -> tuple[str, str]:
    estado = "; ".join(problems) if problems else "gate de pé (enforcement, required check, strict)"
    titulo = "enfraqueceu o gate" if problems else "mudou"
    body = "\n".join(
        [
            marker(*key.split("=", 1)),
            f"O Ruleset `main-protection` (id {RULESET_ID}) mudou em {_iso(changed)}.",
            "",
            f"- **Lido sem admin depois da mudança:** {estado}",
            "- **O que este braço não vê:** `bypass_actors` (a API o omite para quem "
            "não administra). Rode `dev/ci_audit_merge_protection.py --sweep` com "
            "credencial de admin: ele diz se a mudança foi break-glass dentro da tolerância.",
            "",
            TRIAGE,
            "",
            "_Aberta pelo tripwire do push (`--ruleset`, ADR-448)._",
        ]
    )
    return f"CI: Ruleset main-protection {titulo} em {changed:%Y-%m-%d %H:%M}Z", body


def ruleset_tripwire(run: Runner, dry_run: bool) -> int:
    """Braço sem admin, a cada push. Erro de API que não é 404 não é veredito
    sobre o ruleset: sai != 0, e o run fica vermelho em vez de calado."""
    try:
        ruleset = read_ruleset(run)
    except RuntimeError as exc:
        print(f"NÃO MEDIDO: ruleset — {exc}", file=sys.stderr)
        return 2
    if ruleset is None:
        raise_live_alarm(run, MISSING_KEY, _missing_issue(), dry_run)
    else:
        _trip(run, ruleset, dry_run)
    return 0


def _trip(run: Runner, ruleset: dict[str, Any], dry_run: bool) -> None:
    """Gate enfraquecido é alarme vivo; mudança nova (`updated_at` sem registro)
    é evento a explicar — concessão e toggle de `enforcement` passam por aqui,
    e o toggle não deixa rule-suite."""
    changed = _ts(ruleset["updated_at"])
    key = f"ruleset-updated={_iso(changed)}"
    problems = gate_problems(ruleset)
    issue = _changed_issue(key, changed, problems)
    if problems:
        raise_live_alarm(run, key, issue, dry_run)
    elif key in registry(run):
        print(f"ruleset de pé e sem mudança nova desde {_iso(changed)}")
    else:
        open_issue(run, *issue, dry_run)


def _versions_since_epoch(run: Runner) -> list[dict[str, Any]]:
    """Versões do history desde a aplicação da ADR-448, a mais antiga primeiro.
    A API devolve da mais nova para a mais antiga: a primeira anterior ao marco
    encerra a leitura. Teto com páginas cheias é truncagem — erro."""
    kept: list[dict[str, Any]] = []
    for page in range(1, HISTORY_MAX_PAGES + 1):
        query = f"per_page={HISTORY_PAGE_SIZE}&page={page}"
        versions = _api(run, _ruleset_path(f"/history?{query}")) or []
        recent = [v for v in versions if _ts(v["updated_at"]) >= ADR_448_APPLIED]
        kept += recent
        if len(recent) < len(versions) or len(versions) < HISTORY_PAGE_SIZE:
            return kept[::-1]
    raise RuntimeError(f"history: {HISTORY_MAX_PAGES} páginas cheias — leitura truncada")


def _state(run: Runner, version_id: int) -> dict[str, Any]:
    return (_api(run, _ruleset_path(f"/history/{version_id}")) or {}).get("state") or {}


def _grow(window: Window | None, version: dict[str, Any], state: dict[str, Any]) -> Window:
    bypass, problems = len(state.get("bypass_actors") or []), gate_problems(state)
    if window is None:
        return Window(version["version_id"], _ts(version["updated_at"]), None, bypass, problems)
    merged = tuple(dict.fromkeys(window.problems + problems))
    return replace(window, bypass_count=max(window.bypass_count, bypass), problems=merged)


def breach_windows(run: Runner) -> list[Window]:
    """Janelas fora do estado da ADR-448 desde a aplicação dela: fechadas (o
    sweep diário quase nunca pega uma concessão de 703 ms aberta) e a atual."""
    windows: list[Window] = []
    current: Window | None = None
    for version in _versions_since_epoch(run):
        current = _advance(windows, current, version, _state(run, version["version_id"]))
    return windows + ([current] if current else [])


def _advance(
    windows: list[Window], current: Window | None, version: dict[str, Any], state: dict[str, Any]
) -> Window | None:
    """Uma versão: estende a janela aberta, fecha-a em `windows`, ou segue íntegra."""
    if state.get("bypass_actors") or gate_problems(state):
        return _grow(current, version, state)
    if current is not None:
        windows.append(replace(current, closed=_ts(version["updated_at"])))
    return None


def _window_facts(window: Window, now: datetime) -> list[str]:
    """Contagem e versão, nunca ator, tipo ou `bypass_mode`: a API esconde
    `bypass_actors` de quem não administra, e a issue é pública."""
    fim = _iso(window.closed) if window.closed else "ainda aberta"
    fora = [f"`bypass_actors` com {window.bypass_count} entrada(s)"] if window.bypass_count else []
    return [
        f"- **Janela:** versão {window.version_id} do `history`, de "
        f"{_iso(window.opened)} até {fim} ({window.duration(now).total_seconds():.1f} s)",
        f"- **Fora do estado:** {'; '.join(fora + list(window.problems))}",
        f"- **Tolerância:** {int(BREAK_GLASS_TOLERANCE.total_seconds() // 60)} min, só "
        "para concessão de bypass (ADR-448 D2); gate enfraquecido não tem janela (D3).",
    ]


def _window_issue(window: Window, now: datetime) -> tuple[str, str]:
    body = "\n".join(
        [
            marker("ruleset-window", str(window.version_id)),
            f"O Ruleset `main-protection` (id {RULESET_ID}) ficou fora do estado da ADR-448.",
            "",
            *_window_facts(window, now),
            "",
            TRIAGE,
            "",
            "_Aberta por `dev/ci_audit_merge_protection.py --sweep` (ADR-448)._",
        ]
    )
    return f"CI: Ruleset main-protection fora da ADR-448 na versão {window.version_id}", body


def _needs_alarm(window: Window, now: datetime) -> bool:
    return bool(window.problems) or window.duration(now) > BREAK_GLASS_TOLERANCE


def _report_window(run: Runner, window: Window, now: datetime, dry_run: bool) -> None:
    segundos = window.duration(now).total_seconds()
    if not _needs_alarm(window, now):
        print(
            f"ruleset: break-glass na versão {window.version_id}, {segundos:.1f} s — dentro da tolerância"
        )
        return
    print(f"ALARME: ruleset fora da ADR-448 na versão {window.version_id} ({segundos:.0f} s)")
    key, issue = f"ruleset-window={window.version_id}", _window_issue(window, now)
    if window.closed is None:
        raise_live_alarm(run, key, issue, dry_run)
    elif key in registry(run):
        print("janela já registrada — nenhuma issue nova")
    else:
        open_issue(run, *issue, dry_run)


def check_ruleset(run: Runner, now: datetime, dry_run: bool) -> str | None:
    """Braço com admin do sweep. Devolve o motivo de NÃO ter medido, ou None:
    sem `bypass_actors` na resposta não há estado do ruleset a afirmar."""
    try:
        ruleset = read_ruleset(run)
        if ruleset is None:
            raise_live_alarm(run, MISSING_KEY, _missing_issue(), dry_run)
            return None
        if ruleset.get("bypass_actors") is None:
            return NOT_VISIBLE
        windows = breach_windows(run)
    except RuntimeError as exc:
        return str(exc)
    for window in windows:
        _report_window(run, window, now, dry_run)
    if not windows:
        print("ruleset: nenhuma janela fora da ADR-448 desde a aplicação dela")
    return None
