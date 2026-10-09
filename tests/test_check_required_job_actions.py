"""Gate de runtime de action (ADR-320 §Emendas 2026-08-03 e 2026-10-09 (runtime pelo lock)): fato lido do lock pelo `uses:` exato, só node24 em job required, piso node24/composite/docker em todo workflow — prova de mutação em cada mecanismo, 100% offline."""

from __future__ import annotations

from pathlib import Path

from dev import check_required_job_actions as gate
from dev.check_action_inputs import LockEntry

REQUIRED = "required-job"
FREE = "free-job"


def _workflow(tmp_path: Path, job: str, *uses: str) -> Path:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    steps = "".join(f"      - uses: {u}\n" for u in uses)
    body = f"jobs:\n  {job}:\n    runs-on: ubuntu-latest\n    steps:\n{steps}"
    (workflow_dir / "fixture.yml").write_text(body, encoding="utf-8")
    return workflow_dir


def _lock(**runtimes: str) -> dict[str, LockEntry]:
    return {uses: LockEntry(runs_using=runs, inputs=()) for uses, runs in runtimes.items()}


def _registry(*admitted: str) -> dict:
    return {"actions": list(admitted), "required_jobs": {"fixture.yml": [REQUIRED]}}


def _reasons(workflow_dir: Path, registry: dict, lock: dict) -> list[str]:
    sites = gate.collect_step_uses(workflow_dir)
    found = gate.check_required(sites, lock, registry) + gate.check_runtime_floor(sites, lock)
    return [v.reason for v in found]


def test_runtime_e_lido_pelo_ref_exato(tmp_path):
    """Busca por `owner/repo` acharia o v1 (ou nada) e calaria o node20 do v2."""
    lock = _lock(**{"org/a@v1": "node24", "org/a@v2": "node20"})
    assert _reasons(_workflow(tmp_path, FREE, "org/a@v1"), _registry(), lock) == []
    reasons = _reasons(_workflow(tmp_path, FREE, "org/a@v2"), _registry(), lock)
    assert len(reasons) == 1 and "'node20'" in reasons[0]


def test_ref_fora_do_lock_reprova_sem_depender_do_action_inputs(tmp_path):
    reasons = _reasons(_workflow(tmp_path, FREE, "org/a@v3"), _registry(), _lock())
    assert len(reasons) == 1
    assert "runtime desconhecido" in reasons[0] and gate.REFRESH_CMD in reasons[0]


def test_required_aceita_node24_admitida(tmp_path):
    lock = _lock(**{"org/a@v1": "node24"})
    assert _reasons(_workflow(tmp_path, REQUIRED, "org/a@v1"), _registry("org/a"), lock) == []


def test_required_reprova_composite_e_docker(tmp_path):
    for runtime in ("composite", "docker"):
        lock = _lock(**{"org/a@v1": runtime})
        reasons = _reasons(_workflow(tmp_path, REQUIRED, "org/a@v1"), _registry("org/a"), lock)
        assert len(reasons) == 1 and "vedado em job required" in reasons[0], runtime


def test_required_reprova_docker_url_pela_forma(tmp_path):
    reasons = _reasons(_workflow(tmp_path, REQUIRED, "docker://alpine:3"), _registry(), _lock())
    assert reasons == ["`docker://` vedado em job required (ADR-320 §Emenda 2026-08-03)"]


def test_required_reprova_action_nao_admitida(tmp_path):
    lock = _lock(**{"org/a@v1": "node24"})
    reasons = _reasons(_workflow(tmp_path, REQUIRED, "org/a@v1"), _registry(), lock)
    assert reasons == ["não registrada em third-party-actions.yml"]


def test_piso_reprova_node20_fora_de_required_e_nao_duplica_em_required(tmp_path):
    lock = _lock(**{"org/a@v1": "node20"})
    for job in (FREE, REQUIRED):
        reasons = _reasons(_workflow(tmp_path, job, "org/a@v1"), _registry("org/a"), lock)
        assert len(reasons) == 1 and "fora do piso" in reasons[0], job


def test_docker_fora_de_required_passa(tmp_path):
    lock = _lock(**{"org/d@v1": "docker"})
    workflow_dir = _workflow(tmp_path, FREE, "org/d@v1", "docker://alpine:3")
    assert _reasons(workflow_dir, _registry(), lock) == []


def test_forma_local_reprova_em_vez_de_passar_calada(tmp_path):
    reasons = _reasons(_workflow(tmp_path, FREE, "./.github/actions/x"), _registry(), _lock())
    assert len(reasons) == 1 and "forma sem runtime verificável" in reasons[0]


def test_registro_com_fato_de_runtime_reprova():
    """Entrada em mapa (`runs_using` copiado de volta) é a segunda fonte que diverge do lock."""
    registry = {"actions": {"actions/checkout": {"runs_using": "node24"}}, "required_jobs": {}}
    violations = gate.check_all(registry, {}, [])
    assert len(violations) == 1 and "deve ser lista" in violations[0].reason


def test_registro_com_chave_de_topo_desconhecida_reprova():
    registry = {"actions": [], "required_jobs": {}, "verified_at": "2026-10-09"}
    violations = gate.check_registry_shape(registry)
    assert len(violations) == 1 and "verified_at" in violations[0].reason


def _real():
    return gate.load_registry(), gate.load_lock(), gate.collect_step_uses(gate.WORKFLOW_DIR)


def test_repo_real_esta_verde():
    assert gate.check_all(*_real()) == []


def test_repo_real_pega_docker_e_node20_injetados_no_lock():
    """Mutação sobre o lock real: prova que o verde anterior não vem de fecho ou universo vazio."""
    registry, lock, sites = _real()
    required = gate._required_sites(sites, registry)
    assert required, "fecho required sem `uses:` — teste vácuo"
    target = required[0].uses
    for runtime, expected in (("docker", "vedado em job required"), ("node20", "fora do piso")):
        mutated = {**lock, target: LockEntry(runs_using=runtime, inputs=())}
        reasons = [
            v.reason for v in gate.check_all(registry, mutated, sites) if v.action_ref == target
        ]
        assert reasons and all(expected in r for r in reasons), runtime


def _write_needs_chain(tmp_path: Path) -> Path:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    (workflow_dir / "fixture.yml").write_text(
        """
jobs:
  base: {runs-on: ubuntu-latest, steps: []}
  mid: {runs-on: ubuntu-latest, needs: base, steps: []}
  agg: {runs-on: ubuntu-latest, needs: [mid], steps: []}
  fora: {runs-on: ubuntu-latest, steps: []}
""",
        encoding="utf-8",
    )
    return workflow_dir


def test_fecho_transitivo_nao_declarado_reprova(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "WORKFLOW_DIR", _write_needs_chain(tmp_path))
    monkeypatch.setattr(gate, "CLOSURE_ROOTS", {"fixture.yml": "agg"})
    registry = {"actions": [], "required_jobs": {"fixture.yml": ["agg", "mid"]}}
    violations = gate.check_closure_declared(registry)
    assert [v.job for v in violations] == ["base"]


def test_fecho_declarado_passa_e_ignora_job_fora_do_fecho(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "WORKFLOW_DIR", _write_needs_chain(tmp_path))
    monkeypatch.setattr(gate, "CLOSURE_ROOTS", {"fixture.yml": "agg"})
    registry = {"actions": [], "required_jobs": {"fixture.yml": ["agg", "mid", "base"]}}
    assert gate.check_closure_declared(registry) == []


def test_registro_real_declara_o_fecho_real():
    assert gate.check_closure_declared(gate.load_registry()) == []


def test_registro_real_pega_job_do_fecho_removido():
    """Mutação: tirar do registro um job que o `all-green` de fato exige reprova
    — prova que o teste anterior não passa por fecho vazio."""
    closure = gate.required_closure(gate.WORKFLOW_DIR / "ci.yml", "all-green")
    assert len(closure) > 2, f"fecho suspeito de vacuidade: {closure}"
    registry = gate.load_registry()
    registry["required_jobs"]["ci.yml"].remove("frontend-ops-checks")
    violations = gate.check_closure_declared(registry)
    assert [v.job for v in violations] == ["frontend-ops-checks"]
