"""Aviso antecipado de expiração do AUTOUPDATE_PAT (ADR-322 §Emenda 2026-10-08).

O incidente que motiva: o PAT expirou em 2026-10-07 sem aviso no repo; o 401
derrubou trem e watchdog e, pelo `S3` de 3 dias do `ops-train`, travaria o `Lint`
de todo PR em 10-10. A data de expiração era conhecível 90 dias antes."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from dev import ci_pat_expiry as mod
from dev.ci_advance_automerge_train import GhCallFailed

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
HEADERS = (
    "HTTP/2.0 200 OK\r\n"
    "Content-Type: application/json; charset=utf-8\r\n"
    "Github-Authentication-Token-Expiration: 2027-01-06 12:00:00 UTC\r\n"
    "\r\n"
    '{"name": "mathoms", "note": "x: y"}'
)


class FakeGh:
    """Registra as chamadas `gh` e responde por subcomando — sem rede."""

    def __init__(self, api: str = HEADERS, issues: str = "[]") -> None:
        self.calls: list[tuple[str, ...]] = []
        self.api, self.issues = api, issues

    def __call__(self, *args: str) -> str:
        self.calls.append(args)
        if args[0] == "api":
            return self.api
        return self.issues if args[:2] == ("issue", "list") else ""

    def verbs(self) -> list[str]:
        return [" ".join(c[:2]) for c in self.calls]


@pytest.fixture
def com_pat(monkeypatch):
    monkeypatch.setenv("AUTOMERGE_KICK", "1")
    monkeypatch.setenv("GH_REPO", "davidrobert/mathoms")


def test_header_e_lido_case_insensitive_e_so_no_bloco_de_cabecalhos():
    assert mod.expiration_header(HEADERS) == "2027-01-06 12:00:00 UTC"
    assert mod.expiration_header("HTTP/2.0 200 OK\n\n{}") is None


def test_formas_observadas_viram_utc_inclusive_no_fuso():
    """Fine-grained vem no fuso do dono; aware se compara por instante, então o
    `==` sozinho passava com o offset ainda em -03:00 e o aviso rotulava hora local."""
    utc = mod.parse_expiration("2027-01-06 12:00:00 UTC")
    offset = mod.parse_expiration("2027-01-06 09:00:00 -0300")
    assert utc == offset == datetime(2027, 1, 6, 12, 0, tzinfo=timezone.utc)
    assert offset.utcoffset() == timedelta(0)


def test_aviso_mostra_o_instante_em_utc_nao_a_hora_local():
    expira = mod.parse_expiration("2026-10-20 22:47:00 -0300")
    texto = mod.expiry_warning(expira, datetime(2026, 10, 9, 2, 0, tzinfo=timezone.utc))
    assert "2026-10-21 01:47 UTC" in texto


def test_formato_desconhecido_falha_nomeando_o_valor():
    with pytest.raises(ValueError, match="2027-01-06T12:00:00Z"):
        mod.parse_expiration("2027-01-06T12:00:00Z")


@pytest.mark.parametrize(
    ("dias", "avisa"), [(15, False), (14, True), (1, True), (0, True), (-1, True)]
)
def test_limiar_de_aviso_e_t_menos_14(dias, avisa):
    assert (mod.expiry_warning(NOW + timedelta(days=dias, hours=1), NOW) is not None) is avisa


def test_sem_header_e_aviso_nao_folga():
    """Header ausente = token sem expiração, que viola a D2 — não é 'tudo certo'."""
    assert "não tem expiração" in mod.expiry_warning(None, NOW)


def test_expirado_diz_expirou():
    assert "expirou" in mod.expiry_warning(NOW - timedelta(hours=2), NOW)


def test_url_de_rotacao_carrega_as_permissoes_da_d2_e_nao_workflows():
    url = mod.rotation_url(NOW)
    for perm in ("contents=write", "pull_requests=write", "issues=write", "actions=read"):
        assert perm in url
    assert "workflows" not in url
    assert "expires_in=90" in url


def test_sem_pat_explicito_nao_mede(monkeypatch):
    """O fallback GITHUB_TOKEN vive ~1h: medir com ele abriria falso alarme."""
    monkeypatch.setenv("AUTOMERGE_KICK", "0")
    gh = FakeGh()
    monkeypatch.setattr(mod, "_gh", gh)
    mod.check_pat_expiry("ops-pat-expiry", dry_run=False)
    assert gh.calls == []


def test_folga_fecha_a_issue_aberta(monkeypatch, com_pat):
    gh = FakeGh(issues='[{"number": 7, "body": "x"}]')
    monkeypatch.setattr(mod, "_gh", gh)
    mod.check_pat_expiry("ops-pat-expiry", dry_run=False)
    assert gh.verbs()[-1] == "issue close"


def test_perto_de_expirar_abre_uma_issue_rotulada(monkeypatch, com_pat):
    perto = HEADERS.replace(
        "2027-01-06", (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
    )
    gh = FakeGh(api=perto)
    monkeypatch.setattr(mod, "_gh", gh)
    mod.check_pat_expiry("ops-pat-expiry", dry_run=False)
    create = gh.calls[-1]
    assert create[:2] == ("issue", "create")
    assert create[create.index("--label") + 1] == "ops-pat-expiry"


def test_corpo_igual_nao_reedita(monkeypatch):
    body = mod.issue_body("o PAT expira em **5 dia(s)**", NOW)
    gh = FakeGh(issues=json.dumps([{"number": 7, "body": body}]))
    monkeypatch.setattr(mod, "_gh", gh)
    mod.sync_issue("o PAT expira em **5 dia(s)**", NOW, "ops-pat-expiry", dry_run=False)
    assert gh.verbs() == ["issue list"]


def test_falha_da_medicao_vira_warning_e_nunca_levanta(monkeypatch, com_pat, capsys):
    """Run vermelho aqui abriria `ops-train` e o S3 travaria merges por defeito do instrumento."""

    def quebra(*_args: str) -> str:
        raise GhCallFailed(1, "HTTP 502: Bad Gateway")

    monkeypatch.setattr(mod, "_gh", quebra)
    mod.check_pat_expiry("ops-pat-expiry", dry_run=False)
    assert "::warning title=pat-expiry sem medição::" in capsys.readouterr().out


def test_401_no_watchdog_continua_vermelho_e_aponta_o_runbook(monkeypatch, capsys):
    """O canal de falha precisa do run vermelho; o que muda é a mensagem."""
    from dev import ci_automerge_watchdog as watchdog

    def expirado() -> list:
        raise GhCallFailed(1, "HTTP 401: Bad credentials (https://api.github.com/graphql)")

    monkeypatch.setattr(watchdog, "list_watchdog_prs", expirado)
    with pytest.raises(GhCallFailed):
        watchdog._list_prs_explaining_401()
    assert "runbooks/automerge_train.md §2" in capsys.readouterr().out


def test_leitura_incoerente_com_200_vira_warning_sem_issue(monkeypatch, com_pat, capsys):
    """HTTP 200 prova token válido agora; vencimento a <1h é bug de leitura (GitHub,
    ago–set/2025: agora+1min) e abriria '0 dia(s)' que rotacionar não fecha."""
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    gh = FakeGh(api=HEADERS.replace("2027-01-06 12:00:00 UTC", agora))
    monkeypatch.setattr(mod, "_gh", gh)
    mod.check_pat_expiry("ops-pat-expiry", dry_run=False)
    assert not any(c[0] == "issue" for c in gh.calls)
    assert "leitura incoerente" in capsys.readouterr().out
