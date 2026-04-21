"""FastAPI entrypoint for pipeline-service.

Run: `uvicorn app.main:app` from inside `pipeline-service/`.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI

from app.api import events as events_api
from app.api import runs as runs_api
from app.api import stages as stages_api
from app.config import load_settings
from app.contracts.runs import ServiceHealthResponse

VERSION = "0.1.0"


def _ensure_pipeline_on_path() -> None:
    """Add the repo root to sys.path so `pipeline.*` imports resolve.

    In Docker this is also arranged via WORKDIR + PYTHONPATH; keeping the
    insert here makes local dev and pytest runs work with no extra setup.
    """
    here = Path(__file__).resolve()
    repo_root = here.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def create_app() -> FastAPI:
    _ensure_pipeline_on_path()
    _configure_logging()

    app = FastAPI(
        title="Mathoms Pipeline Service",
        version=VERSION,
        description="HTTP boundary for pipeline execution (A6f.1 · ADR-112).",
    )

    app.include_router(stages_api.router)
    app.include_router(runs_api.router)
    app.include_router(events_api.router)

    @app.get("/health", response_model=ServiceHealthResponse)
    def health() -> ServiceHealthResponse:
        return ServiceHealthResponse(version=VERSION)

    return app


def _configure_logging() -> None:
    """Wire JSON logs if backend logging module is importable; else basic."""
    try:
        from backend.app.core.logging import setup_logging
    except Exception:
        _configure_basic_logging()
        return
    os.environ.setdefault("MATHOMS_LOG_FORMAT", load_settings().log_format)
    os.environ.setdefault("MATHOMS_LOG_LEVEL", load_settings().log_level)
    setup_logging()


def _configure_basic_logging() -> None:
    logging.basicConfig(
        level=load_settings().log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


app = create_app()
