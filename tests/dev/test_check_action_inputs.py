"""Gate de input de action (ADR-320 §Emenda 2026-10-09): `with:` com chave que o action.yml do ref não declara reprova — o runner só avisa e segue sem o efeito, e foi assim que o `exempt-pr-authors` do stale.yml deixou o stale fechar 8 PRs do Dependabot. 100% offline."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from dev import check_action_inputs as mod

REAL_STALE = mod.WORKFLOW_DIR / "stale.yml"
STALE = mod.LockEntry("node24", ("days-before-pr-stale", "exempt-pr-labels", "repo-token"))
LOCK = {
    "actions/stale@v11": STALE,
    "o/docker-action@v1": mod.LockEntry("docker", ("alvo",)),
    "o/velha@v2": mod.LockEntry("node24", ("novo", "antigo"), deprecated_inputs=("antigo",)),
}


def _workflow(tmp_path: Path, steps: list[dict], **job_extra: object) -> Path:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    job = {"runs-on": "ubuntu-latest", "steps": steps, **job_extra}
    doc = {"jobs": {"job-a": job}}
    (workflow_dir / "fixture.yml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    return workflow_dir


def _check(workflow_dir: Path, lock: mod.Lock) -> list[str]:
    return [v.format() for v in mod.check_all(mod.collect_step_uses(workflow_dir), lock)]


def _only(tmp_path: Path, step: dict, lock: mod.Lock | None = None) -> list[str]:
    """Lock reduzido ao ref do step: as outras entradas do LOCK virariam órfãs."""
    full = LOCK if lock is None else lock
    return _check(_workflow(tmp_path, [step]), {k: v for k, v in full.items() if k == step["uses"]})


def test_input_inexistente_reprova_com_ofensor_e_inputs_validos(tmp_path: Path) -> None:
    (message,) = _only(tmp_path, {"uses": "actions/stale@v11", "with": {"exempt-pr-authors": "x"}})
    assert message.startswith("fixture.yml::job-a [step #0] actions/stale@v11 — ")
    assert "'exempt-pr-authors' não existe" in message
    assert "'exempt-pr-labels'" in message, "a mensagem precisa trazer o shape esperado"


def test_input_declarado_passa_e_a_caixa_nao_importa(tmp_path: Path) -> None:
    """O runner compara com OrdinalIgnoreCase: `Repo-Token` é o mesmo input que `repo-token`."""
    step = {"uses": "actions/stale@v11", "with": {"Repo-Token": "t", "exempt-pr-labels": "x"}}
    assert _only(tmp_path, step) == []


def test_args_e_entrypoint_so_valem_em_action_docker(tmp_path: Path) -> None:
    docker = {"uses": "o/docker-action@v1", "with": {"args": "-v", "entryPoint": "/x", "alvo": "y"}}
    assert _only(tmp_path, docker) == []
    (message,) = _only(tmp_path, {"uses": "actions/stale@v11", "with": {"args": "-v"}})
    assert "'args' não existe" in message


def test_input_deprecado_reprova(tmp_path: Path) -> None:
    assert _only(tmp_path, {"uses": "o/velha@v2", "with": {"novo": "1"}}) == []
    (message,) = _only(tmp_path, {"uses": "o/velha@v2", "with": {"antigo": "1"}})
    assert "'antigo' está deprecado" in message


def test_bump_sem_refresh_reprova_o_ref_novo_e_o_orfao(tmp_path: Path) -> None:
    """v11→v12 sem refresh: os inputs do ref novo não foram lidos e não podem passar calados."""
    messages = _check(
        _workflow(tmp_path, [{"uses": "actions/stale@v12"}]), {"actions/stale@v11": STALE}
    )
    assert any("actions/stale@v12" in m and mod.REFRESH_CMD in m for m in messages)
    assert any("actions/stale@v11" in m and "nenhum workflow usa" in m for m in messages)
    assert any("dependabot.yml" in m for m in messages), "aponta o procedimento do Dependabot"


def test_step_sem_with_tambem_exige_o_ref_no_lock(tmp_path: Path) -> None:
    """Sem `with:` não há input a errar hoje, mas o próximo `with:` precisa achar o ref já lido."""
    (message,) = _check(_workflow(tmp_path, [{"uses": "actions/checkout@v7"}]), {})
    assert "actions/checkout@v7" in message and "ref fora de" in message


@pytest.mark.parametrize(
    ("step", "job_extra", "fragment"),
    [
        ({"uses": "./.github/actions/minha", "with": {"x": "1"}}, {}, "action local"),
        ({"uses": "docker://alpine:3.20", "with": {"args": "echo"}}, {}, "`docker://`"),
        ({"uses": "actions/checkout"}, {}, "sem `@ref`"),
        (None, {"uses": "o/r/.github/workflows/w.yml@v1", "with": {"x": 1}}, "reusable workflow"),
    ],
)
def test_forma_nao_suportada_reprova_em_vez_de_passar_calada(
    tmp_path: Path, step: dict | None, job_extra: dict, fragment: str
) -> None:
    workflow_dir = _workflow(tmp_path, [step] if step else [], **job_extra)
    (message,) = _check(workflow_dir, {})
    assert "forma não suportada pelo gate" in message and fragment in message


def test_lock_renderizado_e_relido_identico(tmp_path: Path) -> None:
    path = tmp_path / "actions.lock.yml"
    tagged = {**LOCK, "a/b@v1": mod.LockEntry("node24", ("x",), resolved_sha="f" * 40)}
    path.write_text(mod.render_lock(tagged), encoding="utf-8")
    assert mod.load_lock(path) == tagged
    assert path.read_text(encoding="utf-8").startswith("# GERADO por")


def _real_stale_with(tmp_path: Path, extra: dict[str, str]) -> Path:
    doc = yaml.safe_load(REAL_STALE.read_text(encoding="utf-8"))
    steps = doc["jobs"]["stale"]["steps"]
    step = next(s for s in steps if str(s.get("uses", "")).startswith("actions/stale@"))
    step["with"] = {**step["with"], **extra}
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "stale.yml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    return workflow_dir


def test_reintroduzir_exempt_pr_authors_no_stale_real_reprova(tmp_path: Path) -> None:
    """Prova de mutação no workflow e no lock reais: o incidente de origem não volta calado."""
    sites = mod.collect_step_uses(_real_stale_with(tmp_path, {"exempt-pr-authors": "dependabot"}))
    messages = [v.format() for site in sites for v in mod.check_site(site, mod.load_lock())]
    assert any("'exempt-pr-authors' não existe" in m for m in messages), messages


@pytest.mark.parametrize(("key", "flagged"), [("fetch-dept", True), ("Fetch-Depth", False)])
def test_mutacao_em_checkout_real(tmp_path: Path, key: str, flagged: bool) -> None:
    step = {"uses": "actions/checkout@v7", "with": {key: 0}}
    site = mod.collect_step_uses(_workflow(tmp_path, [step]))[0]
    assert bool(mod.check_site(site, mod.load_lock())) is flagged


def test_repo_atual_passa_e_lock_espelha_os_workflows() -> None:
    violations = mod.check_all(mod.collect_step_uses(), mod.load_lock())
    assert violations == [], [v.format() for v in violations]
