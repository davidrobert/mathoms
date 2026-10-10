"""Snapshot imutável de rotas + detector de poluição (A26 CI flake). ``app`` é
singleton de processo; sob xdist um teste pode mutar ``app.routes`` e poluir
testes posteriores no mesmo worker (flake só-CI: 0 rotas de workspace →
``test_tenancy_isolation``/``test_access_audit`` falham, irreprodutível local).
``conftest.pytest_sessionstart`` congela as rotas ANTES de qualquer teste e os
testes-invariante leem este snapshot, não o app vivo; o teardown hook nomeia o
teste que derruba rotas de workspace — caça o poluidor sem repro local.

Rota aqui é sempre a **efetiva** (prefixo + dependências do ``include_router``):
o fastapi 0.137 trocou ``app.routes`` por uma árvore de ``_IncludedRouter`` e
iterar a lista plana passou a ver 1 de 415 rotas — gate verde sobre o vazio.
A guarda contra isso é a igualdade com as operações do snapshot OpenAPI
commitado (``openapi_snapshot_operations``), fonte que não percorre a árvore.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from fastapi.routing import iter_route_contexts

_OPENAPI_SNAPSHOT = Path(__file__).resolve().parents[2] / "docs/reference/api/v1/openapi.json"
_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})

# Preenchido por conftest.pytest_sessionstart (1× por worker, pré-coleta de testes).
ROUTES_SNAPSHOT: list[Any] = []


def iter_effective_routes(routes: Iterable[Any]) -> list[Any]:
    """Rotas efetivas do app (``RouteContext``: prefixo + dependências do include)."""
    return list(iter_route_contexts(routes))


def schema_operations(routes: Iterable[Any]) -> set[tuple[str, str]]:
    """``(método, path)`` das rotas que entram no OpenAPI, sem HEAD/OPTIONS."""
    return {
        (method, route.path)
        for route in routes
        if getattr(route, "include_in_schema", False)
        for method in (getattr(route, "methods", None) or ())
        if method in _HTTP_METHODS
    }


def openapi_snapshot_operations() -> set[tuple[str, str]]:
    """``(método, path)`` do ``openapi.json`` commitado — o universo esperado."""
    paths = json.loads(_OPENAPI_SNAPSHOT.read_text(encoding="utf-8"))["paths"]
    return {(m.upper(), p) for p, item in paths.items() for m in item if m.upper() in _HTTP_METHODS}


def workspace_operations(routes: Iterable[Any]) -> set[tuple[str, str]]:
    """``(método, path)`` das rotas de workspace — o que o detector de poluição vigia."""
    return {
        (method, route.path)
        for route in routes
        if "{workspace_id}" in (getattr(route, "path", None) or "")
        for method in (getattr(route, "methods", None) or ())
    }


def effective_routes() -> list[Any]:
    """Snapshot pré-poluição; fallback para o app vivo se o snapshot não rodou."""
    if ROUTES_SNAPSHOT:
        return ROUTES_SNAPSHOT
    from backend.app.main import app

    return iter_effective_routes(app.routes)
