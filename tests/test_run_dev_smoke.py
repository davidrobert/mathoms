"""Smoke tests para ``python -m pipeline.run_dev`` (CLI fina do orchestrator)."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def minimal_tenant(tmp_path: Path) -> Path:
    """Tenant vazio com config mínima para E3 não explodir no import."""
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    (cfg / "pipeline.json").write_text('{"reconciliation": {}}', encoding="utf-8")
    (cfg / "family_members.json").write_text("{}", encoding="utf-8")
    (cfg / "institutions.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_run_dev_help_exits_zero():
    from pipeline.run_dev import main

    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_run_dev_e3_empty_tenant(minimal_tenant: Path, capsys):
    """E3 sem extracts pode falhar o stage; o processo não deve abortar sem SystemExit tratado."""
    from pipeline.run_dev import main

    # Restore cwd-sensitive scripts after stage (e3 mutates globals)
    from scripts.e3_reconcile import _init_config as e3_init, _DEFAULT_BASE_DIR as E3_DEFAULT

    try:
        code = main(["--root", str(minimal_tenant), "--stages", "E3"])
    finally:
        e3_init(E3_DEFAULT)

    assert code in (0, 1)
    captured = capsys.readouterr()
    assert '"success"' in captured.out or captured.out.strip().startswith("{")


def test_check_pipeline_boundaries_ok():
    dev_script = _REPO / "dev" / "check_pipeline_boundaries.py"
    assert dev_script.is_file()
    import importlib.util

    spec = importlib.util.spec_from_file_location("_check_bounds", dev_script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    assert mod.main([]) == 0
