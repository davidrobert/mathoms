"""Grupo do Dependabot que não recebe o que promete reprova (porte da especificidade do core).

Os contrafactuais reproduzem os jobs de 2026-10-09: o /frontend (run 37982474054)
e o pip `/` (run 37982473671) logaram "Skipping X for group 'G' - belongs to more
specific group 'patch-and-minor'" exatamente para os pares esperados aqui. O
/frontend-ops (run 37982475686) e o github-actions (run 37982489690) logaram zero.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.check_dependabot_groups import (  # noqa: E402
    DEPENDABOT_YML,
    assign_members,
    config_violations,
    entry_violations,
    parse_group,
    pattern_score,
    wildcard_match,
)

FRONTEND_GROUPS_2026_10_09 = {
    "next-and-react": {"patterns": ["next", "react", "react-*", "@types/react*"]},
    "eslint-and-types": {
        "patterns": ["eslint*", "@typescript-eslint/*", "@types/*", "prettier*"],
        "exclude-patterns": ["@types/node"],
    },
    "vitest-and-test": {
        "patterns": ["vitest", "@vitest/*", "@testing-library/*", "@playwright/*", "playwright"]
    },
    "patch-and-minor": {
        "update-types": ["patch", "minor"],
        "exclude-patterns": ["next", "react", "react-dom", "tailwindcss"],
    },
}
# Dependências diretas do /frontend que casam algum padrão acima, mais duas que não casam.
FRONTEND_DEPS = [
    "@playwright/test", "@testing-library/jest-dom", "@testing-library/react",
    "@testing-library/user-event", "@types/node", "@types/pngjs", "@types/react",
    "@types/react-dom", "@typescript-eslint/eslint-plugin", "@typescript-eslint/parser",
    "@vitest/coverage-v8", "eslint", "eslint-plugin-react", "eslint-plugin-react-hooks",
    "next", "react", "react-chartjs-2", "react-dom", "recharts", "vitest",
]  # fmt: skip
FRONTEND_DIVERTED_IN_LOG = {
    "eslint-and-types": {
        "@types/pngjs", "@types/react", "@types/react-dom", "@typescript-eslint/eslint-plugin",
        "@typescript-eslint/parser", "eslint", "eslint-plugin-react", "eslint-plugin-react-hooks",
    },
    "next-and-react": {"@types/react", "@types/react-dom", "react-chartjs-2"},
    "vitest-and-test": {
        "@playwright/test", "@testing-library/jest-dom", "@testing-library/react",
        "@testing-library/user-event", "@vitest/coverage-v8",
    },
}  # fmt: skip


def _groups(rules: dict[str, dict[str, object]]) -> list:
    return [parse_group(name, rule) for name, rule in rules.items()]


def _diverted_by_group(groups: list, deps: list[str]) -> dict[str, set[str]]:
    _, diverted = assign_members(groups, deps)
    found: dict[str, set[str]] = {}
    for group, dep, winner in diverted:
        assert winner == "patch-and-minor", (group, dep, winner)
        found.setdefault(group, set()).add(dep)
    return found


def _real_config() -> dict:
    return yaml.safe_load(DEPENDABOT_YML.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("pattern", "dep", "score"),
    [
        ("eslint", "eslint", 1000),
        ("eslint*", "eslint-plugin-react", 92),
        ("@types/*", "@types/node", 93),
        ("@typescript-eslint/*", "@typescript-eslint/parser", 105),
        ("*", "next", 1),
    ],
)
def test_score_do_padrao_segue_o_core(pattern: str, dep: str, score: int) -> None:
    assert pattern_score(pattern, dep) == score


def test_curinga_casa_sem_caixa_e_ancorado() -> None:
    assert wildcard_match("@types/react*", "@types/react-dom")
    assert wildcard_match("PyTest*", "pytest-asyncio")
    assert not wildcard_match("eslint", "eslint-plugin-react")
    assert not wildcard_match("react-*", "react")


def test_contrafactual_frontend_reproduz_o_log() -> None:
    groups = _groups(FRONTEND_GROUPS_2026_10_09)
    assert _diverted_by_group(groups, FRONTEND_DEPS) == FRONTEND_DIVERTED_IN_LOG
    members, _ = assign_members(groups, FRONTEND_DEPS)
    assert members["vitest-and-test"] == ["vitest"]
    assert members["eslint-and-types"] == []


def test_contrafactual_pip_reproduz_o_log() -> None:
    groups = _groups(
        {
            "pytest": {"patterns": ["pytest*"]},
            "ruff-and-types": {"patterns": ["ruff", "mypy", "types-*"]},
            "patch-and-minor": {
                "update-types": ["patch", "minor"],
                "exclude-patterns": ["fastapi"],
            },
        }
    )
    deps = ["fastapi", "pytest", "pytest-asyncio", "pytest-cov", "pyyaml"]
    assert _diverted_by_group(groups, deps) == {
        "pytest": {"pytest", "pytest-asyncio", "pytest-cov"}
    }
    lines = entry_violations("pip /", groups, deps)
    assert sum("não casa nenhuma dependência" in line for line in lines) == 3


def test_update_types_disjunto_nao_compete_como_no_github_actions() -> None:
    groups = _groups(
        {
            "actions-patch-and-minor": {"update-types": ["patch", "minor"]},
            "actions-first-party-major": {"patterns": ["actions/*"], "update-types": ["major"]},
        }
    )
    deps = ["actions/checkout", "actions/setup-node", "docker/build-push-action"]
    assert entry_violations("github-actions /", groups, deps) == []


def test_exclude_no_catch_all_torna_o_curinga_efetivo_como_no_frontend_ops() -> None:
    groups = _groups(
        {
            "ops-next-and-react": {
                "patterns": ["next", "@types/react*"],
                "update-types": ["patch", "minor"],
            },
            "ops-patch-and-minor": {
                "update-types": ["patch", "minor"],
                "exclude-patterns": ["next", "@types/react*"],
            },
        }
    )
    assert entry_violations("npm /frontend-ops", groups, ["@types/react", "eslint", "next"]) == []


@pytest.mark.parametrize(("catch_all_first", "reprova"), [(True, True), (False, False)])
def test_catch_all_antes_do_nome_exato_atende_primeiro(
    catch_all_first: bool, reprova: bool
) -> None:
    exact = ("next-and-react", {"patterns": ["@types/react"]})
    catch_all = ("patch-and-minor", {"update-types": ["patch", "minor"]})
    ordered = [catch_all, exact] if catch_all_first else [exact, catch_all]
    lines = entry_violations("npm /frontend", _groups(dict(ordered)), ["@types/react"])
    assert any("atendida antes por 'patch-and-minor'" in line for line in lines) is reprova


def test_empate_fica_com_o_grupo_que_vem_antes() -> None:
    """Quem recebeu a dep primeiro passa a valer 1000 (membro explícito) para o seguinte."""
    groups = _groups({"a": {"patterns": ["@types/*"]}, "b": {"patterns": ["@types/*"]}})
    _, diverted = assign_members(groups, ["@types/pngjs"])
    assert diverted == [("b", "@types/pngjs", "a")]


def test_regra_fora_do_porte_falha_alto() -> None:
    with pytest.raises(ValueError, match="dependency-type"):
        parse_group("dev-deps", {"patterns": ["*"], "dependency-type": "development"})


def test_config_real_nao_tem_grupo_inerte() -> None:
    assert config_violations(_real_config(), REPO_ROOT) == []


def test_config_real_le_os_manifests_de_verdade() -> None:
    config = _real_config()
    frontend = next(
        u
        for u in config["updates"]
        if u["package-ecosystem"] == "npm" and u["directory"] == "/frontend"
    )
    frontend["groups"] = {"inerte": {"patterns": ["@testing-library/*"]}, **frontend["groups"]}
    lines = config_violations(config, REPO_ROOT)
    assert lines and all("'inerte'" in line and "patch-and-minor" in line for line in lines)


def test_hook_roda_quando_muda_o_yml_ou_um_manifest() -> None:
    config = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    hook = next(
        h for repo in config["repos"] for h in repo["hooks"] if h["id"] == "dependabot-groups"
    )
    assert hook["entry"] == "python3 dev/check_dependabot_groups.py"
    for path in (".github/dependabot.yml", "frontend/package.json", "frontend-ops/package.json",
                 "requirements.in", "backend/requirements.in", "requirements-dev.txt"):  # fmt: skip
        assert re.search(hook["files"], path), path
