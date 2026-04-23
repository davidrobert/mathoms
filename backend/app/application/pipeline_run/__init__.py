"""Use cases do agregado ``PipelineRun`` (A6e.4 · ADR-101 R15).

Trigger + listagem + cancel + resume + stage reviews. Execução real
continua delegada a ``services/pipeline_service.py`` (kickoff async via
Celery). Aqui só orquestra DB + validação.
"""

from backend.app.application.pipeline_run.action_review import action_review
from backend.app.application.pipeline_run.cancel_run import cancel_run
from backend.app.application.pipeline_run.get_run import get_run
from backend.app.application.pipeline_run.list_reviews import list_reviews
from backend.app.application.pipeline_run.list_runs import list_runs
from backend.app.application.pipeline_run.new_doc_count import new_doc_count
from backend.app.application.pipeline_run.resume_run import resume_run
from backend.app.application.pipeline_run.trigger_pipeline import trigger_pipeline

__all__ = [
    "action_review",
    "cancel_run",
    "get_run",
    "list_reviews",
    "list_runs",
    "new_doc_count",
    "resume_run",
    "trigger_pipeline",
]
