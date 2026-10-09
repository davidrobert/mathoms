"""Refresh do lock de actions (ADR-320 §Emenda 2026-10-09): único ponto com rede, tudo-ou-nada, offline quando nenhum ref falta. A API do GitHub é um fake injetado — nenhum teste chama `gh`."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from dev import check_action_inputs as gate
from dev import refresh_actions_lock as mod

SHA_A = "a" * 40
SHA_TAG = "c" * 40
SHA_OBJ = "d" * 40
MANIFEST = "name: x\ninputs:\n  b: {description: livre}\n  a: {deprecationMessage: use b}\nruns:\n  using: node24\n  main: x.js\n"


class FakeApi:
    """Responde por path; path sem resposta é 404 (None). Registra cada chamada."""

    def __init__(self, routes: dict[str, str]) -> None:
        self.routes = routes
        self.calls: list[str] = []

    def __call__(self, path: str, raw: bool = False) -> str | None:
        self.calls.append(path)
        return self.routes.get(path)


def _ref_obj(type_: str, sha: str) -> str:
    return json.dumps({"object": {"type": type_, "sha": sha}})


def _no_network(path: str, raw: bool = False) -> str | None:
    raise AssertionError(f"refresh abriu rede sem ref faltando: {path}")


def test_sem_ref_faltando_so_poda_e_nao_abre_rede() -> None:
    entry = gate.LockEntry("node24", ("x",))
    lock = {"o/r@v1": entry, "o/velha@v1": entry}
    assert mod.refresh_lock(["o/r@v1"], lock, _no_network) == {"o/r@v1": entry}


def test_ref_faltando_busca_ele_e_rele_as_tags_mas_nao_o_sha_travado() -> None:
    api = FakeApi(
        {
            f"repos/o/novo/contents/sub/action.yml?ref={SHA_A}": MANIFEST,
            "repos/o/tag/git/ref/tags/v1": _ref_obj("commit", SHA_TAG),
            f"repos/o/tag/contents/action.yml?ref={SHA_TAG}": MANIFEST,
        }
    )
    old = gate.LockEntry("node16", ("velho",))
    lock = {"o/tag@v1": old, f"o/sha@{'b' * 40}": old}
    new = mod.refresh_lock([f"o/novo/sub@{SHA_A}", "o/tag@v1", f"o/sha@{'b' * 40}"], lock, api)
    assert new[f"o/novo/sub@{SHA_A}"] == gate.LockEntry("node24", ("a", "b"), ("a",), None)
    assert new["o/tag@v1"] == gate.LockEntry("node24", ("a", "b"), ("a",), SHA_TAG)
    assert new[f"o/sha@{'b' * 40}"] is old, "SHA é imutável: não se relê"
    assert not any("o/sha" in call for call in api.calls)


def test_tag_anotada_e_descascada_ate_o_commit() -> None:
    api = FakeApi(
        {
            "repos/o/r/git/ref/tags/v2": _ref_obj("tag", SHA_OBJ),
            f"repos/o/r/git/tags/{SHA_OBJ}": _ref_obj("commit", SHA_TAG),
        }
    )
    assert mod.resolve_tag_sha(api, "o/r", "v2") == SHA_TAG


def test_ref_de_branch_e_recusado() -> None:
    """`@main` anda sem PR: um lock dele é falso por construção."""
    with pytest.raises(mod.RefreshError, match="não é tag nem SHA"):
        mod.build_entry(FakeApi({}), "o/r@main")


def test_action_yaml_e_o_fallback_do_action_yml() -> None:
    api = FakeApi({f"repos/o/r/contents/action.yaml?ref={SHA_A}": MANIFEST})
    assert mod.build_entry(api, f"o/r@{SHA_A}").runs_using == "node24"
    assert api.calls[0].endswith(f"action.yml?ref={SHA_A}")


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("inputs: [a, b]\nruns: {using: node24}\n", "deveria ser mapping"),
        ("inputs:\n  'a b': {}\nruns: {using: node24}\n", "nome de input fora"),
        ("inputs: {}\n", "sem `runs.using`"),
        ("- lista\n", "sem `runs.using`"),
        ("inputs: {}\nruns: {using: node24}\n" + "#" * mod.MAX_MANIFEST_BYTES, "bytes"),
    ],
)
def test_manifesto_malformado_aborta(text: str, fragment: str) -> None:
    with pytest.raises(mod.RefreshError, match=fragment):
        mod.parse_manifest(text, "o/r@v1", None)


def test_manifesto_sem_inputs_e_valido() -> None:
    assert mod.parse_manifest("runs: {using: composite, steps: []}\n", "o/r@v1", None).inputs == ()


def test_falha_de_rede_nao_escreve_nada(tmp_path: Path) -> None:
    """403/5xx/timeout abortam o refresh inteiro: lock byte-idêntico, exit ≠ 0."""
    lock_path = tmp_path / "actions.lock.yml"
    lock_path.write_text("# lock anterior\n{}\n", encoding="utf-8")
    before = lock_path.read_bytes()

    def broken(path: str, raw: bool = False) -> str | None:
        raise mod.RefreshError(f"gh api {path}: rc=1 HTTP 403")

    assert mod.main([], api=broken, lock_path=lock_path) == 2
    assert lock_path.read_bytes() == before


def test_refresh_duas_vezes_nao_gera_diff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "w.yml").write_text(f"jobs:\n  j:\n    steps:\n      - uses: o/r@{SHA_A}\n")
    monkeypatch.setattr(mod, "collect_step_uses", lambda: gate.collect_step_uses(workflow_dir))
    api = FakeApi({f"repos/o/r/contents/action.yml?ref={SHA_A}": MANIFEST})
    lock_path = tmp_path / "actions.lock.yml"
    mod.main([], api=api, lock_path=lock_path)
    first = lock_path.read_bytes()
    assert mod.main([], api=_no_network, lock_path=lock_path) == 0
    assert lock_path.read_bytes() == first


@pytest.mark.parametrize(
    ("returncode", "stderr", "expected"),
    [(0, "", "corpo"), (1, "gh: Not Found (HTTP 404)", None)],
)
def test_gh_api_traduz_404_em_none(
    monkeypatch: pytest.MonkeyPatch, returncode: int, stderr: str, expected: str | None
) -> None:
    done = subprocess.CompletedProcess([], returncode, stdout="corpo", stderr=stderr)
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: done)
    assert mod.gh_api("repos/o/r") == expected


@pytest.mark.parametrize(
    "outcome",
    [
        subprocess.CompletedProcess([], 1, stdout="", stderr="gh: Forbidden (HTTP 403)"),
        subprocess.TimeoutExpired(["gh"], mod.GH_TIMEOUT_S),
    ],
)
def test_gh_api_aborta_em_403_e_timeout(monkeypatch: pytest.MonkeyPatch, outcome: object) -> None:
    def fake_run(*args: object, **kwargs: object) -> object:
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    with pytest.raises(mod.RefreshError):
        mod.gh_api("repos/o/r")


def test_path_e_ref_saem_quoted() -> None:
    api = FakeApi({})
    with pytest.raises(mod.RefreshError):
        mod.resolve_tag_sha(api, "o/r", "v1?x=1")
    assert api.calls == ["repos/o/r/git/ref/tags/v1%3Fx%3D1"]


@pytest.mark.parametrize(
    ("uses", "expected"),
    [
        ("actions/stale@v11", ("actions/stale", "", "v11")),
        ("github/codeql-action/init@deadbeef", ("github/codeql-action", "init", "deadbeef")),
    ],
)
def test_split_uses_separa_subpath(uses: str, expected: tuple[str, str, str]) -> None:
    assert mod.split_uses(uses) == expected
