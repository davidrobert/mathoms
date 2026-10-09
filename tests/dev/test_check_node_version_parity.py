"""Prova por mutação do gate de paridade do major do Node (`.nvmrc` = FROM = CI = compose)."""

from __future__ import annotations

import fnmatch
import json
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
    node_major,
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


# --- Node do runner: job que chama Node sem setup-node antes ---------------------


def _run_job(*steps: str, extra: str = "") -> str:
    body = "".join(f"      - {step}\n" for step in steps)
    return "jobs:\n  lint:\n    runs-on: ubuntu-latest\n" + extra + "    steps:\n" + body


_SETUP_STEP = (
    "uses: actions/setup-node@v5\n        with:\n          node-version-file: frontend/.nvmrc"
)


@pytest.mark.parametrize(
    ("run", "command"),
    [
        ("npm ci", "npm"),
        ("pre-commit run --all-files", "pre-commit"),
        ("python3 x.py && node -e 1", "node"),
        ("env CI=1 npx playwright test", "npx"),
        ('echo "$(npm --version)"', "npm"),
    ],
)
def test_job_que_chama_node_sem_setup_node_reprova(tmp_path: Path, run: str, command: str) -> None:
    _mini_repo(tmp_path)
    _write(
        tmp_path, ".github/workflows/x.yml", _run_job("uses: actions/checkout@v5", f"run: {run}")
    )
    assert _divergences(tmp_path) == [
        f".github/workflows/x.yml#lint: step 2 chama `{command}` no Node do runner (sem "
        "setup-node antes); esperado `actions/setup-node` com `node-version-file: "
        "<app>/.nvmrc` antes dele (ou `container: node:<major>`)"
    ]


def test_setup_node_depois_do_step_que_chama_node_reprova(tmp_path: Path) -> None:
    _mini_repo(tmp_path)
    _write(tmp_path, ".github/workflows/x.yml", _run_job("run: npm ci", _SETUP_STEP))
    assert any("#lint: step 1 chama `npm`" in d for d in _divergences(tmp_path))
    _write(tmp_path, ".github/workflows/x.yml", _run_job(_SETUP_STEP, "run: npm ci"))
    assert _divergences(tmp_path) == []


@pytest.mark.parametrize(
    "run",
    [
        "|\n          # npm ci fica para o job do frontend\n          ruff check .",
        "ls frontend/node_modules/.bin",
        "cat .pre-commit-config.yaml",
        "echo setup-node --node-version",
    ],
)
def test_texto_que_nao_chama_node_passa(tmp_path: Path, run: str) -> None:
    _mini_repo(tmp_path)
    _write(tmp_path, ".github/workflows/x.yml", _run_job(f"run: {run}"))
    assert _divergences(tmp_path) == []


def test_container_node_dispensa_setup_node(tmp_path: Path) -> None:
    _mini_repo(tmp_path)
    extra = "    container: node:26-bookworm\n    defaults:\n      run:\n        working-directory: frontend\n"
    _write(tmp_path, ".github/workflows/x.yml", _run_job("run: npm ci", extra=extra))
    assert _divergences(tmp_path) == []
    _write(
        tmp_path,
        ".github/workflows/x.yml",
        _run_job("run: npm ci", extra="    container: python:3.13\n"),
    )
    assert any("chama `npm` no Node do runner" in d for d in _divergences(tmp_path))


# --- @types/node: major ≤ runtime, medido no lock ------------------------------

_TYPES_KEY = "node_modules/@types/node"


def _types_repo(root: Path, copies: dict[str, object], *, declared: bool = True) -> Path:
    _mini_repo(root)
    manifest = {"devDependencies": {"@types/node": "^26.0.0"}} if declared else {}
    _write(root, "frontend/package.json", json.dumps(manifest))
    packages = {"": manifest, **{k: {"version": v} for k, v in copies.items()}}
    _write(
        root, "frontend/package-lock.json", json.dumps({"lockfileVersion": 3, "packages": packages})
    )
    return root


@pytest.mark.parametrize("version", ["26.6.4", "25.6.0", "22.19.17"])
def test_types_node_no_major_do_runtime_ou_abaixo_passa(tmp_path: Path, version: str) -> None:
    """Major ímpar (25) passa: o calendário de 2026 faz todo major ≥27 LTS — paridade não é regra."""
    report = check_node_parity(_types_repo(tmp_path, {_TYPES_KEY: version}))
    assert report.divergences == []
    assert report.types_node == {f"frontend/package-lock.json#{_TYPES_KEY}": version}


def test_types_node_acima_do_runtime_reprova(tmp_path: Path) -> None:
    assert _divergences(_types_repo(tmp_path, {_TYPES_KEY: "27.0.0"})) == [
        f"frontend/package-lock.json#{_TYPES_KEY}: @types/node '27.0.0' → major 27; esperado "
        "major ≤ 26 (frontend/.nvmrc) — types acima do runtime liberam API que prod não tem; "
        "suba o runtime antes, em PR humano (.nvmrc + Dockerfile + compose) — não comite no "
        "branch do Dependabot; o PR dele fica verde no rebase"
    ]


def test_types_node_aninhado_acima_do_runtime_reprova(tmp_path: Path) -> None:
    nested = "node_modules/some-dep/node_modules/@types/node"
    found = _divergences(_types_repo(tmp_path, {_TYPES_KEY: "26.6.4", nested: "28.1.0"}))
    assert [d.split(":")[0] for d in found] == [f"frontend/package-lock.json#{nested}"]
    assert found[0].endswith("fixe a cópia aninhada com `overrides` no package.json")


@pytest.mark.parametrize("version", [None, "latest", ""])
def test_types_node_sem_versao_mensuravel_reprova(tmp_path: Path, version: object) -> None:
    found = _divergences(_types_repo(tmp_path, {_TYPES_KEY: version}))
    assert len(found) == 1 and "sem major numérico" in found[0]


def test_types_node_declarado_sem_copia_no_lock_reprova(tmp_path: Path) -> None:
    _types_repo(tmp_path, {})
    expected = (
        "frontend/package-lock.json: @types/node declarado em frontend/package.json sem cópia "
        "no lock; esperado `packages` com a versão"
    )
    assert _divergences(tmp_path) == [expected]
    (tmp_path / "frontend/package-lock.json").unlink()
    assert _divergences(tmp_path) == [expected]


def test_app_sem_types_node_nao_tem_o_que_medir(tmp_path: Path) -> None:
    assert check_node_parity(_types_repo(tmp_path, {}, declared=False)).divergences == []


def test_types_node_mede_contra_o_nvmrc_do_proprio_app(tmp_path: Path) -> None:
    """Bump de runtime alinhado libera o major dos types — a unidade é o app."""
    _types_repo(tmp_path, {_TYPES_KEY: "28.0.0"})
    assert main(["--root", str(tmp_path)]) == 1
    _write(tmp_path, "frontend/.nvmrc", "28\n")
    _write(tmp_path, "frontend/Dockerfile", f"FROM node:28-alpine{_DIGEST}\n")
    assert main(["--root", str(tmp_path)]) == 0


# --- Repo real: o gate discrimina sobre os arquivos que o CI de fato lê ---------


def _copy_real_inputs(dest: Path) -> Path:
    for path in walk_repo(_REPO):
        rel = path.relative_to(_REPO).as_posix()
        wanted = (
            path.name.startswith("Dockerfile")
            or is_workflow(rel)
            or bool(_COMPOSE_RE.match(path.name))
            or (
                rel.count("/") == 1 and path.name in {"package.json", "package-lock.json", ".nvmrc"}
            )
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
    assert {w.split("#")[0] for w in report.types_node} == {
        "frontend/package-lock.json",
        "frontend-ops/package-lock.json",
    }


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
    head, job = text.split("\n  frontend-checks:\n", 1)
    job = job.replace("node-version-file: frontend/.nvmrc", 'node-version: "20"', 1)
    (root / ci).write_text(f"{head}\n  frontend-checks:\n{job}")
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


def test_repo_real_types_node_acima_do_runtime_reprova(tmp_path: Path) -> None:
    """Mutação no lock real: o PR de major de @types/node do Dependabot fica vermelho."""
    root = _copy_real_inputs(tmp_path)
    lock_path = root / "frontend/package-lock.json"
    lock = json.loads(lock_path.read_text())
    assert node_major(lock["packages"][_TYPES_KEY]["version"]) <= 26
    lock["packages"][_TYPES_KEY]["version"] = "27.0.0"
    lock_path.write_text(json.dumps(lock))
    found = _divergences(root)
    assert len(found) == 1
    assert found[0].startswith(f"frontend/package-lock.json#{_TYPES_KEY}: @types/node '27.0.0'")


def test_repo_real_lint_sem_setup_node_reprova(tmp_path: Path) -> None:
    """Mutação no ci.yml real: os hooks `node -e`/`npx` do Lint voltam ao Node do runner."""
    root = _copy_real_inputs(tmp_path)
    ci = root / ".github/workflows/ci.yml"
    workflow = yaml.safe_load(ci.read_text())
    steps = workflow["jobs"]["lint-all"]["steps"]
    kept = [st for st in steps if not str(st.get("uses", "")).startswith("actions/setup-node@")]
    assert len(steps) - len(kept) == 1
    workflow["jobs"]["lint-all"]["steps"] = kept
    ci.write_text(yaml.safe_dump(workflow, sort_keys=False))
    found = _divergences(root)
    assert len(found) == 1
    assert found[0].startswith(".github/workflows/ci.yml#lint-all: step ")
    assert "chama `pre-commit` no Node do runner" in found[0]


def _groups_carrying_types_node_major(update: dict[str, object]) -> list[str]:
    carrying = []
    for name, group in (update.get("groups") or {}).items():
        majors = "major" in group.get("update-types", ["major"])
        matches = any(fnmatch.fnmatch("@types/node", p) for p in group.get("patterns", []))
        excluded = any(fnmatch.fnmatch("@types/node", p) for p in group.get("exclude-patterns", []))
        if majors and matches and not excluded:
            carrying.append(name)
    return carrying


def test_dependabot_isola_o_major_de_types_node() -> None:
    """Agrupado, o major vermelho de @types/node travaria eslint/prettier junto."""
    config = yaml.safe_load((_REPO / ".github/dependabot.yml").read_text())
    npm = [u for u in config["updates"] if u["package-ecosystem"] == "npm"]
    assert npm and all(_groups_carrying_types_node_major(u) == [] for u in npm)


def test_hook_roda_sempre_e_nao_e_pulado_no_ci() -> None:
    config = yaml.safe_load((_REPO / ".pre-commit-config.yaml").read_text())
    hooks = {h["id"]: h for repo in config["repos"] for h in repo["hooks"]}
    hook = hooks["node-version-parity"]
    assert hook["entry"] == "python3 dev/check_node_version_parity.py"
    assert hook.get("always_run") is True and "stages" not in hook
    ci = (_REPO / ".github/workflows/ci.yml").read_text()
    skip_lines = [line for line in ci.splitlines() if line.strip().startswith("SKIP:")]
    assert skip_lines and all("node-version-parity" not in line for line in skip_lines)
