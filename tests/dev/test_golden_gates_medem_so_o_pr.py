"""Os dois gates de golden medem o que o PR escreveu, não a main que ele ainda não tem.

Em `pull_request` o checkout é o merge sintético (`refs/pull/N/merge`): pai 1 é a
main contra a qual o GitHub montou o merge, pai 2 a cabeça do PR. `base.sha` é o
merge-base no último push, então `base.sha..HEAD` arrastava a main inteira desde a
base do PR. Squash de PR que isolou o rebaseline junta golden+produção num commit
só: todo PR atrás da main tomava vermelho por commit alheio. Medido no #2065 (run
37868572346), acusado por `3ff4c12174` — o squash do #2063 — sem ter tocado golden.
O passo do delta tinha a mesma faixa e cobrava do PR o delta que veio da main.

Os testes tiram do `ci.yml` o argv com que o CI chama cada gate: o defeito morava na
costura YAML↔script, e um teste de um lado só não o veria.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from string import Template

import pytest
import yaml

import dev.check_golden_delta_declarado as delta
import dev.check_golden_rebaseline_isolation as isolamento

_CI = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"
_EXPRESSAO_DO_EVENTO = re.compile(r"\$\{\{\s*github\.event\.pull_request\.([\w.]+)\s*\}\}")

_VIEW_MODEL = "backend/tests/snapshots/dogfood_view_model.json"
_MANIFESTO = "tests/fixtures/pipeline_golden/rebaseline_manifest.yaml"
_GOLDEN_DO_PR = "tests/fixtures/pipeline_golden/e3/do_pr-3_reconciled.json"
_PRODUCAO_DA_MAIN = "pipeline/domain/services/da_main.py"
_PRODUCAO_DO_PR = "pipeline/domain/services/do_pr.py"

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "PATH": os.environ["PATH"],
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, env=_GIT_ENV
    ).stdout.strip()


# Campos monetários separados por linhas inertes: a main e o PR rebaselinam campos
# diferentes do mesmo golden, e hunks adjacentes viram conflito no merge.
def _view_model_inicial() -> str:
    campos = {"bruto": 100.0, "_a": "-", "_b": "-", "_c": "-", "liquido": 100.0}
    return json.dumps({"patrimonio": campos}, indent=2) + "\n"


def _waiver(campo: str, antigo: float, novo: float) -> str:
    entrada = {
        "golden": Path(_VIEW_MODEL).name,
        "path": f"patrimonio.{campo}",
        "old_cents": round(antigo * 100),
        "new_cents": round(novo * 100),
        "adr": "ADR-439",
        "rationale": "rebaseline do teste",
        "ref": f"{_PRODUCAO_DA_MAIN}:1",
    }
    return yaml.safe_dump([entrada], sort_keys=False)


@dataclass(frozen=True)
class _Evento:
    """O que o CI recebe: o merge sintético em HEAD e os SHAs do payload."""

    repo: Path
    base_sha: str
    head_sha: str

    def payload(self) -> dict[str, str]:
        return {"base.sha": self.base_sha, "head.sha": self.head_sha}


class _Historico:
    """Main e branch do PR evoluindo em paralelo, até o evento de `pull_request`."""

    def __init__(self, tmp_path: Path) -> None:
        self.repo = tmp_path / "r"
        self.repo.mkdir()
        self._n = 0
        _git(self.repo, "init", "-q", "-b", "main")
        self._commit(
            {_VIEW_MODEL: _view_model_inicial(), _MANIFESTO: "[]\n", _PRODUCAO_DA_MAIN: "v = 0\n"},
            "base",
        )
        _git(self.repo, "branch", "pr")

    def _commit(self, arquivos: dict[str, str], msg: str) -> str:
        for rel, conteudo in arquivos.items():
            alvo = self.repo / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text(conteudo, encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "--no-verify", "-m", msg)
        return _git(self.repo, "rev-parse", "HEAD")

    def _rebaselina(self, campo: str, novo: float) -> tuple[str, float]:
        vm = json.loads((self.repo / _VIEW_MODEL).read_text(encoding="utf-8"))
        antigo = vm["patrimonio"][campo]
        vm["patrimonio"][campo] = novo
        return json.dumps(vm, indent=2) + "\n", antigo

    def _contador(self) -> int:
        self._n += 1
        return self._n

    def squash_de_rebaseline_na_main(self, campo: str, novo: float) -> str:
        """O squash do PR que isolou o rebaseline — golden e produção num commit só."""
        _git(self.repo, "switch", "-q", "main")
        conteudo, antigo = self._rebaselina(campo, novo)
        squash = self._commit(
            {
                _VIEW_MODEL: conteudo,
                _MANIFESTO: _waiver(campo, antigo, novo),
                _PRODUCAO_DA_MAIN: f"v = {self._contador()}\n",
            },
            f"squash: rebaseline de {campo} isolado no PR dele",
        )
        self._commit({_MANIFESTO: "[]\n"}, "closeout: waiver consumido")
        return squash

    def commit_no_pr(self, *, misto: bool) -> str:
        _git(self.repo, "switch", "-q", "pr")
        n = self._contador()
        arquivos = {_PRODUCAO_DO_PR: f"w = {n}\n"}
        if misto:
            arquivos[_GOLDEN_DO_PR] = json.dumps({"n": n}) + "\n"
        return self._commit(arquivos, "misto, escrito no PR" if misto else "produção do PR")

    def rebaseline_no_pr(self, campo: str, novo: float, *, com_waiver: bool) -> str:
        _git(self.repo, "switch", "-q", "pr")
        conteudo, antigo = self._rebaselina(campo, novo)
        manifesto = _waiver(campo, antigo, novo) if com_waiver else "[]\n"
        return self._commit({_VIEW_MODEL: conteudo, _MANIFESTO: manifesto}, "rebaseline isolado")

    def pr_faz_merge_da_main(self) -> None:
        """O fluxo de auto-fix: merge da base na branch, não rebase."""
        _git(self.repo, "switch", "-q", "pr")
        _git(self.repo, "merge", "-q", "--no-ff", "--no-edit", "main")

    def evento(self) -> _Evento:
        """Monta `refs/pull/N/merge` como o GitHub: pai 1 = main, pai 2 = cabeça."""
        ponta = _git(self.repo, "rev-parse", "main")
        cabeca = _git(self.repo, "rev-parse", "pr")
        base_sha = _git(self.repo, "merge-base", cabeca, ponta)
        self._main_anda_depois_do_evento()
        _git(self.repo, "switch", "-q", "--detach", ponta)
        _git(self.repo, "merge", "-q", "--no-ff", "--no-edit", cabeca)
        return _Evento(self.repo, base_sha, cabeca)

    def _main_anda_depois_do_evento(self) -> None:
        """O deepen do CI roda minutos depois do evento: `origin/main` já passou do pai 1."""
        tardio = self.squash_de_rebaseline_na_main("bruto", 999.0)
        _git(self.repo, "update-ref", "refs/remotes/origin/main", tardio)


def _passo_do_ci(prefixo: str) -> dict:
    passos = yaml.safe_load(_CI.read_text(encoding="utf-8"))["jobs"]["pipeline-tests"]["steps"]
    achados = [p for p in passos if p.get("name", "").startswith(prefixo)]
    assert len(achados) == 1, f"esperado 1 passo {prefixo!r} em pipeline-tests, got {len(achados)}"
    return achados[0]


def _resolve_expressoes(texto: str, payload: dict[str, str]) -> str:
    def _valor(m: re.Match[str]) -> str:
        assert m.group(1) in payload, f"expressão do CI sem valor no cenário: {m.group(0)}"
        return payload[m.group(1)]

    return _EXPRESSAO_DO_EVENTO.sub(_valor, texto)


def _argv_do_ci(prefixo: str, script: str, evento: _Evento) -> list[str]:
    """O argv com que o passo `prefixo` do CI chama `script`, com o payload do cenário."""
    passo = _passo_do_ci(prefixo)
    payload = evento.payload()
    env = {k: _resolve_expressoes(str(v), payload) for k, v in (passo.get("env") or {}).items()}
    linhas = passo["run"].replace("\\\n", " ").splitlines()
    (chamada,) = [linha for linha in linhas if script in linha]
    argv = shlex.split(Template(_resolve_expressoes(chamada, payload)).substitute(env))
    return argv[argv.index(script) + 1 :]


def _acusados_pelo_ci(evento: _Evento, capsys: pytest.CaptureFixture[str]) -> set[str]:
    argv = _argv_do_ci(
        "Golden rebaseline isolation", "dev/check_golden_rebaseline_isolation.py", evento
    )
    codigo = isolamento.main(argv)
    prefixo = "check_golden_rebaseline_isolation: "
    erros = [l for l in capsys.readouterr().err.splitlines() if l.startswith(prefixo)]
    assert codigo == (1 if erros else 0)
    return {linha.removeprefix(prefixo).split(":", 1)[0] for linha in erros}


@pytest.fixture
def historico(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Historico:
    h = _Historico(tmp_path)
    monkeypatch.chdir(h.repo)
    monkeypatch.setattr(delta, "REPO_ROOT", h.repo)
    return h


@pytest.mark.parametrize("misto_proprio", [False, True], ids=["limpo", "misto-proprio"])
def test_branch_atras_da_main_so_responde_pelo_que_escreveu(historico, capsys, misto_proprio):
    """(a) e (b): o squash misto da main depois da base do PR não é dele; o misto dele é."""
    proprio = historico.commit_no_pr(misto=misto_proprio)
    historico.squash_de_rebaseline_na_main("bruto", 150.0)
    evento = historico.evento()
    esperado = {proprio[:10]} if misto_proprio else set()
    assert _acusados_pelo_ci(evento, capsys) == esperado


@pytest.mark.parametrize("misto_proprio", [False, True], ids=["limpo", "misto-proprio"])
def test_branch_que_fez_merge_da_main_so_responde_pelo_que_escreveu(
    historico, capsys, misto_proprio
):
    """(c): squash misto da main antes E depois do merge da base — nenhum é do PR."""
    proprio = historico.commit_no_pr(misto=misto_proprio)
    historico.squash_de_rebaseline_na_main("bruto", 150.0)
    historico.pr_faz_merge_da_main()
    historico.commit_no_pr(misto=False)
    historico.squash_de_rebaseline_na_main("bruto", 175.0)
    evento = historico.evento()
    esperado = {proprio[:10]} if misto_proprio else set()
    assert _acusados_pelo_ci(evento, capsys) == esperado


def _goldens_medidos_pelo_ci(evento: _Evento, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    medidos: list[str] = []
    monkeypatch.setattr(delta, "_diff_de", lambda _b, path, _t: medidos.append(path) or 0)
    argv = _argv_do_ci("Delta de golden declarado", "dev/check_golden_delta_declarado.py", evento)
    assert delta.main(argv) == 0
    return medidos


@pytest.mark.parametrize("fez_merge_da_main", [False, True], ids=["atras", "merge-da-main"])
def test_delta_nao_cobra_do_pr_o_rebaseline_da_main(historico, monkeypatch, fez_merge_da_main):
    """(a') e (c'): a main rebaselinou e esvaziou o manifesto — não há delta do PR."""
    historico.commit_no_pr(misto=False)
    historico.squash_de_rebaseline_na_main("bruto", 150.0)
    if fez_merge_da_main:
        historico.pr_faz_merge_da_main()
        historico.squash_de_rebaseline_na_main("bruto", 175.0)
    evento = historico.evento()
    assert _goldens_medidos_pelo_ci(evento, monkeypatch) == []


def _delta_do_ci_de_ponta_a_ponta(evento: _Evento, capfd: pytest.CaptureFixture[str]):
    argv = _argv_do_ci("Delta de golden declarado", "dev/check_golden_delta_declarado.py", evento)
    codigo = delta.main(argv)
    return codigo, capfd.readouterr().err


# A main rebaselina `bruto` depois do merge da base; o PR rebaselina `liquido`. Medido
# contra `base.sha`, o delta de `bruto` cairia no PR; contra a main do merge, só o
# `liquido` dele aparece — e reprova se ele não o declarou (anti-vacuidade do fix).
@pytest.mark.parametrize("com_waiver", [True, False], ids=["declarado", "sem-waiver"])
def test_delta_mede_o_rebaseline_do_pr_contra_a_main_do_merge(historico, capfd, com_waiver):
    """(b') e (c''): o delta do PR é medido contra a main do merge, não contra a base dele."""
    historico.squash_de_rebaseline_na_main("bruto", 150.0)
    historico.pr_faz_merge_da_main()
    historico.rebaseline_no_pr("liquido", 120.0, com_waiver=com_waiver)
    historico.squash_de_rebaseline_na_main("bruto", 175.0)
    codigo, err = _delta_do_ci_de_ponta_a_ponta(historico.evento(), capfd)
    assert "patrimonio.bruto" not in err
    assert codigo == (0 if com_waiver else 1)
    assert ("não-justificado: patrimonio.liquido" in err) is not com_waiver
