"""Testes do gate `dev/check_frontend_lock_sync.py`.

Cada caso monta um repo git real. O npm e o docker entram como fakes
injetados: a decisão sob teste é QUAL npm valida o lock e QUAL imagem
responde. O comportamento do npm 10 vs 11 é fato externo, medido em
2026-10-09 e registrado no docstring do gate.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dev import check_frontend_lock_sync as gate

DIGEST = "sha256:" + "a" * 64
FROM_26 = f"FROM node:26-alpine@{DIGEST} AS deps\nFROM node:26-alpine@{DIGEST} AS runner\n"
DESYNC = "npm error `npm ci` can only install packages when your package.json and package-lock.json are in sync.\nnpm error Missing: @next/swc-linux-x64-musl@16.4.0 from lock file\n"


def _repo(tmp_path: Path, apps: dict[str, dict[str, str]]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    for app, files in apps.items():
        (repo / app).mkdir()
        for name, content in files.items():
            (repo / app / name).write_text(content, encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    return repo


def _app(dockerfile: str = FROM_26) -> dict[str, str]:
    return {"package.json": "{}", "package-lock.json": "{}", "Dockerfile": dockerfile}


class _FakeNpm:
    def __init__(self, returncode: int = 0, stderr: str = "") -> None:
        self.calls: list[tuple[str, str]] = []
        self._result = (returncode, stderr)

    def __call__(self, app_dir: Path, npm_version: str) -> subprocess.CompletedProcess[str]:
        self.calls.append((app_dir.name, npm_version))
        return subprocess.CompletedProcess([], self._result[0], "", self._result[1])


def _fake_docker(version: str, returncode: int = 0):
    def run(ref: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([ref], returncode, f"{version}\n", "pull failed")

    return run


@pytest.fixture
def npm() -> _FakeNpm:
    return _FakeNpm()


def _run(repo: Path, npm: _FakeNpm, *extra: str, npx: str | None = "/bin/npx", env=None) -> int:
    return gate.main(
        ["--repo", str(repo), *extra],
        npm_runner=npm,
        which=lambda _: npx,
        env=env or {},
    )


def test_lock_e_validado_pelo_npm_do_from_nao_pelo_npm_10(tmp_path: Path) -> None:
    # A mutação de origem: o hook rodava `npm@10` contra imagem que traz npm 11,
    # e o lock sem o optional musl passava aqui e quebrava o `npm ci` de prod.
    repo = _repo(tmp_path, {"frontend": _app()})
    npm = _FakeNpm()
    assert _run(repo, npm) == 0
    assert npm.calls == [("frontend", gate.NPM_BY_NODE_MAJOR[26])]
    assert not gate.NPM_BY_NODE_MAJOR[26].startswith("10.")


def test_todo_app_com_package_json_e_validado(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"frontend": _app(), "frontend-ops": _app(), "backend": {"x.py": ""}})
    npm = _FakeNpm()
    assert _run(repo, npm) == 0
    assert {app for app, _ in npm.calls} == {"frontend", "frontend-ops"}


@pytest.mark.parametrize("missing", ["package-lock.json", "Dockerfile"])
def test_app_sem_lock_ou_sem_dockerfile_reprova(
    tmp_path: Path, missing: str, npm: _FakeNpm, capsys
) -> None:
    files = _app()
    del files[missing]
    repo = _repo(tmp_path, {"frontend": files})
    assert _run(repo, npm) == 1
    assert npm.calls == []
    assert f"sem frontend/{missing}" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("dockerfile", "expected"),
    [
        ("FROM python:3.12-slim\n", "nenhum `FROM node:`"),
        ("ARG NODE=26\nFROM node:${NODE}-alpine\n", "variável não resolvível"),
        ("FROM node:lts-alpine\n", "tag sem major"),
        (f"FROM node@{DIGEST}\n", "tag sem major"),
        ("FROM node:26-alpine AS deps\nFROM node:24-alpine AS runner\n", "majors divergentes"),
    ],
)
def test_from_que_nao_fixa_um_major_reprova(
    tmp_path: Path, dockerfile: str, expected: str, npm: _FakeNpm, capsys
) -> None:
    repo = _repo(tmp_path, {"frontend": _app(dockerfile)})
    assert _run(repo, npm) == 1
    assert expected in capsys.readouterr().err


@pytest.mark.parametrize(
    "line",
    [
        f"FROM node:26-alpine@{DIGEST} AS deps",
        "FROM --platform=$BUILDPLATFORM node:26.8.1-alpine3.22 AS deps",
        "from docker.io/library/node:26 as deps",
    ],
)
def test_formas_validas_de_from_resolvem_o_major(line: str) -> None:
    refs = gate.node_image_refs("frontend", f"{line}\nFROM deps AS builder\n")
    assert gate.node_major("frontend", refs) == 26


def test_node_major_fora_do_mapa_reprova_com_o_comando_de_medida(tmp_path: Path, capsys) -> None:
    # O PR de major do Dependabot (precedente: node 22→26 em #1634) fica vermelho
    # até alguém medir o npm da imagem nova e mapear.
    repo = _repo(tmp_path, {"frontend": _app(f"FROM node:28-alpine@{DIGEST}\n")})
    assert _run(repo, _FakeNpm()) == 1
    err = capsys.readouterr().err
    assert "[mapa]" in err
    assert "docker run --rm --entrypoint npm" in err
    assert '`28: "<versão>",`' in err


def test_lock_dessincronizado_reprova_com_a_correcao_no_npm_certo(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path, {"frontend": _app()})
    assert _run(repo, _FakeNpm(1, DESYNC)) == 1
    err = capsys.readouterr().err
    assert "[lock]" in err
    assert f"npx -y npm@{gate.NPM_BY_NODE_MAJOR[26]} install --package-lock-only" in err
    assert "Missing: @next/swc-linux-x64-musl" in err


_NPM_CI_USAGE = """npm error Clean install a project
npm error
npm error Usage:
npm error npm ci
npm error
npm error Options:
npm error [--install-strategy <hoisted|nested|shallow|linked>] [--legacy-bundling]
npm error [--global-style] [--omit <dev|optional|peer> [--omit <dev|optional|peer> ...]]
npm error [--include <prod|dev|optional|peer> [--include <prod|dev|optional|peer> ...]]
npm error [--strict-peer-deps] [--foreground-scripts] [--ignore-scripts] [--no-audit]
npm error [--no-bin-links] [--no-fund] [--dry-run]
npm error [-w|--workspace <workspace-name> [-w|--workspace <workspace-name> ...]]
npm error [-ws|--workspaces] [--include-workspace-root] [--install-links]
npm error
npm error aliases: clean-install, ic, install-clean, isntall-clean
npm error
npm error Run "npm help ci" for more info
npm error A complete log of this run can be found in: /tmp/npm-debug.log
"""


def test_motivo_do_lock_aparece_mesmo_com_o_bloco_de_uso_do_npm(tmp_path: Path, capsys) -> None:
    # Regressão do #2187 (msw 3): o corte pelas últimas 15 linhas mostrava só o
    # uso do `npm ci` e escondia os 11 `Missing:` que davam o motivo.
    missing = [f"npm error Missing: pacote-{i}@1.0.0 from lock file" for i in range(11)]
    output = "\n".join(["npm error code EUSAGE", *missing]) + "\n" + _NPM_CI_USAGE
    repo = _repo(tmp_path, {"frontend": _app()})
    assert _run(repo, _FakeNpm(1, output)) == 1
    err = capsys.readouterr().err
    assert all(line.removeprefix("npm error ") in err for line in missing)
    assert "Options:" not in err


def test_trecho_do_erro_tem_teto_e_conta_o_que_omitiu() -> None:
    output = "\n".join(f"npm error Missing: p{i}@1.0.0 from lock file" for i in range(100))
    excerpt = gate.npm_error_excerpt(output)
    assert "p59@" in excerpt
    assert "p60@" not in excerpt
    assert "(+40 linhas)" in excerpt


def test_conflito_de_peer_nao_manda_regenerar_o_lock(tmp_path: Path, capsys) -> None:
    eresolve = (
        "npm error code ERESOLVE\nnpm error ERESOLVE could not resolve\n"
        "npm error While resolving: @vitest/mocker@3.2.4\nnpm error Found: msw@3.0.2\n"
        'npm error Could not resolve dependency:\nnpm error peerOptional msw@"^2.4.9"\n'
    )
    repo = _repo(tmp_path, {"frontend": _app()})
    assert _run(repo, _FakeNpm(1, eresolve)) == 1
    err = capsys.readouterr().err
    assert "[peer]" in err
    assert 'peerOptional msw@"^2.4.9"' in err
    assert "install --package-lock-only" not in err


def test_falha_de_ambiente_nao_e_atribuida_ao_lock(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path, {"frontend": _app()})
    assert _run(repo, _FakeNpm(1, "npm error code ECONNRESET\nnpm error network aborted")) == 1
    err = capsys.readouterr().err
    assert "[ambiente]" in err
    assert "dessincronizado" not in err


def test_npx_ausente_reprova_em_ci(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"frontend": _app()})
    assert _run(repo, _FakeNpm(), npx=None, env={"CI": "true"}) == 1


def test_npx_ausente_so_avisa_local(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path, {"frontend": _app()})
    assert _run(repo, _FakeNpm(), npx=None) == 0
    assert "pulado" in capsys.readouterr().err


def _verify(repo: Path, docker) -> int:
    return gate.main(["--repo", str(repo), "--verify-image", "frontend"], docker_runner=docker)


def test_verify_image_passa_quando_a_imagem_traz_o_npm_do_mapa(tmp_path: Path, capsys) -> None:
    # O sucesso imprime o que a imagem respondeu: step verde sem saída não prova
    # que o `docker run` aconteceu.
    repo = _repo(tmp_path, {"frontend": _app()})
    assert _verify(repo, _fake_docker(gate.NPM_BY_NODE_MAJOR[26])) == 0
    assert f"traz npm {gate.NPM_BY_NODE_MAJOR[26]}" in capsys.readouterr().out


def test_verify_image_reprova_mapa_mutado_para_o_npm_10(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    # Contrafactual: com o mapa de volta ao npm 10, o lock-sync voltaria ao ponto
    # cego da classe "optional ausente". A imagem real responde npm 11.
    monkeypatch.setitem(gate.NPM_BY_NODE_MAJOR, 26, "10.9.9")
    repo = _repo(tmp_path, {"frontend": _app()})
    assert _verify(repo, _fake_docker("11.19.0")) == 1
    assert "[imagem]" in capsys.readouterr().err


def test_verify_image_so_avisa_quando_o_minor_diverge(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path, {"frontend": _app()})
    assert _verify(repo, _fake_docker("11.99.0")) == 0
    assert "::warning::" in capsys.readouterr().out


def test_verify_image_falha_do_docker_reprova(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"frontend": _app()})
    assert _verify(repo, _fake_docker("", returncode=125)) == 1


def test_dockerfiles_reais_resolvem_para_o_mapa() -> None:
    tracked = gate.tracked_files(gate.REPO)
    apps = gate.apps_from_tracked(tracked)
    assert {"frontend", "frontend-ops"} <= set(apps)
    for app in apps:
        target = gate.resolve_target(gate.REPO, app, set(tracked))
        assert target.npm_version == gate.NPM_BY_NODE_MAJOR[target.node_major]
