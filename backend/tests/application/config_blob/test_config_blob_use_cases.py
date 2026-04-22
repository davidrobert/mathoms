"""Use cases do agregado ``ConfigBlob`` — testes puros (sem DB)."""

from __future__ import annotations

import pytest

from backend.app.application.config_blob import (
    get_institution_config,
    get_pipeline_config,
    get_report_layout,
    update_institution_config,
    update_pipeline_config,
    update_report_layout,
)
from backend.app.models.config_blob import (
    InstitutionConfig,
    PipelineConfig,
    ReportLayout,
)
from backend.app.schemas.dto.config_blob import (
    InstitutionConfigUpdateCommand,
    PipelineConfigUpdateCommand,
    ReportLayoutUpdateCommand,
)
from backend.tests.fakes import (
    FakeConfigBlobRepository,
    FakeGlobalDefaultsLoader,
)

_PIPELINE_DEFAULT = {
    "llm": {
        "model": "claude-opus-4",
        "max_tokens": 500,
        "confidence_threshold": 0.7,
    },
    "file_limits": {
        "preview_max_chars": 2000,
        "preview_max_rows": 20,
        "min_pdf_bytes": 1024,
        "min_xls_bytes": 40000,
        "min_csv_bytes": 500,
    },
    "reconciliation": {"saldo_diff": 0.01, "mode": "strict"},
    "qa_thresholds": {"score_diff_max": 0.5},
    "artifact_names": {},
    "log_files": {},
    "period_regex": {},
}

_INSTITUTION_DEFAULT = {"banks": {"itau": {"code": "itau"}}}

_LAYOUT_DEFAULT = {"sections": ["summary", "patrimony"]}


def _defaults() -> FakeGlobalDefaultsLoader:
    return FakeGlobalDefaultsLoader(
        json_defaults={
            "pipeline.json": _PIPELINE_DEFAULT,
            "institutions.json": _INSTITUTION_DEFAULT,
        },
        yaml_defaults={"report_layout.yaml": _LAYOUT_DEFAULT},
    )


# ───── PipelineConfig ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_pipeline_falls_back_to_global_default_when_missing():
    repo = FakeConfigBlobRepository()

    resp = await get_pipeline_config("ws-1", repo=repo, defaults=_defaults())

    assert resp.llm.model == "claude-opus-4"
    assert resp.file_limits.preview_max_chars == 2000


@pytest.mark.asyncio
async def test_get_pipeline_returns_workspace_override_when_present():
    repo = FakeConfigBlobRepository()
    custom = dict(_PIPELINE_DEFAULT)
    custom["llm"] = {**_PIPELINE_DEFAULT["llm"], "model": "claude-sonnet-4-6"}
    await repo.upsert("ws-1", PipelineConfig, custom)

    resp = await get_pipeline_config("ws-1", repo=repo, defaults=_defaults())

    assert resp.llm.model == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_update_pipeline_merges_on_top_of_default_when_no_override():
    repo = FakeConfigBlobRepository()
    cmd = PipelineConfigUpdateCommand(qa_thresholds={"score_diff_max": 0.9})

    resp = await update_pipeline_config(cmd, workspace_id="ws-1", repo=repo, defaults=_defaults())

    assert resp.qa_thresholds.score_diff_max == 0.9
    # Campos não fornecidos preservam o default
    assert resp.llm.model == "claude-opus-4"

    persisted = await repo.get_config_json("ws-1", PipelineConfig)
    assert persisted is not None
    assert persisted["qa_thresholds"]["score_diff_max"] == 0.9
    assert persisted["llm"]["model"] == "claude-opus-4"


@pytest.mark.asyncio
async def test_update_pipeline_deep_merges_nested_dicts():
    repo = FakeConfigBlobRepository()
    await repo.upsert(
        "ws-1",
        PipelineConfig,
        {**_PIPELINE_DEFAULT, "reconciliation": {"saldo_diff": 0.05, "mode": "strict"}},
    )

    cmd = PipelineConfigUpdateCommand(reconciliation={"saldo_diff": 0.10})
    resp = await update_pipeline_config(cmd, workspace_id="ws-1", repo=repo, defaults=_defaults())

    # Deep merge: saldo_diff atualiza, mode preserva
    persisted = await repo.get_config_json("ws-1", PipelineConfig)
    assert persisted is not None
    assert persisted["reconciliation"]["saldo_diff"] == 0.10
    assert persisted["reconciliation"]["mode"] == "strict"
    assert resp.file_limits.preview_max_chars == 2000


# ───── InstitutionConfig ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_institution_falls_back_to_default_when_missing():
    repo = FakeConfigBlobRepository()

    resp = await get_institution_config("ws-1", repo=repo, defaults=_defaults())

    assert resp.config_json == _INSTITUTION_DEFAULT


@pytest.mark.asyncio
async def test_update_institution_replaces_total():
    repo = FakeConfigBlobRepository()
    await repo.upsert("ws-1", InstitutionConfig, {"banks": {"old": {}}})

    cmd = InstitutionConfigUpdateCommand(
        config_json={"banks": {"itau": {"code": "itau"}, "c6": {"code": "c6"}}}
    )
    resp = await update_institution_config(cmd, workspace_id="ws-1", repo=repo)

    assert "c6" in resp.config_json["banks"]
    assert "old" not in resp.config_json["banks"]


# ───── ReportLayout ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_report_layout_falls_back_to_yaml_default():
    repo = FakeConfigBlobRepository()

    resp = await get_report_layout("ws-1", repo=repo, defaults=_defaults())

    assert resp.config_json == _LAYOUT_DEFAULT


@pytest.mark.asyncio
async def test_update_report_layout_replaces_total():
    repo = FakeConfigBlobRepository()
    cmd = ReportLayoutUpdateCommand(
        config_json={"sections": ["summary", "expenses", "investments"]}
    )

    resp = await update_report_layout(cmd, workspace_id="ws-1", repo=repo)

    assert resp.config_json["sections"] == ["summary", "expenses", "investments"]

    persisted = await repo.get_config_json("ws-1", ReportLayout)
    assert persisted is not None
    assert persisted["sections"] == ["summary", "expenses", "investments"]


# ───── Isolamento por workspace ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_in_one_workspace_does_not_leak_to_another():
    repo = FakeConfigBlobRepository()

    await update_institution_config(
        InstitutionConfigUpdateCommand(config_json={"banks": {"itau": {}}}),
        workspace_id="ws-A",
        repo=repo,
    )

    resp_b = await get_institution_config("ws-B", repo=repo, defaults=_defaults())
    assert resp_b.config_json == _INSTITUTION_DEFAULT
