"""Alerta do Dependabot com conserto, sem PR e além do SLO (issue `security-slo-breach`).

O incidente que motiva: o alerta #130 (GHSA-hq66-cqwq-w95j, `pdfjs-dist`, HIGH) ficou
aberto de 2026-08-07 a 2026-10-09, 63 dias contra o SLO de 14. O conserto exigia major
do pai, o Dependabot nunca abriu PR, e nada no repositório avisou. Em 2026-10-09 os 3
alertas abertos não têm versão corrigida, então o canal está em 0 disparos e a prova é
por mutação: alerta sintético acima do SLO dispara, o controle sem conserto não."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

from dev import ci_dependabot_alert_slo as mod
from dev import ci_dependabot_health as health
from dev.ci_advance_automerge_train import GhCallFailed

LABEL = "security-slo-breach"
REPO = "davidrobert/mathoms"
ROOT = Path(__file__).resolve().parents[2]
DIRS = {"npm_and_yarn": {"/frontend", "/frontend-ops"}, "go_modules": {"/services/x-go"}}


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _raw_alert(number: int = 130, **over) -> dict:
    """Campos reais do #130, já na projeção que o `--jq` de `fetch_alerts` devolve."""
    raw = {
        "number": number,
        "html_url": f"https://github.com/{REPO}/security/dependabot/{number}",
        "created_at": "2026-08-07T10:27:39Z",
        "manifest": "frontend/package-lock.json",
        "ecosystem": "npm",
        "package": "pdfjs-dist",
        "severity": "high",
        "advisory_updated_at": "2026-08-06T21:12:27Z",
        "patched": "6.2.108",
    }
    return {**raw, **over}


def _alert(**over) -> mod.DependabotAlert:
    return mod.parse_alert(_raw_alert(**over))


def _raw_pr(number: int, branch: str, *deps: str) -> dict:
    meta = "".join(f"- dependency-name: {d}\n  dependency-type: indirect\n" for d in deps)
    message = f"Bumps x.\n\n---\nupdated-dependencies:\n{meta}...\n\nSigned-off-by: dependabot"
    return {
        "number": number,
        "url": f"https://github.com/{REPO}/pull/{number}",
        "headRefName": f"dependabot/{branch}",
        "commits": {"nodes": [{"commit": {"message": message}}]},
    }


def _pr(number: int, branch: str, *deps: str) -> mod.OpenUpdate:
    return mod.parse_update(_raw_pr(number, branch, *deps), DIRS)


# ── Predicado: a mutação que prova o canal ───────────────────────────────────────
def test_aceite_alerta_sintetico_high_alem_do_slo_sem_pr_dispara():
    verdict = mod.judge(_alert(), [], _ts("2026-09-01T02:00:00Z"))
    assert verdict.breach and verdict.reason == "venceu em 2026-08-21"


def test_aceite_controle_sem_versao_corrigida_nao_dispara_nem_com_63_dias():
    """O estado real de 2026-10-09: #137/#154 (`extract-zip`, HIGH) sem `first_patched_version`."""
    verdict = mod.judge(_alert(patched=None), [], _ts("2026-10-09T02:00:00Z"))
    assert not verdict.breach and verdict.reason == "sem versão corrigida publicada"


def test_contrafactual_130_real_dispara_no_cron_de_08_22_e_nao_no_de_08_21():
    """Prazo 08-21T10:27: o cron das 02:00 do dia 21 ainda está dentro do SLO."""
    alert = _alert()
    assert not mod.judge(alert, [], _ts("2026-08-21T02:00:00Z")).breach
    assert mod.judge(alert, [], _ts("2026-08-22T02:00:00Z")).breach


@pytest.mark.parametrize(
    ("severity", "age", "breach"),
    [
        ("critical", timedelta(hours=71), False),
        ("critical", timedelta(hours=73), True),
        ("high", timedelta(days=14) - timedelta(hours=1), False),
        ("high", timedelta(days=14) + timedelta(hours=1), True),
        ("medium", timedelta(days=400), False),
        ("low", timedelta(days=400), False),
    ],
)
def test_slo_sai_da_severidade_do_runbook(severity, age, breach):
    alert = _alert(severity=severity, advisory_updated_at="2026-01-01T00:00:00Z")
    assert mod.judge(alert, [], alert.created_at + age).breach is breach


@pytest.mark.parametrize(("hours", "breach"), [(23, False), (25, True)])
def test_carencia_de_24h_do_advisory_adia_o_disparo_sem_reiniciar_o_relogio(hours, breach):
    """Fix publicado hoje para alerta velho: o Dependabot tem 24h para abrir o PR."""
    now = _ts("2026-10-01T02:00:00Z")
    alert = _alert(advisory_updated_at=(now - timedelta(hours=hours)).isoformat())
    verdict = mod.judge(alert, [], now)
    assert verdict.breach is breach
    assert breach or "menos de 24h" in verdict.reason


def test_runbook_declara_o_mesmo_slo_que_o_codigo():
    text = (ROOT / mod.RUNBOOK).read_text(encoding="utf-8")
    assert "| CRITICAL | ≤ 72h corridas |" in text and "| HIGH | ≤ 14 dias corridos |" in text
    assert mod.SLO == {"critical": timedelta(hours=72), "high": timedelta(days=14)}


# ── PR do Dependabot: pacote do metadata, diretório da branch ────────────────────
def test_pr_do_dependabot_do_pacote_no_mesmo_diretorio_silencia():
    """Major do pai + transitiva: o metadata lista as duas, e casar pela transitiva basta."""
    pr = _pr(2165, "npm_and_yarn/frontend/pdf-to-png-converter-4.0.0", "pdf-to-png-converter", "pdfjs-dist")  # fmt: skip
    verdict = mod.judge(_alert(), [pr], _ts("2026-09-01T02:00:00Z"))
    assert not verdict.breach and verdict.reason == "PR #2165 do Dependabot aberto"


def test_contrafactual_158_next_critical_silenciado_pelo_2003_e_nao_pelo_2057():
    """Real: o #2057 trocou o `next` em `/frontend-ops`; o #158 era de `/frontend`."""
    alert = _alert(number=158, package="next", severity="critical", patched="16.3.3",
                   created_at="2026-09-10T02:16:04Z", advisory_updated_at="2026-09-08T21:21:13Z")  # fmt: skip
    ops = _pr(2057, "npm_and_yarn/frontend-ops/npm_and_yarn-a93a89a6b5", "next", "sharp")
    group = _pr(2003, "npm_and_yarn/frontend/next-and-react-42e237accf", "next", "react")
    now = _ts("2026-10-08T02:00:00Z")
    assert mod.judge(alert, [ops], now).breach
    assert mod.judge(alert, [ops, group], now).reason == "PR #2003 do Dependabot aberto"


def test_pr_de_outro_pacote_nao_silencia():
    pr = _pr(2232, "npm_and_yarn/frontend/eslint-core-4c219eb705", '"@eslint/js"', "eslint")
    assert mod.judge(_alert(), [pr], _ts("2026-09-01T02:00:00Z")).breach


def test_metadata_com_aspas_yaml_e_grupo_de_frontend_ops_resolvem():
    """Medido em 2026-10-09 (#2230): pacote com escopo vem entre aspas no metadata."""
    pr = _pr(2230, "npm_and_yarn/frontend-ops/ops-eslint-core-4c219eb705", '"@eslint/js"', "eslint")  # fmt: skip
    assert (pr.ecosystem, pr.directory, pr.packages) == (
        "npm_and_yarn", "/frontend-ops", frozenset({"@eslint/js", "eslint"}),
    )  # fmt: skip


def test_security_update_de_go_sem_entrada_no_yml_resolve_pelo_diretorio_do_alerta():
    alert = _alert(
        ecosystem="go", manifest="services/x-go/go.mod", package="google.golang.org/grpc"
    )
    dirs = {"go_modules": {alert.directory}}
    raw = _raw_pr(2020, "go_modules/services/x-go/go_modules-864e87b884", "google.golang.org/grpc")
    assert mod.parse_update(raw, dirs).covers(alert)


@pytest.mark.parametrize(
    ("manifest", "directory"),
    [("frontend/package-lock.json", "/frontend"), ("requirements.in", "/"),
     ("services/pipeline-service-go/go.mod", "/services/pipeline-service-go")],
)  # fmt: skip
def test_diretorio_sai_do_manifest_path(manifest, directory):
    assert mod.manifest_directory(manifest) == directory


def test_ecossistema_do_alerta_vira_o_nome_da_branch_que_o_health_ja_mede():
    assert set(mod.BRANCH_ECOSYSTEM.values()) <= set(health.TITLE_ECOSYSTEM.values())


def test_diretorios_do_yml_real_entram_na_resolucao_da_branch():
    """Sem o yml, PR de `/frontend-ops` cairia na raiz e casaria alerta de `/`."""
    dirs = mod.branch_directories([_alert()])
    assert {"/frontend", "/frontend-ops"} <= dirs["npm_and_yarn"]


# ── Issue: espelha o estado; fechar à mão é soneca até o próximo cron ────────────
class FakeGh:
    """Responde por subcomando, sem rede; `closed_by` é o login de quem fechou."""

    def __init__(self, alerts=(), prs=(), issues=(), closed_by=mod.BOT_LOGIN, total=None):
        self.calls: list[tuple[str, ...]] = []
        self.alerts, self.prs, self.issues = list(alerts), list(prs), list(issues)
        self.closed_by, self.total = closed_by, total

    def __call__(self, *args: str) -> str:
        self.calls.append(args)
        if args[:2] == ("api", "--paginate"):
            return "".join(json.dumps(a) + "\n" for a in self.alerts)
        if args[:2] == ("api", "graphql"):
            count = len(self.prs) if self.total is None else self.total
            return json.dumps({"data": {"search": {"issueCount": count, "nodes": self.prs}}})
        if args[0] == "api":
            return f"{self.closed_by}\n"
        return json.dumps(self.issues) if args[:2] == ("issue", "list") else ""

    def verbs(self) -> list[str]:
        return [" ".join(c[:2]) for c in self.calls if c[0] in ("issue", "label")]

    def body(self) -> str:
        last = next(c for c in reversed(self.calls) if "--body" in c)
        return last[last.index("--body") + 1]


NOW = _ts("2026-09-01T02:00:00Z")
BREACH = [mod.judge(_alert(), [], NOW)]
CLOSED = {"number": 9, "state": "CLOSED", "body": "", "closedAt": "2026-08-30T12:00:00Z"}


def _sync(monkeypatch, gh: FakeGh, breaches=BREACH, blind=(), issues=()) -> str:
    monkeypatch.setattr(mod, "_gh", gh)
    return mod.sync_issue(
        list(breaches), list(blind), list(issues), label=LABEL, repo=REPO, dry_run=False
    )


def test_sem_issue_abre_uma_rotulada_com_o_alerta_e_a_saida_auditavel(monkeypatch):
    gh = FakeGh()
    assert _sync(monkeypatch, gh) == "cria"
    assert gh.verbs() == ["label create", "issue create"]
    create = gh.calls[-1]
    assert create[create.index("--label") + 1] == LABEL
    body = gh.body()
    assert "| [#130](" in body and "`pdfjs-dist` | `/frontend` | `6.2.108`" in body
    assert "*Dismiss* do alerta" in body and "requirements.lock" in body


def test_fechada_a_mao_com_violacao_viva_reabre_a_mesma_issue(monkeypatch):
    """Issue nova zeraria o createdAt e o `S3` mediria a soneca, não a violação."""
    gh = FakeGh(closed_by="davidrobert")
    assert _sync(monkeypatch, gh, issues=[CLOSED]) == "reabre"
    assert gh.verbs() == ["issue reopen", "issue edit"]
    assert ("api", f"repos/{REPO}/issues/9", "--jq", ".closed_by.login") in gh.calls


def test_fechada_pelo_bot_e_episodio_novo_issue_nova(monkeypatch):
    gh = FakeGh(closed_by=mod.BOT_LOGIN)
    assert _sync(monkeypatch, gh, issues=[CLOSED]) == "cria"


def test_reabre_a_fechada_mais_recente(monkeypatch):
    older = {**CLOSED, "number": 3, "closedAt": "2026-08-01T00:00:00Z"}
    gh = FakeGh(closed_by="davidrobert")
    _sync(monkeypatch, gh, issues=[older, CLOSED])
    assert gh.calls[-2][:3] == ("issue", "reopen", "9")


def test_issue_aberta_fecha_quando_zera_e_diz_o_que_zerou(monkeypatch):
    open_ = {"number": 7, "state": "OPEN", "body": mod.issue_body(BREACH, []), "closedAt": None}
    gh = FakeGh()
    assert _sync(monkeypatch, gh, breaches=[], issues=[open_]) == "fecha"
    close = gh.calls[-1]
    assert close[close.index("--comment") + 1] == (
        "Zerou: #130 (`pdfjs-dist`). Nenhum alerta com conserto além do SLO sem PR."
    )


def test_corpo_igual_nao_reedita_e_sem_violacao_nem_issue_nao_faz_nada(monkeypatch):
    open_ = {"number": 7, "state": "OPEN", "body": mod.issue_body(BREACH, []), "closedAt": None}
    assert _sync(monkeypatch, FakeGh(), issues=[open_]) == "mantém"
    assert _sync(monkeypatch, FakeGh(), breaches=[], issues=[CLOSED]) == "nada"


def test_dry_run_decide_mas_nao_age(monkeypatch):
    gh = FakeGh()
    monkeypatch.setattr(mod, "_gh", gh)
    action = mod.sync_issue(BREACH, [], [], label=LABEL, repo=REPO, dry_run=True)
    assert action == "cria" and gh.verbs() == []


# ── Instrumento: cego determinístico vira linha; indisponível vira warning ───────
def _run(monkeypatch, gh: FakeGh) -> None:
    monkeypatch.setattr(mod, "_gh", gh)
    monkeypatch.setattr(mod, "load_entries", lambda: [])
    monkeypatch.setenv("GH_REPO", REPO)
    mod.check_alert_slo(LABEL, dry_run=False)


def test_ponta_a_ponta_alerta_vencido_sem_pr_abre_issue(monkeypatch, capsys):
    gh = FakeGh(alerts=[_raw_alert(), _raw_alert(154, package="extract-zip", patched=None)])
    _run(monkeypatch, gh)
    out = capsys.readouterr().out
    assert gh.verbs()[-1] == "issue create" and "[#130](" in gh.body()
    assert "[#154](" not in gh.body()
    assert "#154 high `extract-zip` /frontend → sem versão corrigida publicada" in out


def test_ponta_a_ponta_pr_aberto_do_pacote_nao_abre_issue(monkeypatch):
    pr = _raw_pr(2165, "npm_and_yarn/frontend/pdf-to-png-converter-4.0.0", "pdfjs-dist")
    gh = FakeGh(alerts=[_raw_alert()], prs=[pr])
    _run(monkeypatch, gh)
    assert gh.verbs() == ["issue list"]


@pytest.mark.parametrize(
    "stderr",
    ["HTTP 403: Resource not accessible by integration",
     "HTTP 403: Dependabot alerts are disabled for this repository."],
)  # fmt: skip
def test_alertas_sem_leitura_viram_linha_sem_medicao_nunca_pass(monkeypatch, stderr):
    """Token sem `vulnerability-alerts: read` é canal de segurança cego: tem que aparecer."""

    class Denied(FakeGh):
        def __call__(self, *args: str) -> str:
            if args[:2] == ("api", "--paginate"):
                self.calls.append(args)
                raise GhCallFailed(1, stderr)
            return super().__call__(*args)

    gh = Denied()
    _run(monkeypatch, gh)
    assert gh.verbs()[-1] == "issue create"
    assert "## Sem medição" in gh.body() and "HTTP 403" in gh.body()


def test_lista_de_prs_cortada_nao_silencia_alerta_vencido(monkeypatch):
    gh = FakeGh(alerts=[_raw_alert()], prs=[], total=150)
    _run(monkeypatch, gh)
    body = gh.body()
    assert "venceu em 2026-08-21; PRs sem medição" in body
    assert "lista de PRs cortada: 0 de 150" in body


@pytest.mark.parametrize(
    "falha", [GhCallFailed(1, "HTTP 502: Bad Gateway"), TypeError("shape"), KeyError("x")]
)
def test_indisponibilidade_vira_warning_e_nunca_levanta(monkeypatch, capsys, falha):
    """Run vermelho dispararia o canal de falha do budget-alert por defeito do instrumento."""

    def quebra(*_args: str) -> str:
        raise falha

    monkeypatch.setattr(mod, "_gh", quebra)
    monkeypatch.setenv("GH_REPO", REPO)
    mod.check_alert_slo(LABEL, dry_run=False)
    assert "::warning title=dependabot-alert-slo sem medição::" in capsys.readouterr().out


# ── Amarração com o workflow e o manifesto ───────────────────────────────────────
def _budget_job() -> dict:
    workflow = yaml.safe_load((ROOT / ".github/workflows/budget-alert.yml").read_text())
    return workflow["jobs"]["check-budget"]


def test_job_do_cron_le_alertas_e_roda_o_canal_com_o_label_do_manifesto():
    job = _budget_job()
    assert job["permissions"]["vulnerability-alerts"] == "read"
    step = next(s for s in job["steps"] if "ci_dependabot_alert_slo.py" in s.get("run", ""))
    assert f"--label {LABEL}" in step["run"] and step["if"] == "${{ !cancelled() }}"


def test_label_tem_s3_de_7_dias_no_manifesto():
    manifest = yaml.safe_load((ROOT / ".github/scheduled-workflows.yml").read_text())
    entry = next(w for w in manifest["workflows"] if w["file"] == "budget-alert.yml")
    alerts = {a["label"]: a.get("max_issue_age_days") for a in entry["alerts"]}
    assert alerts[LABEL] == 7
