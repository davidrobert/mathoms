"""Skip-class incoming_main_docs_only — fail-closed (ADR-322 emenda 2026-08-21)."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dev.incoming_main_docs_only import (
    decide,
    is_docs_only_path,
    paths_are_docs_only,
    should_skip_heavy_jobs,
    smoke_is_fresh,
)

NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
FRESH = {
    "name": "Nightly",
    "status": "completed",
    "conclusion": "success",
    "updatedAt": "2026-08-21T11:00:00Z",
}
STALE = {
    "name": "Nightly",
    "status": "completed",
    "conclusion": "success",
    "updatedAt": "2026-08-19T11:00:00Z",
}
FAILED = {
    "name": "Nightly",
    "status": "completed",
    "conclusion": "failure",
    "updatedAt": "2026-08-21T11:00:00Z",
}


def _skip(**overrides: object) -> bool:
    base: dict[str, object] = {
        "is_merge_commit": True,
        "second_parent_on_main": True,
        "paths": ("docs/adr/322-trem-de-automerge-serializado-identidade-real.md",),
        "smoke_fresh": True,
    }
    base.update(overrides)
    return should_skip_heavy_jobs(
        is_merge_commit=bool(base["is_merge_commit"]),
        second_parent_on_main=bool(base["second_parent_on_main"]),
        paths=tuple(base["paths"]),  # type: ignore[arg-type]
        smoke_fresh=bool(base["smoke_fresh"]),
    )


def test_readme_e_docs_passam_openapi_nao() -> None:
    assert is_docs_only_path("README.md")
    assert is_docs_only_path("docs/adr/322-x.md")
    assert not is_docs_only_path("docs/reference/api/v1/openapi.json")
    assert not is_docs_only_path("pipeline/foo.py")
    assert not is_docs_only_path("config/prompts/parecer_planejador.yaml")


def test_lista_vazia_nao_e_docs() -> None:
    assert not paths_are_docs_only(())
    assert not paths_are_docs_only(("docs/a.md", "ci.yml"))


def test_skip_so_com_todos_os_predicados() -> None:
    assert _skip() is True


def test_rebase_nao_skipa() -> None:
    assert _skip(is_merge_commit=False) is False


def test_segundo_parent_fora_de_main_nao_skipa() -> None:
    assert _skip(second_parent_on_main=False) is False


def test_codigo_no_delta_nao_skipa() -> None:
    assert _skip(paths=("docs/a.md", "pipeline/x.py")) is False


def test_openapi_nao_skipa() -> None:
    assert _skip(paths=("docs/reference/api/v1/openapi.json",)) is False


def test_smoke_velho_ou_ausente_nao_skipa() -> None:
    assert _skip(smoke_fresh=False) is False
    assert smoke_is_fresh([], now=NOW) is False
    assert smoke_is_fresh([STALE], now=NOW) is False
    assert smoke_is_fresh([FAILED], now=NOW) is False
    assert smoke_is_fresh([FRESH], now=NOW) is True


def test_decide_em_repo_sem_merge_e_false(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    assert decide(tmp_path, [FRESH]) is False
