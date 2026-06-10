"""Fixtures do eval de lineage: payload E5 dogfood rodado UMA vez por sessão (PII-zero, fixtures sintéticas) — cada caso muta um deepcopy em memória."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.pipeline_golden_substrate import (
    load_fixture,
    run_dogfood_pipeline,
    write_e5_config,
)

_REPO = Path(__file__).resolve().parents[2]
_DOGFOOD = _REPO / "tests" / "fixtures" / "pipeline_golden" / "dogfood"


@pytest.fixture(scope="session")
def dogfood_e5(tmp_path_factory) -> dict:
    root = tmp_path_factory.mktemp("lineage_eval_dogfood")
    write_e5_config(root)
    return run_dogfood_pipeline(
        root,
        raw_baseline=load_fixture(_DOGFOOD / "baseline-1.5.json"),
        e2_extracts={
            "fict_a": load_fixture(_DOGFOOD / "extrato-a-2_extract.json"),
            "fict_b": load_fixture(_DOGFOOD / "extrato-b-2_extract.json"),
        },
    )
