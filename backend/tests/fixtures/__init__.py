"""Fixtures reutilizáveis para tests backend.

Atualmente:
- `pipeline_runs.seed_completed_run`: cria PipelineRun + Report completos
  para pular execução real em E2E (F6.5F.4).
"""

from backend.tests.fixtures.pipeline_runs import seed_completed_run

__all__ = ["seed_completed_run"]
