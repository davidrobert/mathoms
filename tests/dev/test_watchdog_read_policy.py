"""Política de leitura do watchdog de agendados (ADR-210 §Adendo 2026-08-21c):
sem retry, uma chamada por família, orçamento de wall-clock — e todo caminho de
"não li" caindo em GH, nunca em pass nem em sinal fabricado."""

from __future__ import annotations

import json
import subprocess
from datetime import date

import pytest

from dev import check_scheduled_workflows as mod

REF = date(2026, 8, 21)
FRESCO = "2026-08-21T00:00:00Z"
ENTRY = {"file": "qualquer-agendado.yml", "max_age_days": 2}
# As duas classes medidas em 2026-08-17 nos logs do trem, que lê a mesma API no
# mesmo CI: 5×503 (transitório) e 5×403 (determinístico). O retry de 5s que já
# existia ali recuperou 0 de 10 — é a medição que rejeitou o retry aqui.
TRANSITORIO = "HTTP 503: No server is currently available to service your request."
DETERMINISTICO = "HTTP 403: Resource not accessible by personal access token"


def _install_gh(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """`_run` fake sobre o manifesto real — o caminho feliz completo, sem rede."""
    chamadas: list[list[str]] = []
    arquivos = [e["file"] for e in mod.load_manifest()]
    listados = [{"path": f".github/workflows/{f}", "state": "active"} for f in arquivos]

    def _fake(cmd: list[str], timeout: float):
        chamadas.append(cmd)
        junto = " ".join(cmd)
        if "actions/workflows?per_page" in junto:
            return json.dumps({"total_count": len(listados), "workflows": listados})
        if "issue" in cmd:
            return json.dumps([])
        if "/runs?" in junto:
            return json.dumps({"workflow_runs": [{"run_started_at": FRESCO}]})
        raise AssertionError(f"chamada inesperada: {junto}")

    monkeypatch.setattr(mod, "_run", _fake)
    return chamadas


def test_leitura_falha_nao_e_re_tentada(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem retry é decisão medida, não omissão: em 08-17 a segunda tentativa
    devolveu o mesmo 503, e 403 de permissão não muda por re-tentar."""
    tentativas: list[list[str]] = []

    def _fake(cmd, capture_output, text, timeout):
        tentativas.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, "", TRANSITORIO)

    monkeypatch.setattr(mod.subprocess, "run", _fake)
    falha = mod._run(["gh", "api", "x"], 10.0)
    assert isinstance(falha, mod.GhFailure)
    assert len(tentativas) == 1


@pytest.mark.parametrize("stderr,status", [(TRANSITORIO, 503), (DETERMINISTICO, 403)])
def test_gh_cita_a_causa_em_vez_de_palpitar(monkeypatch, stderr: str, status: int) -> None:
    """A mensagem anterior afirmava "cheque permissions" — errada em 7 de 7. O
    que separa "re-rode" de "não adianta re-rodar" é o status, então ele vai junto."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    (violacao,) = mod._unreachable(ENTRY, "state dos workflows", mod.GhFailure(1, stderr))
    assert violacao.signal == "GH"
    assert str(status) in violacao.detail


def test_leitura_e_por_familia_nao_por_entrada(monkeypatch: pytest.MonkeyPatch) -> None:
    """9 entradas custavam 23 chamadas (state e Issues por entrada). Cada chamada
    é uma exposição a 5xx, e a superfície era o multiplicador do falso vermelho."""
    chamadas = _install_gh(monkeypatch)
    reader = mod.Reader.for_repo("o/r")
    violacoes = mod.collect(reader, REF)
    assert len(mod.load_manifest()) == 9
    assert reader.calls == len(chamadas) == 11
    assert [v.signal for v in violacoes if v.signal == "GH"] == []


def test_pagina_cheia_de_issues_vira_gh_e_nao_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """`gh issue list` ordena newest-first e o S3 caça a MAIS VELHA: truncar
    descartaria exatamente o que o sinal existe para pegar. Fail-open por
    inversão de polaridade é pior que o falso vermelho que o batch economiza."""
    reader = mod.Reader("o/r")
    cheia = [
        {"number": n, "title": "x", "createdAt": FRESCO, "labels": []} for n in range(mod.PAGE_SIZE)
    ]
    monkeypatch.setattr(reader, "json", lambda _args: cheia)
    assert isinstance(mod.read_open_issues(reader), mod.GhFailure)


def test_lista_de_workflows_truncada_vira_gh(monkeypatch: pytest.MonkeyPatch) -> None:
    """`total_count` acima da página é veredito parcial — e parcial não é veredito."""
    reader = mod.Reader("o/r")
    parcial = {
        "total_count": 120,
        "workflows": [{"path": ".github/workflows/a.yml", "state": "active"}],
    }
    monkeypatch.setattr(reader, "json", lambda _args: parcial)
    assert isinstance(mod.read_workflow_states(reader), mod.GhFailure)


def test_orcamento_estourado_vira_gh_e_nao_tenta_ler(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem teto, N chamadas × timeout matam o `lint-all` por timeout-minutes, e
    job *cancelled* não nomeia causa nem desbloqueio. Estourar bloqueia igual —
    com mensagem — em vez de pular entrada não medida."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("MATHOMS_PR_LABELS", raising=False)

    def _proibido(cmd, timeout):
        raise AssertionError("orçamento esgotado não pode tentar ler")

    monkeypatch.setattr(mod, "_run", _proibido)
    reader = mod.Reader("o/r", budget_s=-1.0)
    violacoes = mod.collect(reader, REF)
    assert reader.calls == 0
    assert {v.signal for v in violacoes if not v.waived} == {"GH"}
    assert mod._gate(violacoes, reader) == 1


def test_reader_sem_leitura_batch_nao_fabrica_veredito(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reader construído sem `for_repo` não tem dado — "não li" cai em GH, e
    jamais num S1 inventado ou num pass."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert [v.signal for v in mod._check_state(mod.Reader("o/r"), ENTRY)] == ["GH"]
