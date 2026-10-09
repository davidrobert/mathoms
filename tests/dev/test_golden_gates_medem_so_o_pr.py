"""Os dois gates de golden medem o que o PR escreveu, não a main que ele ainda não tem.

Em `pull_request` o checkout é o merge sintético (`refs/pull/N/merge`): pai 1 é a
main contra a qual o GitHub montou o merge, pai 2 a cabeça do PR. `base.sha` é o
merge-base no último push, então `base.sha..HEAD` arrastava a main inteira desde a
base do PR. Squash de PR que isolou o rebaseline junta golden+produção num commit
só: todo PR atrás da main tomava vermelho por commit alheio. Medido no #2065 (run
37868572346), acusado por `3ff4c12174` — o squash do #2063 — sem ter tocado golden.
O passo do delta tinha a mesma faixa e cobrava do PR o delta que veio da main.

A faixa certa exige o histórico do merge do evento, e o `--deepen` relativo não o
trazia quando o GitHub recomputava a ref (a main andou): o HEAD ficava sem pais e o
gate antigo saía verde calado. Por isso o passo de fetch também é exercitado aqui.

Os testes tiram do `ci.yml` o argv com que o CI chama cada gate, e rodam o passo de
fetch dele: o defeito morava na costura YAML↔script, e um lado só não o veria.
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
_EXPRESSAO = re.compile(r"\$\{\{\s*(.+?)\s*\}\}")
_ISOLAMENTO = ("Golden rebaseline isolation", "dev/check_golden_rebaseline_isolation.py")
_DELTA = ("Delta de golden declarado", "dev/check_golden_delta_declarado.py")
_PASSO_DE_HISTORICO = "historico-pr"
# O GitHub serve o merge do evento por SHA mesmo sem ref que o alcance.
_SERVE_QUALQUER_SHA = "git -c uploadpack.allowAnySHA1InWant=true upload-pack"

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
    """O que o CI recebe: o merge sintético em HEAD, o payload e o `GITHUB_SHA`."""

    repo: Path
    base_sha: str
    head_sha: str
    merge_sha: str

    def contexto(self) -> dict[str, str]:
        return {
            "github.event.pull_request.base.sha": self.base_sha,
            "github.event.pull_request.head.sha": self.head_sha,
            "github.sha": self.merge_sha,
        }

    def env_do_runner(self) -> dict[str, str]:
        return {"GITHUB_SHA": self.merge_sha}


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
        return _Evento(self.repo, base_sha, cabeca, _git(self.repo, "rev-parse", "HEAD"))

    def _main_anda_depois_do_evento(self) -> None:
        """Os gates rodam minutos depois do evento: `origin/main` já passou do pai 1."""
        tardio = self.squash_de_rebaseline_na_main("bruto", 999.0)
        _git(self.repo, "update-ref", "refs/remotes/origin/main", tardio)


def _unico(passos: list[dict], rotulo: str) -> dict:
    assert len(passos) == 1, f"esperado 1 passo {rotulo!r} em pipeline-tests, got {len(passos)}"
    return passos[0]


def _passos_do_ci() -> list[dict]:
    return yaml.safe_load(_CI.read_text(encoding="utf-8"))["jobs"]["pipeline-tests"]["steps"]


def _resolve_expressoes(texto: str, contexto: dict[str, str]) -> str:
    def _valor(m: re.Match[str]) -> str:
        assert m.group(1) in contexto, f"expressão do CI fora da lista conhecida: {m.group(0)}"
        return contexto[m.group(1)]

    return _EXPRESSAO.sub(_valor, texto)


def _argv_do_ci(passo_e_script: tuple[str, str], evento: _Evento) -> list[str]:
    """O argv com que o passo do CI chama o script, com o evento do cenário resolvido."""
    prefixo, script = passo_e_script
    passo = _unico([p for p in _passos_do_ci() if p.get("name", "").startswith(prefixo)], prefixo)
    contexto = evento.contexto()
    env = {k: _resolve_expressoes(str(v), contexto) for k, v in (passo.get("env") or {}).items()}
    linhas = passo["run"].replace("\\\n", " ").splitlines()
    (chamada,) = [linha for linha in linhas if script in linha]
    expandida = Template(_resolve_expressoes(chamada, contexto))
    argv = shlex.split(expandida.substitute({**evento.env_do_runner(), **env}))
    return argv[argv.index(script) + 1 :]


def _acusados_pelo_ci(evento: _Evento, capsys: pytest.CaptureFixture[str]) -> set[str]:
    codigo = isolamento.main(_argv_do_ci(_ISOLAMENTO, evento))
    prefixo = "check_golden_rebaseline_isolation: "
    erros = [l for l in capsys.readouterr().err.splitlines() if l.startswith(prefixo)]
    assert codigo == (1 if erros else 0), erros
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
    assert delta.main(_argv_do_ci(_DELTA, evento)) == 0
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
    codigo = delta.main(_argv_do_ci(_DELTA, historico.evento()))
    err = capfd.readouterr().err
    assert "patrimonio.bruto" not in err
    assert codigo == (0 if com_waiver else 1)
    assert ("não-justificado: patrimonio.liquido" in err) is not com_waiver


def test_checkout_que_nao_e_o_merge_do_evento_e_recusado(historico, capsys):
    """Numa cabeça que fez merge da main, os pais trocados inverteriam a faixa."""
    historico.commit_no_pr(misto=False)
    historico.squash_de_rebaseline_na_main("bruto", 150.0)
    historico.pr_faz_merge_da_main()
    evento = historico.evento()
    _git(historico.repo, "switch", "-q", "--detach", evento.head_sha)
    assert isolamento.check_commit_range("HEAD^1..HEAD^2"), "a faixa invertida acusaria a main"
    argv = ["--pr-head-sha", evento.head_sha, "--merge-sha"]
    assert isolamento.main([*argv, evento.merge_sha]) == 2
    assert isolamento.main([*argv, evento.head_sha]) == 2
    err = capsys.readouterr().err
    assert "não é o merge do evento" in err and "pai 2" in err


def test_sha_que_nao_e_sha_e_recusado(historico, capsys):
    historico.commit_no_pr(misto=False)
    evento = historico.evento()
    assert isolamento.main(["--pr-head-sha", "HEAD^2", "--merge-sha", evento.merge_sha]) == 2
    assert "SHA de 40 hex" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        isolamento.main(["--pr-head-sha", evento.head_sha])


def _clone_do_checkout(evento: _Evento, destino: Path) -> Path:
    """O que o actions/checkout faz em `pull_request`: o merge do evento, com depth 1."""
    _git(evento.repo, "update-ref", "refs/pull/1/merge", evento.merge_sha)
    _git(evento.repo, "switch", "-q", "main")
    destino.mkdir()
    _git(destino, "init", "-q")
    _git(destino, "remote", "add", "origin", f"file://{evento.repo}")
    _git(destino, "config", "remote.origin.uploadpack", _SERVE_QUALQUER_SHA)
    alvo = f"+{evento.merge_sha}:refs/remotes/pull/1/merge"
    _git(destino, "fetch", "-q", "--no-tags", "--depth=1", "origin", alvo)
    _git(destino, "switch", "-q", "--detach", "refs/remotes/pull/1/merge")
    return destino


def _github_recomputa_o_merge(evento: _Evento) -> None:
    """A main andou e o GitHub refez o `refs/pull/N/merge`: o merge do evento fica sem ref."""
    _git(evento.repo, "update-ref", "-d", "refs/pull/1/merge")


def _roda_o_passo_de_historico_do_ci(clone: Path, evento: _Evento) -> None:
    passos = [p for p in _passos_do_ci() if p.get("id") == _PASSO_DE_HISTORICO]
    script = _resolve_expressoes(_unico(passos, _PASSO_DE_HISTORICO)["run"], evento.contexto())
    env = {**_GIT_ENV, **evento.env_do_runner()}
    subprocess.run(["bash", "-e", "-c", script], cwd=clone, env=env, check=True)


def _pr_atras_da_main_com_misto_proprio(historico: _Historico) -> tuple[_Evento, str]:
    proprio = historico.commit_no_pr(misto=True)
    for valor in (150.0, 175.0, 200.0):
        historico.squash_de_rebaseline_na_main("bruto", valor)
    return historico.evento(), proprio


@pytest.mark.parametrize("recomputado", [False, True], ids=["ref-viva", "ref-recomputada"])
def test_passo_de_historico_do_ci_delimita_o_pr_mesmo_com_o_merge_recomputado(
    historico, tmp_path, monkeypatch, capsys, recomputado
):
    """Re-run, ou main que anda durante o pytest: o merge do evento perde a ref."""
    evento, proprio = _pr_atras_da_main_com_misto_proprio(historico)
    clone = _clone_do_checkout(evento, tmp_path / "ci")
    if recomputado:
        _github_recomputa_o_merge(evento)
    _roda_o_passo_de_historico_do_ci(clone, evento)
    monkeypatch.chdir(clone)
    assert _acusados_pelo_ci(evento, capsys) == {proprio[:10]}


def test_a_fixture_reproduz_o_merge_recomputado_com_o_deepen_relativo(historico, tmp_path):
    """Anti-vacuidade do teste acima: com o fetch de antes, o HEAD fica sem pais."""
    evento, _ = _pr_atras_da_main_com_misto_proprio(historico)
    clone = _clone_do_checkout(evento, tmp_path / "ci")
    _github_recomputa_o_merge(evento)
    _git(clone, "fetch", "-q", "--no-tags", "--deepen=500", "origin")
    with pytest.raises(isolamento.MergeSinteticoInesperado, match="sem pais"):
        isolamento.base_do_merge_sintetico(evento.head_sha, evento.merge_sha, cwd=clone)


@pytest.mark.parametrize(
    "aprofunda,recusa",
    [(0, "sem pais"), (2, "cruza o limite do clone raso")],
    ids=["sem-fetch", "deepen-curto"],
)
def test_clone_raso_demais_e_recusado_em_vez_de_mentir(historico, tmp_path, aprofunda, recusa):
    """Faixa truncada pelo clone raso arrastaria a main; a guarda recusa."""
    evento, _ = _pr_atras_da_main_com_misto_proprio(historico)
    clone = _clone_do_checkout(evento, tmp_path / "ci")
    if aprofunda:
        _git(clone, "fetch", "-q", "--no-tags", f"--deepen={aprofunda}", "origin")
    with pytest.raises(isolamento.MergeSinteticoInesperado, match=re.escape(recusa)):
        isolamento.base_do_merge_sintetico(evento.head_sha, evento.merge_sha, cwd=clone)
