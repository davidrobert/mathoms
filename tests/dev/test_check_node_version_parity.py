"""Prova por mutação do gate de paridade do major do Node (`.nvmrc` = FROM = CI = compose)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest
import yaml

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "dev"))

from check_node_version_parity import (  # noqa: E402
    _COMPOSE_RE,
    check_node_parity,
    is_workflow,
    main,
    walk_repo,
)

_DIGEST = "@sha256:" + "a" * 64


def _write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _setup_node_job(with_block: str, extra: str = "") -> str:
    return (
        "jobs:\n  web:\n    runs-on: ubuntu-latest\n" + extra + "    steps:\n"
        "      - uses: actions/setup-node@v4\n        with:\n" + with_block
    )


def _mini_repo(root: Path, *, nvmrc: str = "26\n", from_major: str = "26") -> Path:
    _write(root, "frontend/package.json", "{}\n")
    _write(root, "frontend/.nvmrc", nvmrc)
    _write(
        root,
        "frontend/Dockerfile",
        f"# syntax=docker/dockerfile:1\nFROM node:{from_major}-alpine{_DIGEST} AS deps\n"
        "FROM deps AS builder\n"
        f"FROM node:{from_major}-alpine{_DIGEST} AS runner\n",
    )
    _write(
        root,
        ".github/workflows/ci.yml",
        _setup_node_job(
            "          node-version-file: frontend/.nvmrc\n"
            "          cache-dependency-path: frontend/package-lock.json\n"
        ),
    )
    return root


def _divergences(root: Path) -> list[str]:
    return [d.format() for d in check_node_parity(root).divergences]


def test_repo_minimo_alinhado_passa(tmp_path: Path) -> None:
    assert main(["--root", str(_mini_repo(tmp_path))]) == 0


def test_dockerfile_em_major_novo_sem_nvmrc_reprova(tmp_path: Path) -> None:
    found = _divergences(_mini_repo(tmp_path, from_major="28"))
    assert len(found) == 2
    assert all("major 28" in d and "esperado 26 (frontend/.nvmrc)" in d for d in found)


def test_nvmrc_sozinho_em_major_novo_reprova(tmp_path: Path) -> None:
    assert main(["--root", str(_mini_repo(tmp_path, nvmrc="28\n"))]) == 1


def test_bump_alinhado_no_mesmo_pr_passa(tmp_path: Path) -> None:
    assert main(["--root", str(_mini_repo(tmp_path, nvmrc="28\n", from_major="28"))]) == 0


@pytest.mark.parametrize("nvmrc", ["lts/*", "node", ""])
def test_nvmrc_sem_major_numerico_reprova(tmp_path: Path, nvmrc: str) -> None:
    found = _divergences(_mini_repo(tmp_path, nvmrc=nvmrc))
    assert found and all(d.startswith("frontend/.nvmrc:") for d in found)


def test_nvmrc_ausente_reprova(tmp_path: Path) -> None:
    (_mini_repo(tmp_path) / "frontend/.nvmrc").unlink()
    assert _divergences(tmp_path) == [
        "frontend/.nvmrc: arquivo ausente; esperado um major numérico (ex.: `26`)"
    ]


def test_repo_sem_app_reprova(tmp_path: Path) -> None:
    assert main(["--root", str(tmp_path)]) == 1


def test_from_com_plataforma_registry_e_patch_passa(tmp_path: Path) -> None:
    _mini_repo(tmp_path)
    _write(
        tmp_path,
        "frontend/Dockerfile",
        "FROM --platform=$BUILDPLATFORM docker.io/library/node:26.1.0-alpine AS deps\n"
        "from deps as builder\n",
    )
    assert _divergences(tmp_path) == []


@pytest.mark.parametrize(
    ("line", "trecho"),
    [
        ("FROM node:${NODE_MAJOR}-alpine", "sem major numérico"),
        ("FROM node:lts-alpine", "sem major numérico"),
        (f"FROM node{_DIGEST}", "sem major numérico"),
        ("FROM python:3.12-slim\nFROM node:26-alpine", "base 'python:3.12-slim'"),
    ],
)
def test_from_que_o_gate_nao_sabe_medir_reprova(tmp_path: Path, line: str, trecho: str) -> None:
    _mini_repo(tmp_path)
    _write(tmp_path, "frontend/Dockerfile", line + "\n")
    assert any(trecho in d for d in _divergences(tmp_path))


def test_dockerfile_de_app_sem_from_node_reprova(tmp_path: Path) -> None:
    _mini_repo(tmp_path)
    _write(tmp_path, "frontend/Dockerfile", "FROM gcr.io/distroless/nodejs26-debian12\n")
    assert "frontend/Dockerfile: 0 `FROM node:`; esperado ≥1 (imagem de app)" in _divergences(
        tmp_path
    )


def test_from_node_fora_de_app_reprova(tmp_path: Path) -> None:
    _mini_repo(tmp_path)
    _write(tmp_path, "services/worker/Dockerfile", "FROM node:26-alpine\n")
    assert any(
        d.startswith("services/worker/Dockerfile:1") and "nenhum app" in d
        for d in _divergences(tmp_path)
    )


@pytest.mark.parametrize(
    ("with_block", "trecho"),
    [
        ("          node-version: '20'\n", "atribuível a nenhum app"),
        ("          cache: npm\n", "setup-node sem versão"),
        ("          node-version: ${{ matrix.node }}\n", "node-version '${{ matrix.node }}'"),
        ("          node-version-file: ${{ matrix.file }}\n", "node-version-file '${{"),
        ("          node-version-file: frontend-ops/.nvmrc\n", "node-version-file 'frontend-ops"),
    ],
)
def test_setup_node_que_o_gate_nao_sabe_atribuir_reprova(
    tmp_path: Path, with_block: str, trecho: str
) -> None:
    _mini_repo(tmp_path)
    _write(tmp_path, ".github/workflows/x.yml", _setup_node_job(with_block))
    assert any(
        d.startswith(".github/workflows/x.yml#web") and trecho in d for d in _divergences(tmp_path)
    )


def test_literal_atribuido_por_path_e_comparado(tmp_path: Path) -> None:
    _mini_repo(tmp_path)
    defaults = "    defaults:\n      run:\n        working-directory: frontend\n"
    _write(
        tmp_path,
        ".github/workflows/x.yml",
        _setup_node_job("          node-version: 26\n", defaults),
    )
    assert _divergences(tmp_path) == []
    _write(
        tmp_path,
        ".github/workflows/x.yml",
        _setup_node_job("          node-version: 20.x\n", defaults),
    )
    assert ["major 20" in d for d in _divergences(tmp_path)] == [True]


def test_prosa_do_job_nao_atribui_app(tmp_path: Path) -> None:
    _mini_repo(tmp_path)
    job = (
        "jobs:\n  web:\n    name: frontend\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: actions/setup-node@0a44ba7841725637a19e28fa30b79a866c81b0a6\n"
        "        with:\n          node-version: '26'\n"
        "      - run: cd frontend && npm ci\n"
    )
    _write(tmp_path, ".github/workflows/x.yml", job)
    assert any("atribuível a nenhum app" in d for d in _divergences(tmp_path))


def test_matrix_por_app_le_o_nvmrc_de_cada_um_passa(tmp_path: Path) -> None:
    _mini_repo(tmp_path)
    _write(
        tmp_path,
        ".github/workflows/x.yml",
        _setup_node_job("          node-version-file: ${{ matrix.dir }}/.nvmrc\n"),
    )
    assert _divergences(tmp_path) == []


def test_container_node_do_job_e_medido(tmp_path: Path) -> None:
    _mini_repo(tmp_path)
    extra = "    container: node:20-bookworm\n    defaults:\n      run:\n        working-directory: frontend\n"
    _write(
        tmp_path,
        ".github/workflows/x.yml",
        _setup_node_job("          node-version-file: frontend/.nvmrc\n", extra),
    )
    assert any("'node:20-bookworm' → major 20" in d for d in _divergences(tmp_path))


def test_compose_de_dev_atrasado_reprova(tmp_path: Path) -> None:
    _mini_repo(tmp_path)
    compose = (
        "services:\n  frontend:\n    image: node:22-alpine\n    working_dir: /app/frontend\n"
        "    volumes:\n      - ./frontend:/app/frontend\n"
        "      - mathoms_dev_frontend_modules:/app/frontend/node_modules\n"
        "  ops:\n    build:\n      context: ./frontend\n    image: mathoms-ops:dev\n"
    )
    _write(tmp_path, "docker-compose.dev.yml", compose)
    assert _divergences(tmp_path) == [
        "docker-compose.dev.yml#frontend: 'node:22-alpine' → major 22; esperado 26 "
        "(frontend/.nvmrc); alinhe este sítio — ou, se o major novo é o certo (PR de major do "
        "Dependabot), suba o .nvmrc e os demais sítios do app no mesmo PR"
    ]


# --- Repo real: o gate discrimina sobre os arquivos que o CI de fato lê ---------


def _copy_real_inputs(dest: Path) -> Path:
    for path in walk_repo(_REPO):
        rel = path.relative_to(_REPO).as_posix()
        wanted = (
            path.name.startswith("Dockerfile")
            or is_workflow(rel)
            or bool(_COMPOSE_RE.match(path.name))
            or (rel.count("/") == 1 and path.name in {"package.json", ".nvmrc"})
        )
        if wanted:
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest / rel)
    return dest


def _bump(root: Path, rel: str, old: str, new: str, count: int) -> None:
    text = (root / rel).read_text()
    assert text.count(old) == count, f"{rel}: esperava {count}× {old!r}, achei {text.count(old)}"
    (root / rel).write_text(text.replace(old, new))


def test_repo_real_passa_e_mede_os_sitios_conhecidos() -> None:
    report = check_node_parity(_REPO)
    assert report.divergences == []
    assert report.majors == {"frontend": 26, "frontend-ops": 26}
    wheres = {pin.where.split(":")[0].split("#")[0] for pin in report.pins}
    assert {"frontend/Dockerfile", "frontend-ops/Dockerfile", "docker-compose.dev.yml"} <= wheres


def test_repo_real_dockerfile_em_node_28_reprova(tmp_path: Path) -> None:
    root = _copy_real_inputs(tmp_path)
    _bump(root, "frontend/Dockerfile", "FROM node:26-alpine", "FROM node:28-alpine", 3)
    found = _divergences(root)
    assert len(found) == 3
    assert all(d.startswith("frontend/Dockerfile:") and "major 28; esperado 26" in d for d in found)


def test_repo_real_literal_velho_no_ci_reprova(tmp_path: Path) -> None:
    root = _copy_real_inputs(tmp_path)
    ci = ".github/workflows/ci.yml"
    text = (root / ci).read_text()
    (root / ci).write_text(
        text.replace("node-version-file: frontend/.nvmrc", 'node-version: "20"', 1)
    )
    assert _divergences(root) == [
        ".github/workflows/ci.yml#frontend-checks: 'node-version: 20' → major 20; esperado 26 "
        "(frontend/.nvmrc); alinhe este sítio — ou, se o major novo é o certo (PR de major do "
        "Dependabot), suba o .nvmrc e os demais sítios do app no mesmo PR"
    ]


def test_repo_real_bump_de_major_alinhado_por_app_passa(tmp_path: Path) -> None:
    """Unidade de paridade = unidade de bump do Dependabot (um PR por diretório)."""
    root = _copy_real_inputs(tmp_path)
    _bump(root, "frontend-ops/Dockerfile", "FROM node:26-alpine", "FROM node:28-alpine", 3)
    assert main(["--root", str(root)]) == 1
    _bump(root, "frontend-ops/.nvmrc", "26", "28", 1)
    assert main(["--root", str(root)]) == 0
    assert check_node_parity(root).majors == {"frontend": 26, "frontend-ops": 28}


def test_hook_roda_sempre_e_nao_e_pulado_no_ci() -> None:
    config = yaml.safe_load((_REPO / ".pre-commit-config.yaml").read_text())
    hooks = {h["id"]: h for repo in config["repos"] for h in repo["hooks"]}
    hook = hooks["node-version-parity"]
    assert hook["entry"] == "python3 dev/check_node_version_parity.py"
    assert hook.get("always_run") is True and "stages" not in hook
    ci = (_REPO / ".github/workflows/ci.yml").read_text()
    skip_lines = [line for line in ci.splitlines() if line.strip().startswith("SKIP:")]
    assert skip_lines and all("node-version-parity" not in line for line in skip_lines)
