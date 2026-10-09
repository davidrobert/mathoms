"""PR do Dependabot fica fora do stale por uma label que o labeler não consegue tirar.

O `actions/stale` não filtra por autor: o `exempt-pr-authors` do stale.yml era
input inexistente (`Unexpected input(s)` em todo run) e o stale fechou 8 PRs do
Dependabot (#2006–#2015), cada fechamento virando ignore da release. A isenção
passou a ser por label, e o labeler roda com `sync-labels: true`, que remove
toda label DECLARADA no labeler.yml que não case com o PR — então a label de
isenção precisa casar todo branch `dependabot/…` por `head-branch`, e nenhum
branch humano.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
STALE_YML = REPO_ROOT / ".github" / "workflows" / "stale.yml"
LABELER_YML = REPO_ROOT / ".github" / "labeler.yml"

EXEMPTION_LABEL = "dependabot"
DEPENDABOT_BRANCHES = [
    "dependabot/github_actions/actions-first-party-major-8a469ff805",
    "dependabot/npm_and_yarn/frontend-ops/ops-patch-and-minor-3f2a1b",
    "dependabot/docker/pipeline-service/python-3.12-slim",
    "dependabot/pip/backend/litellm-gte-1.104",
]
HUMAN_BRANCHES = ["agent/stale-dependabot-exempt/20261009-0748", "claude/busy-roentgen-41a015"]
# Dependências de manifest que um PR humano também toca — a label `dependency`
# casa por path e NÃO pode isentar, senão feature que adiciona lib nunca fecha.
PATH_LABELS = {"dependency"}


def _stale_inputs() -> dict[str, object]:
    workflow = yaml.safe_load(STALE_YML.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["stale"]["steps"]
    stale_step = next(s for s in steps if str(s.get("uses", "")).startswith("actions/stale@"))
    return stale_step["with"]


def _exempt_pr_labels() -> set[str]:
    return {label.strip() for label in str(_stale_inputs()["exempt-pr-labels"]).split(",")}


def _head_branch_regexes(label_rule: list[dict[str, object]]) -> list[str]:
    """Regexes de `head-branch` no topo da regra — lá elas entram no `any` (OR)."""
    assert all("all" not in item for item in label_rule), f"`all:` muda a semântica: {label_rule!r}"
    raw = [item["head-branch"] for item in label_rule if "head-branch" in item]
    return [regex for value in raw for regex in ([value] if isinstance(value, str) else value)]


def _labeler_keeps(label: str, branch: str) -> bool:
    config = yaml.safe_load(LABELER_YML.read_text(encoding="utf-8"))
    return any(re.search(rx, branch) for rx in _head_branch_regexes(config[label]))


def test_stale_step_uses_no_author_filter() -> None:
    inputs = _stale_inputs()
    assert not any(
        "author" in key for key in inputs
    ), f"actions/stale não tem filtro por autor; got {sorted(inputs)!r}"


def test_exemption_label_is_exempt_and_path_labels_are_not() -> None:
    exempt = _exempt_pr_labels()
    assert (
        EXEMPTION_LABEL in exempt
    ), f"expected {EXEMPTION_LABEL!r} in exempt-pr-labels, got {exempt!r}"
    assert not exempt & PATH_LABELS, f"label por path isenta PR humano: {exempt & PATH_LABELS!r}"


@pytest.mark.parametrize("branch", DEPENDABOT_BRANCHES)
def test_labeler_keeps_exemption_label_on_dependabot_branch(branch: str) -> None:
    assert _labeler_keeps(
        EXEMPTION_LABEL, branch
    ), f"sync-labels tiraria {EXEMPTION_LABEL!r} de {branch!r}"


@pytest.mark.parametrize("branch", HUMAN_BRANCHES)
def test_labeler_never_applies_exemption_label_to_human_branch(branch: str) -> None:
    assert not _labeler_keeps(EXEMPTION_LABEL, branch), f"{branch!r} ficaria isento do stale"


@pytest.mark.parametrize("branch", DEPENDABOT_BRANCHES)
def test_labeler_keeps_dependency_label_on_dependabot_branch(branch: str) -> None:
    assert _labeler_keeps("dependency", branch), f"sync-labels tiraria 'dependency' de {branch!r}"
