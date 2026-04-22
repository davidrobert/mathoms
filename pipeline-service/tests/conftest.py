"""Shared fixtures for pipeline-service tests.

Pipeline-service runs from its own directory in CI; tests here need:
- repo root on sys.path so `pipeline.*` resolves;
- `pipeline-service/` on sys.path so `app.*` resolves without `pip install -e`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SERVICE_ROOT.parent
for p in (_SERVICE_ROOT, _REPO_ROOT):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

import pytest
from app.main import create_app  # noqa: E402
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client for unit-level HTTP tests."""
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _reset_event_client():
    """Reset Redis singleton between tests to avoid fixture bleed."""
    from app.services import event_publisher

    event_publisher.reset_client()
    yield
    event_publisher.reset_client()
