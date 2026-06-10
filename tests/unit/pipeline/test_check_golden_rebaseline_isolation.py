"""Testes do gate de isolamento de rebaseline (A24.l1 · F2-DB5 · G-c)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from dev.check_golden_rebaseline_isolation import (  # noqa: E402
    check_commit_range,
    is_golden,
    is_production,
    violation,
)

_GOLDEN = "tests/fixtures/pipeline_golden/e3/minimal-conta-3_reconciled.json"
_MANIFEST = "tests/fixtures/pipeline_golden/rebaseline_manifest.yaml"
_PRODUCTION = "pipeline/domain/services/patrimonio_calculator.py"
_SCHEMA = "config/schemas/e2_extract.schema.json"


def test_classification():
    assert is_golden(_GOLDEN) and is_golden(_MANIFEST)
    assert is_production(_PRODUCTION) and is_production("scripts/e2/common.py")
    assert not is_production(_SCHEMA)  # contrato, não produção (F2-DB1)
    assert not is_production("backend/tests/test_x.py")  # só backend/app
    assert not is_production("docs/plan/DATA_LINEAGE/_README.md")


def test_mixed_commit_is_violation():
    msg = violation([_GOLDEN, _MANIFEST, _PRODUCTION])
    assert msg is not None
    assert "golden-rebaseline" in msg


def test_golden_plus_manifest_is_legitimate():
    assert violation([_GOLDEN, _MANIFEST]) is None


def test_golden_plus_schema_is_legitimate():
    assert violation([_GOLDEN, _MANIFEST, _SCHEMA]) is None


def test_production_only_is_legitimate():
    assert violation([_PRODUCTION, "backend/app/services/foo.py"]) is None


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "PATH": "/usr/bin:/bin",
            "HOME": str(cwd),
        },
    )


def _commit_files(repo: Path, files: dict[str, str], message: str) -> None:
    for rel, content in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message, "--no-verify")


def test_commit_range_flags_only_mixed_commit(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _commit_files(repo, {"README.md": "base"}, "base")
    _commit_files(repo, {_GOLDEN: "{}", _MANIFEST: "[]"}, "rebaseline isolado")
    _commit_files(repo, {_GOLDEN: "{1}", _PRODUCTION: "x = 1"}, "commit misto")
    monkeypatch.chdir(repo)

    errors = check_commit_range("HEAD~2..HEAD")
    assert len(errors) == 1
    assert "commit" not in errors[0] or "golden" in errors[0]
