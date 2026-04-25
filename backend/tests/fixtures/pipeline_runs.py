"""Pipeline run fixtures pré-computadas — F6.5F.4.

# Por que

Pipeline real demora 5-15min. Playwright timeout default é 30s. Para que
`golden-path.spec.ts` (6.5C.0) e `upload-pipeline-report.spec.ts` (6.5C.3)
rodem em CI sem flakiness, usamos fixtures pré-computadas:

- `PipelineRun` com `status="completed"` já no DB
- `PipelineStageLog` por stage com timestamps plausíveis
- `Report` apontando para arquivo HTML estático em `storage/{ws_id}/output/`

# Quando usar real

- `--real-pipeline` flag (env var `PW_REAL_PIPELINE=1`) faz o test SKIPAR
  o mock e rodar orchestrator de verdade. Configurado em nightly CI.
- Por default (PR checks), usa fixtures.

# Política

- Mocks são "snapshot" realista: estrutura do JSON E5 real.
- Gerado por `regenerate_fixtures.py` quando pipeline muda output.
- Versionado em tests/fixtures/pipeline_runs/ (JSON + HTML pequenos).

# Uso em E2E

```python
# backend/tests/fixtures/pipeline_runs.py
from backend.tests.fixtures.pipeline_runs import seed_completed_run

# Dentro de um test helper chamado via API:
async def test_golden_uses_precomputed(client, db):
    ws = await make_workspace(db)
    run, report = await seed_completed_run(db, ws, period="2026-04")
    # Agora /reports lista o report sem precisar rodar pipeline de verdade
```

# Regeneração

Rodar um pipeline real contra fixtures sintéticas de 6.5F.12 e capturar
o output em `tests/fixtures/pipeline_runs/{period}/`. Script futuro:
`tests/fixtures/regenerate_pipeline_fixtures.py` (deferido).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    PipelineRun,
    PipelineStageLog,
    Report,
    Workspace,
)
from backend.app.models.pipeline_artifact import PipelineArtifact

# Stages que compõem uma run free tier (DETERMINISTIC_ORDER)
_DEFAULT_FREE_STAGES: list[tuple[str, str, int]] = [
    # (stage, status, duration_ms)
    ("E0-audit", "completed", 800),
    ("E0-route", "completed", 500),
    ("E1.5c", "skipped", 0),
    ("E2-faturas", "completed", 12_000),
    ("E2-extratos", "completed", 15_000),
    ("E3", "completed", 6_000),
    ("E4", "completed", 4_000),
    ("E5", "completed", 8_000),
    ("E5.N", "completed", 2_000),
    ("E7-crossval", "completed", 3_000),
    ("E7-apply", "skipped", 0),
]


async def seed_completed_run(
    db: AsyncSession,
    workspace: Workspace,
    *,
    period: str = "2026-04",
    tier: str = "free",
    family_surname: Optional[str] = None,
) -> tuple[PipelineRun, Report]:
    """Cria um PipelineRun completo no DB + Report associado com HTML stub.

    Usado em E2E para pular a execução real do pipeline (que leva minutos)
    e testar apenas a UI de reports.

    Returns:
        (run, report) — ambos já persistidos com flush.
    """
    now = datetime.now(timezone.utc)
    started = now.replace(microsecond=0)

    run = PipelineRun(
        workspace_id=workspace.id,
        status="completed",
        current_stage=None,
        failed_at_stage=None,
        tier_at_run=tier,
        total_documents=2,
        celery_task_id="seed-fixture",
        started_at=started,
        completed_at=started,
    )
    db.add(run)
    await db.flush()

    for stage, status, duration in _DEFAULT_FREE_STAGES:
        db.add(
            PipelineStageLog(
                pipeline_run_id=run.id,
                stage=stage,
                status=status,
                output_summary={"seeded": True, "stage": stage},
                errors=None,
                duration_ms=duration,
                started_at=started,
                completed_at=started if status == "completed" else None,
            )
        )

    # ADR-129/ADR-131: renderer HTML server-side removido e Report referencia
    # o artefato E5 em pipeline_artifacts via FK — sem filesystem.
    artifact = PipelineArtifact(
        workspace_id=workspace.id,
        pipeline_run_id=run.id,
        stage="E5",
        artifact_key="analise_financeira",
        content_json={"periodo_dados": period, "score": {"valor": 78}},
    )
    db.add(artifact)
    await db.flush()

    report = Report(
        workspace_id=workspace.id,
        pipeline_run_id=run.id,
        title=f"Relatório {family_surname or workspace.name} — {period}",
        period=period,
        analysis_artifact_id=artifact.id,
        score=78.0,
        patrimonio_liquido=250_000.0,
    )
    db.add(report)
    await db.flush()

    return run, report


__all__ = ["seed_completed_run"]
