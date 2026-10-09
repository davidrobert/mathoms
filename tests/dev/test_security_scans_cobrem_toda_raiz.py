"""Os scans de `security.yml` cobrem toda raiz versionada, não só a que existia
quando o filtro foi escrito (ADR-230 §Emenda 2026-10-08).

Até 2026-10-08 o `npm-audit-prod` rodava com `working-directory: frontend` e
o filtro só olhava `frontend/package*.json`: o `frontend-ops/` travou next
16.3.4 (RCE CRITICAL, GHSA-vcvr-r3jv-pc5j) por 8 dias com `Security green`
verde. A classe é "raiz nova não entra no gate", então o universo vem do
`git ls-files`, nunca de uma lista fixada aqui. Sem rede."""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github/workflows/security.yml"
NPM_JOBS = ("npm-audit-prod", "npm-audit-dev")


def _versionados(pattern: str) -> list[str]:
    saida = subprocess.run(
        ["git", "ls-files", pattern], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout
    return saida.split()


def _raizes_npm() -> list[str]:
    raizes = sorted(str(PurePosixPath(p).parent) for p in _versionados("*package-lock.json"))
    assert raizes, "git ls-files não achou package-lock.json — âncora do universo quebrou"
    return raizes


def _workflow() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _passo(job: str, step_id: str) -> dict[str, Any]:
    return next(s for s in _workflow()["jobs"][job]["steps"] if s.get("id") == step_id)


def _grupos_do_filtro() -> dict[str, list[str]]:
    return yaml.safe_load(_passo("changes", "filter")["with"]["files_yaml"])


def _casa(path: str, glob: str) -> bool:
    """`**/X` do changed-files também casa X na raiz; o `fnmatch` sozinho não."""
    if fnmatch.fnmatchcase(path, glob):
        return True
    return glob.startswith("**/") and fnmatch.fnmatchcase(path, glob[3:])


def _grupo_npm_da_raiz(raiz: str) -> str | None:
    alvo = {f"{raiz}/package.json", f"{raiz}/package-lock.json"}
    for nome, globs in _grupos_do_filtro().items():
        if nome.startswith("npm_") and alvo <= set(globs):
            return nome
    return None


@pytest.mark.parametrize("raiz", _raizes_npm())
class TestTodaRaizNpmEAuditada:
    def test_tem_grupo_proprio_no_filtro(self, raiz: str) -> None:
        assert _grupo_npm_da_raiz(raiz), (
            f"`{raiz}/package-lock.json` é versionado e nenhum grupo `npm_*` do "
            f"filtro do `changes` cobre `{raiz}/package.json` + `{raiz}/package-lock.json`"
        )

    def test_o_grupo_poe_a_raiz_no_npm_dirs(self, raiz: str) -> None:
        """A linha que acrescenta a raiz tem de ler o grupo DELA — trocar o
        `_any_changed` de linha audita a raiz errada calado."""
        grupo = _grupo_npm_da_raiz(raiz)
        script = _passo("changes", "set")["run"].splitlines()
        linhas = [ln for ln in script if f"npm_dirs+=({raiz})" in ln]
        assert linhas, f"nenhuma linha do `Set outputs` faz `npm_dirs+=({raiz})`"
        assert all(
            f"{grupo}_any_changed" in ln for ln in linhas
        ), f"`npm_dirs+=({raiz})` não é condicionado por `{grupo}_any_changed`: {linhas}"
        assert all(
            '"$force" == "true"' in ln for ln in linhas
        ), f"`{raiz}` saiu do schedule/dispatch — a deriva da main fica sem cobertura"


@pytest.mark.parametrize("job", NPM_JOBS)
class TestJobsNpmAuditamARaizDaMatrix:
    def test_matrix_vem_do_npm_dirs(self, job: str) -> None:
        cfg = _workflow()["jobs"][job]
        assert cfg["strategy"]["matrix"]["dir"] == "${{ fromJSON(needs.changes.outputs.npm_dirs) }}"
        assert cfg["strategy"]["fail-fast"] is False, "fail-fast esconde a 2ª raiz vermelha"

    def test_roda_na_raiz_da_leg(self, job: str) -> None:
        """Era `working-directory: frontend` fixo — a origem do incidente."""
        cfg = _workflow()["jobs"][job]
        assert cfg["defaults"]["run"]["working-directory"] == "${{ matrix.dir }}"

    def test_pula_matrix_vazia_antes_de_expandir(self, job: str) -> None:
        """Matrix vazia é erro do runner, não skip — o `if` precisa barrar antes."""
        assert _workflow()["jobs"][job]["if"] == "needs.changes.outputs.npm_dirs != '[]'"


def _dockerfiles() -> list[str]:
    achados = _versionados("*Dockerfile*")
    assert achados, "git ls-files não achou Dockerfile — âncora do universo quebrou"
    return achados


@pytest.mark.parametrize("dockerfile", _dockerfiles())
def test_todo_dockerfile_versionado_dispara_o_trivy_config(dockerfile: str) -> None:
    """Mesma classe no grupo `iac`: listava `frontend/` e `backend/` (que nem
    existe) e deixava de fora `frontend-ops/`, `pipeline-service/` e
    `services/pipeline-service-go/`."""
    globs = _grupos_do_filtro()["iac"]
    assert any(_casa(dockerfile, g) for g in globs), f"`{dockerfile}` fora do grupo `iac`: {globs}"
