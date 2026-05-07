---
id: CHG-2026-04-15-F65-PIPELINE-MOCK-FIXTUR
type: changelog-entry
date: "2026-04-15"
sprint: F65
summary: "Pipeline mock fixtures. - **Pipeline mock fixtures** (`backend/tests/fixtures/pipeline_runs.py::seed_completed_run`): `PipelineRun(status=\"completed\")` + 13 StageLogs + Report com HTML"
tags:
  - type/changelog-entry
  - sprint/f65
---


# Pipeline mock fixtures

- **Pipeline mock fixtures** (`backend/tests/fixtures/pipeline_runs.py::seed_completed_run`): `PipelineRun(status="completed")` + 13 StageLogs + Report com HTML stub — permite Golden Path rodar em <30s; `PW_REAL_PIPELINE=1` para opt-in real
