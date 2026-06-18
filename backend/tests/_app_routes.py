"""Snapshot imutável de rotas + detector de poluição (A26 CI flake). ``app`` é
singleton de processo; sob xdist um teste pode mutar ``app.routes`` e poluir
testes posteriores no mesmo worker (flake só-CI: 0 rotas de workspace →
``test_tenancy_isolation``/``test_access_audit`` falham, irreprodutível local).
``conftest.pytest_sessionstart`` congela as rotas ANTES de qualquer teste e os
testes-invariante leem este snapshot, não o app vivo; o teardown hook nomeia o
teste que derruba rotas de workspace — caça o poluidor sem repro local.
"""

from __future__ import annotations

from typing import Any

# Preenchido por conftest.pytest_sessionstart (1× por worker, pré-coleta de testes).
ROUTES_SNAPSHOT: list[Any] = []


def _ws_route_count(routes: list[Any]) -> int:
    return sum(1 for r in routes if "{workspace_id}" in getattr(r, "path", ""))


def effective_routes() -> list[Any]:
    """Snapshot pré-poluição; fallback para o app vivo se o snapshot não rodou."""
    if ROUTES_SNAPSHOT:
        return ROUTES_SNAPSHOT
    from backend.app.main import app

    return list(app.routes)
