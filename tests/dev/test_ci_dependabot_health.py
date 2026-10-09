"""Saúde das entradas do Dependabot (issue `ops-dependabot-red`).

O incidente que motiva: a entrada pip `/` saiu `failure` em 08-31, 09-07, 10-05 e
10-09 (redis×kombu no pip 26 do updater, #2124), e pip `/backend` e
github_actions `/` passaram de 07-28 a 10-09 sem nenhuma run agendada. Nada no
repositório viu: o workflow dinâmico do Dependabot não tem canal de falha."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from dev import ci_dependabot_health as mod
from dev.ci_advance_automerge_train import GhCallFailed

LABEL = "ops-dependabot-red"
REPO = "davidrobert/mathoms"
PIP_ROOT = mod.DependabotEntry("pip", "/", "weekly")
PIP_BACKEND = mod.DependabotEntry("pip", "/backend", "weekly")


def _ts(day: str) -> datetime:
    return datetime.fromisoformat(f"{day}T09:17:00+00:00")


def _raw(title: str, day: str, conclusion: str | None, status: str = "completed") -> dict:
    return {
        "created_at": f"{day}T09:17:00Z",
        "status": status,
        "conclusion": conclusion,
        "display_title": title,
        "html_url": f"https://github.com/{REPO}/actions/runs/{day.replace('-', '')}",
    }


# Histórico REAL das runs agendadas (workflow 261301753, `event=dynamic`), medido em
# 2026-10-09 — mais um rebase de PR do mesmo dia, que precisa ser ignorado.
REAL_HISTORY = [
    _raw("pip in /. - Update #1", "2026-08-24", "success"),
    _raw("pip in /. - Update #2", "2026-08-31", "failure"),
    _raw("pip in /. - Update #3", "2026-09-07", "failure"),
    _raw("pip in / for redis - Update #4", "2026-09-07", "success"),
    _raw("pip in /backend - Update #5", "2026-07-28", "cancelled"),
]


def _pr(number: int, branch: str, created: str, closed: str | None = None) -> dict:
    return {
        "number": number,
        "url": f"https://github.com/{REPO}/pull/{number}",
        "headRefName": f"dependabot/{branch}",
        "createdAt": created,
        "closedAt": closed,
        "mergedAt": None,
    }


def _findings(entries, raw_runs, now):
    return mod.measure_findings(entries, mod.scheduled_runs(raw_runs), now)


class FakeGh:
    """Registra as chamadas `gh` e responde por subcomando — sem rede."""

    def __init__(self, runs: list[dict], issues: list[dict] | None = None, prs=None) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.runs, self.issues = runs, issues or []
        young = _pr(1, "pip/x-1.0", datetime.now(timezone.utc).isoformat())
        self.prs = [young] if prs is None else prs

    def __call__(self, *args: str) -> str:
        self.calls.append(args)
        if args[:2] == ("pr", "list"):
            want_open = args[args.index("--state") + 1] == "open"
            return json.dumps([p for p in self.prs if (p["closedAt"] is None) is want_open])
        if args[:2] == ("api", "--paginate"):
            return "".join(json.dumps(r) + "\n" for r in self.runs)
        if args[0] == "api":
            return "261301753\n"
        return json.dumps(self.issues) if args[:2] == ("issue", "list") else ""

    def verbs(self) -> list[str]:
        return [" ".join(c[:2]) for c in self.calls if c[0] != "api"]


@pytest.mark.parametrize(
    ("entry", "key"),
    [
        (PIP_ROOT, "pip in /."),
        (PIP_BACKEND, "pip in /backend"),
        (mod.DependabotEntry("pip", "/backend/", "weekly"), "pip in /backend"),
        (mod.DependabotEntry("npm", "/frontend", "weekly"), "npm_and_yarn in /frontend"),
        (mod.DependabotEntry("github-actions", "/", "weekly"), "github_actions in /."),
        (mod.DependabotEntry("docker", "/frontend-ops", "weekly"), "docker in /frontend-ops"),
    ],
)
def test_titulo_medido_por_ecossistema(entry, key):
    """A raiz vira `/.` e o ecossistema vira o nome interno — medido, não suposto."""
    assert entry.title_key() == key


def test_toda_entrada_do_yml_real_tem_titulo_e_limite_medidos():
    """Ecossistema ou intervalo novo sem medição reprova aqui, antes de virar linha no cron."""
    for entry in mod.load_entries():
        assert entry.title_key() is not None, entry
        assert entry.interval in mod.STALE_LIMIT, entry


def test_rebase_de_pr_e_multi_diretorio_nao_contam_como_run_da_entrada():
    raw = [
        _raw("pip in / for redis - Update #1", "2026-09-07", "failure"),
        _raw("npm_and_yarn in /frontend, /frontend-ops for next - Update #2", "2026-09-07", None),
        _raw("pip in /. - Update #3", "2026-09-07", "success"),
    ]
    assert [r.key for r in mod.scheduled_runs(raw)] == ["pip in /."]


def test_contrafactual_historico_real_dispara_em_09_07():
    """As runs 08-24 s, 08-31 f e 09-07 f já bastavam: o alerta sairia no cron de 09-07."""
    found = _findings([PIP_ROOT], REAL_HISTORY, _ts("2026-09-07") + timedelta(hours=3))
    assert [(f.entry, f.signal) for f in found] == [("pip /", "vermelho")]


def test_contrafactual_falha_isolada_de_08_31_nao_dispara():
    """Uma falha só pode ser instabilidade do registry."""
    found = _findings([PIP_ROOT], REAL_HISTORY[:2], _ts("2026-08-31") + timedelta(hours=3))
    assert found == []


def test_contrafactual_backend_sem_run_desde_07_28():
    found = _findings([PIP_BACKEND], REAL_HISTORY, _ts("2026-09-07"))
    assert [(f.entry, f.signal) for f in found] == [("pip /backend", "sem run")]
    assert "cancelled" in found[0].evidence


@pytest.mark.parametrize(
    ("conclusions", "red"),
    [
        (["failure", "failure"], True),
        (["failure", "success"], False),
        (["failure", "cancelled"], False),
        (["failure"], False),
    ],
)
def test_vermelho_exige_as_duas_ultimas_concluidas_failure(conclusions, red):
    days = ["2026-10-05", "2026-09-28"]
    raw = [
        _raw(f"pip in /. - Update #{i}", d, c) for i, (d, c) in enumerate(zip(days, conclusions))
    ]
    found = _findings([PIP_ROOT], raw, _ts("2026-10-06"))
    assert any(f.signal == "vermelho" for f in found) is red


def test_run_em_andamento_nao_entra_na_janela_do_vermelho():
    raw = [
        _raw("pip in /. - Update #3", "2026-10-05", None, status="in_progress"),
        _raw("pip in /. - Update #2", "2026-09-28", "failure"),
        _raw("pip in /. - Update #1", "2026-09-21", "failure"),
    ]
    assert [f.signal for f in _findings([PIP_ROOT], raw, _ts("2026-10-05"))] == ["vermelho"]


@pytest.mark.parametrize(
    ("interval", "days", "stale"),
    [("daily", 3, False), ("daily", 4, True), ("weekly", 10, False), ("weekly", 11, True),
     ("monthly", 40, False), ("monthly", 41, True)],
)  # fmt: skip
def test_limite_de_sem_run_sai_do_intervalo(interval, days, stale):
    entry = mod.DependabotEntry("pip", "/", interval)
    raw = [_raw("pip in /. - Update #1", "2026-09-01", "success")]
    found = _findings([entry], raw, _ts("2026-09-01") + timedelta(days=days))
    assert any(f.signal == "sem run" for f in found) is stale


def test_entrada_sem_nenhuma_run_vira_linha_nunca_pass():
    entry = mod.DependabotEntry("npm", "/frontend-ops", "weekly")
    found = _findings([entry], REAL_HISTORY, _ts("2026-09-07"))
    assert [f.signal for f in found] == ["sem correspondência"]


@pytest.mark.parametrize(
    "entry",
    [
        mod.DependabotEntry("bundler", "/", "weekly"),
        mod.DependabotEntry("pip", None, "weekly"),
        mod.DependabotEntry("pip", "/", "quarterly"),
    ],
)
def test_ecossistema_diretorio_ou_intervalo_nao_medido_vira_linha(entry):
    """Intervalo sem limite ainda mede o vermelho; a linha extra é o que não pode faltar."""
    found = _findings([entry], REAL_HISTORY, _ts("2026-09-07"))
    assert "sem correspondência" in [f.signal for f in found]


def _red_now():
    now = _ts("2026-09-07") + timedelta(hours=3)
    return _findings([PIP_ROOT], REAL_HISTORY, now), now


def test_sem_issue_abre_uma_rotulada_criando_a_label_antes(monkeypatch):
    findings, now = _red_now()
    gh = FakeGh([])
    monkeypatch.setattr(mod, "_gh", gh)
    mod.sync_issue(findings, [], now, label=LABEL, repo=REPO, dry_run=False)
    assert gh.verbs() == ["label create", "issue create"]
    create = gh.calls[-1]
    assert create[create.index("--label") + 1] == LABEL


def test_fechamento_manual_e_triagem_falha_anterior_nao_reabre(monkeypatch):
    """Sem isto o fechamento esperaria a próxima run passar, e o `S3` reprova o Lint
    do próprio PR do conserto — o impasse de 2026-10-08."""
    findings, now = _red_now()
    closed = [{"number": 9, "state": "CLOSED", "body": "", "closedAt": "2026-09-07T11:00:00Z"}]
    gh = FakeGh([])
    monkeypatch.setattr(mod, "_gh", gh)
    mod.sync_issue(findings, closed, now, label=LABEL, repo=REPO, dry_run=False)
    assert gh.verbs() == []


def test_failure_depois_do_fechamento_abre_issue_nova_nunca_reopen(monkeypatch):
    """`reopen` herdaria o createdAt velho e o `S3` reprovaria todo PR na hora."""
    findings, now = _red_now()
    closed = [{"number": 9, "state": "CLOSED", "body": "", "closedAt": "2026-09-05T00:00:00Z"}]
    gh = FakeGh([])
    monkeypatch.setattr(mod, "_gh", gh)
    mod.sync_issue(findings, closed, now, label=LABEL, repo=REPO, dry_run=False)
    assert gh.verbs() == ["label create", "issue create"]


@pytest.mark.parametrize(("closed_days_ago", "reopens"), [(5, False), (11, True)])
def test_sem_run_triado_so_volta_com_o_limite_vencido_depois_do_fechamento(
    monkeypatch, closed_days_ago, reopens
):
    now = _ts("2026-09-07")
    findings = _findings([PIP_BACKEND], REAL_HISTORY, now)
    closed_at = (now - timedelta(days=closed_days_ago)).isoformat()
    closed = [{"number": 9, "state": "CLOSED", "body": "", "closedAt": closed_at}]
    gh = FakeGh([])
    monkeypatch.setattr(mod, "_gh", gh)
    mod.sync_issue(findings, closed, now, label=LABEL, repo=REPO, dry_run=False)
    assert ("issue create" in gh.verbs()) is reopens


def test_issue_aberta_fecha_quando_tudo_fica_saudavel(monkeypatch):
    gh = FakeGh([])
    monkeypatch.setattr(mod, "_gh", gh)
    open_ = [{"number": 7, "state": "OPEN", "body": "x", "closedAt": None}]
    mod.sync_issue([], open_, _ts("2026-10-09"), label=LABEL, repo=REPO, dry_run=False)
    assert gh.verbs() == ["issue close"]


def test_corpo_igual_nao_reedita_e_diferente_reedita(monkeypatch):
    findings, now = _red_now()
    body = mod.issue_body(findings, REPO)
    for current, expected in ((body, []), ("velho", ["issue edit"])):
        gh = FakeGh([])
        monkeypatch.setattr(mod, "_gh", gh)
        open_ = [{"number": 7, "state": "OPEN", "body": current, "closedAt": None}]
        mod.sync_issue(findings, open_, now, label=LABEL, repo=REPO, dry_run=False)
        assert gh.verbs() == expected


def test_dry_run_nao_age(monkeypatch):
    findings, now = _red_now()
    gh = FakeGh([])
    monkeypatch.setattr(mod, "_gh", gh)
    mod.sync_issue(findings, [], now, label=LABEL, repo=REPO, dry_run=True)
    assert gh.verbs() == []


def test_ponta_a_ponta_le_runs_dinamicas_do_workflow_resolvido(monkeypatch):
    now = datetime.now(timezone.utc)
    day = lambda d: f"{now - timedelta(days=d):%Y-%m-%d}"  # noqa: E731
    runs = [_raw("pip in /. - Update #2", day(1), "failure")]
    runs.append(_raw("pip in /. - Update #1", day(8), "failure"))
    gh = FakeGh(runs)
    monkeypatch.setattr(mod, "_gh", gh)
    monkeypatch.setattr(mod, "load_entries", lambda: [PIP_ROOT])
    monkeypatch.setenv("GH_REPO", REPO)
    mod.check_dependabot_health(LABEL, dry_run=False)
    paginated = next(c for c in gh.calls if c[:2] == ("api", "--paginate"))
    assert "workflows/261301753/runs?event=dynamic" in paginated[2]
    assert gh.verbs()[-1] == "issue create"


def test_zero_runs_e_instrumento_cego_nao_dez_linhas_de_sem_run(monkeypatch, capsys):
    """Token sem leitura do workflow dinâmico devolve lista vazia, não erro."""
    gh = FakeGh([])
    monkeypatch.setattr(mod, "_gh", gh)
    monkeypatch.setenv("GH_REPO", REPO)
    mod.check_dependabot_health(LABEL, dry_run=False)
    assert "::warning title=dependabot-health sem medição::" in capsys.readouterr().out
    assert not any(c[0] == "issue" for c in gh.calls)


@pytest.mark.parametrize(
    "falha",
    [GhCallFailed(1, "HTTP 502: Bad Gateway"), TypeError("shape inesperado"), KeyError("x")],
)
def test_falha_da_medicao_vira_warning_e_nunca_levanta(monkeypatch, capsys, falha):
    """Run vermelho dispararia o canal de falha do budget-alert por defeito do instrumento."""

    def quebra(*_args: str) -> str:
        raise falha

    monkeypatch.setattr(mod, "_gh", quebra)
    monkeypatch.setenv("GH_REPO", REPO)
    mod.check_dependabot_health(LABEL, dry_run=False)
    assert "::warning title=dependabot-health sem medição::" in capsys.readouterr().out


# ── PR parado (co-design sre-devops 2026-10-09) ──────────────────────────────────
NPM_FRONTEND = mod.DependabotEntry("npm", "/frontend", "weekly", 2)
GO_SECURITY = "go_modules/services/pipeline-service-go/go_modules-ab12cd34ef"
NOW = datetime.fromisoformat("2026-10-20T02:00:00+00:00")
TRIAGED = [{"number": 9, "state": "CLOSED", "body": "", "closedAt": "2026-10-08T12:00:00Z"}]


def _stuck(raws: list[dict], entries=(NPM_FRONTEND,), now=NOW) -> list[mod.EntryFinding]:
    return mod.stuck_findings(list(entries), mod.parse_prs(list(entries), raws), now)


def _vite(created: str = "2026-10-01T09:00:00Z") -> dict:
    return _pr(2131, "npm_and_yarn/frontend/vite-8.3.3", created)


def test_vagas_saem_do_open_pull_requests_limit_do_yml_real():
    limits = {(e.ecosystem, e.directory): e.pr_limit for e in mod.load_entries()}
    assert limits[("npm", "/frontend-ops")] == 3
    assert limits[("pip", "/")] == 8


@pytest.mark.parametrize(("age_hours", "stuck"), [(5 * 24 - 1, False), (5 * 24 + 1, True)])
def test_limiar_do_pr_parado_e_5_dias(age_hours, stuck):
    assert bool(_stuck([_vite((NOW - timedelta(hours=age_hours)).isoformat())])) is stuck


def test_pr_parado_vira_linha_da_entrada_com_as_vagas():
    (found,) = _stuck([_vite()])
    assert (found.entry, found.signal) == ("npm /frontend", "PR parado")
    assert "[#2131](" in found.evidence and "desde 2026-10-01" in found.evidence
    assert "1/2 vagas ocupadas" in found.evidence and "lotada" not in found.evidence


def test_entrada_lotada_e_destacada():
    raws = [_vite(), _pr(2132, "npm_and_yarn/frontend/typescript-7.0.2", "2026-10-19T09:00:00Z")]
    (found,) = _stuck(raws)
    assert "**lotada**, 2/2 vagas ocupadas" in found.evidence


def test_pr_sem_entrada_no_yml_tambem_vira_linha_e_nao_conta_como_entrada(capsys):
    """Security update parado (go_modules) é o mais grave, mesmo fora do limite de vagas."""
    prs = mod.parse_prs([NPM_FRONTEND], [_pr(2020, GO_SECURITY, "2026-10-01T00:00:00Z")])
    (found,) = mod.stuck_findings([NPM_FRONTEND], prs, NOW)
    assert found.entry == "go_modules (sem entrada)" and "n/d (só security)" in found.evidence
    mod.report([NPM_FRONTEND], [], prs, [found])
    assert "1/1 entradas saudáveis" in capsys.readouterr().out


def test_aceite_pr_parado_abre_issue_e_nao_toca_no_pr(monkeypatch):
    now = datetime.now(timezone.utc)
    run = _raw(
        "npm_and_yarn in /frontend - Update #1", f"{now - timedelta(days=1):%Y-%m-%d}", "success"
    )
    gh = FakeGh([run], prs=[_vite((now - timedelta(days=6)).isoformat())])
    monkeypatch.setattr(mod, "_gh", gh)
    monkeypatch.setattr(mod, "load_entries", lambda: [NPM_FRONTEND])
    monkeypatch.setenv("GH_REPO", REPO)
    mod.check_dependabot_health(LABEL, dry_run=False)
    assert gh.verbs()[-1] == "issue create"
    assert "#2131" in gh.calls[-1][gh.calls[-1].index("--body") + 1]
    assert [c[:2] for c in gh.calls if c[0] == "pr"] == [("pr", "list"), ("pr", "list")]


@pytest.mark.parametrize(
    ("created", "reopens"), [("2026-10-01T09:00:00Z", False), ("2026-10-10T09:00:00Z", True)]
)
def test_pr_parado_triado_nao_volta_e_pr_cruzando_depois_volta(monkeypatch, created, reopens):
    gh = FakeGh([])
    monkeypatch.setattr(mod, "_gh", gh)
    mod.sync_issue(_stuck([_vite(created)]), TRIAGED, NOW, label=LABEL, repo=REPO, dry_run=False)
    assert ("issue create" in gh.verbs()) is reopens


def test_pr_deixado_aberto_na_triagem_volta_quando_a_entrada_lota(monkeypatch):
    """Na triagem (10-08) sobrava vaga; o PR novo de 10-19 é jovem, mas lota a entrada."""
    raws = [_vite(), _pr(2140, "npm_and_yarn/frontend/sharp-0.36.0", "2026-10-19T09:00:00Z")]
    gh = FakeGh([])
    monkeypatch.setattr(mod, "_gh", gh)
    mod.sync_issue(_stuck(raws), TRIAGED, NOW, label=LABEL, repo=REPO, dry_run=False)
    assert gh.verbs() == ["label create", "issue create"]


def test_issue_aberta_por_outro_sinal_marca_o_pr_ja_triado(monkeypatch):
    red = mod.EntryFinding("pip /", "vermelho", "runs", newest_fact=NOW - timedelta(hours=3))
    gh = FakeGh([])
    monkeypatch.setattr(mod, "_gh", gh)
    mod.sync_issue([red, *_stuck([_vite()])], TRIAGED, NOW, label=LABEL, repo=REPO, dry_run=False)
    rows = [
        r
        for r in gh.calls[-1][gh.calls[-1].index("--body") + 1].splitlines()
        if r.startswith("| `")
    ]
    assert "triado em" not in rows[0] and rows[1].endswith("_(triado em 2026-10-08)_ |")


def test_issue_aberta_fecha_quando_so_restam_triados_e_diz_o_que_zerou(monkeypatch):
    red = mod.EntryFinding("pip /", "vermelho", "runs", newest_fact=NOW - timedelta(hours=3))
    stuck = _stuck([_vite()])
    body = mod.issue_body([red, *stuck], REPO)
    open_ = [{"number": 7, "state": "OPEN", "body": body, "closedAt": None}, *TRIAGED]
    gh = FakeGh([])
    monkeypatch.setattr(mod, "_gh", gh)
    mod.sync_issue(stuck, open_, NOW, label=LABEL, repo=REPO, dry_run=False)
    close = gh.calls[-1]
    assert close[:2] == ("issue", "close")
    assert close[close.index("--comment") + 1] == (
        "Zerou: `pip /` (vermelho). Restam só achados já triados."
    )
