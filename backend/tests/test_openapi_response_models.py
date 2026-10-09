"""Structural test — todo endpoint JSON tem ``response_model`` explícito.

A6f.2 (ADR-102 · R18: wire formats explícitos): qualquer client (Go, TS,
Rust) precisa saber a shape do response sem inspecionar Python. Endpoints
que retornam JSON devem declarar ``response_model=...``; endpoints que
retornam bytes/HTML/texto/CSV/PDF declaram ``response_class=...``.

Este teste garante essa disciplina — falha se um endpoint novo é
mergeado sem ``response_model`` nem ``response_class`` explícito e sem
status ``204 No Content``.
"""

from __future__ import annotations

from typing import Any, Iterable

from backend.app.main import app
from backend.tests._app_routes import iter_effective_routes, openapi_snapshot_operations

# Rotas built-in do FastAPI (docs/redoc/openapi-spec) — não são nosso contrato.
_FASTAPI_BUILTIN_PATHS = frozenset(
    {
        "/api/v1/openapi.json",
        "/api/v1/docs",
        "/api/v1/docs/oauth2-redirect",
        "/redoc",
        "/docs/oauth2-redirect",
    }
)

# response_class aceitos como "não-JSON, declaração explícita suficiente".
_NON_JSON_RESPONSE_CLASSES = frozenset(
    {
        "HTMLResponse",
        "PlainTextResponse",
        "FileResponse",
        "StreamingResponse",
        "Response",
        "JSONResponse",
    }
)

# Status codes que não carregam body.
_NO_CONTENT_STATUS = frozenset({204, 205, 304})


def _iter_endpoints(
    routes: Iterable[Any] | None = None,
) -> Iterable[tuple[str, str, object, object, int | None]]:
    """Yield (method, path, response_model, response_class, status_code) por endpoint
    exposto pelo app, pulando built-ins FastAPI e métodos HEAD/OPTIONS."""
    for route in iter_effective_routes(app.routes) if routes is None else routes:
        if not getattr(route, "methods", None):
            continue
        path = route.path
        if path in _FASTAPI_BUILTIN_PATHS:
            continue
        for method in sorted(route.methods):
            if method in ("HEAD", "OPTIONS"):
                continue
            yield (
                method,
                path,
                getattr(route, "response_model", None),
                getattr(route, "response_class", None),
                getattr(route, "status_code", None),
            )


def test_every_json_endpoint_has_response_model_or_explicit_response_class() -> None:
    """Estrutural — gap de contrato bloqueia merge.

    Aceita três caminhos por endpoint:
    1. ``response_model=...`` declarado (caso comum).
    2. ``response_class=HTMLResponse/FileResponse/...`` declarado (file, stream, html, csv, pdf).
    3. Endpoint sem body: ``status_code in {204, 205, 304}``.
    """
    gaps: list[str] = []
    for method, path, response_model, response_class, status_code in _iter_endpoints():
        if response_model is not None:
            continue
        if status_code in _NO_CONTENT_STATUS:
            continue
        rc_name = (
            response_class.__name__
            if response_class is not None and hasattr(response_class, "__name__")
            else ""
        )
        if rc_name in _NON_JSON_RESPONSE_CLASSES:
            continue
        gaps.append(f"{method} {path} (status={status_code}, response_class={rc_name or '-'})")

    assert not gaps, (
        "A6f.2 · ADR-102 R18: endpoint sem contrato explícito. Adicione "
        "``response_model=...`` (para JSON) ou ``response_class=...`` (para "
        "file/stream/html). Gaps:\n  - " + "\n  - ".join(gaps)
    )


def _unexamined_schema_operations(routes: Iterable[Any]) -> set[tuple[str, str]]:
    """Operações do OpenAPI commitado que o gate não examinou — não-vazio = gate cego."""
    examined = {(method, path) for method, path, *_ in _iter_endpoints(routes)}
    return openapi_snapshot_operations() - examined


def test_gate_examines_every_openapi_operation() -> None:
    """Não-vácuo: o gate acima vê toda operação do snapshot, não só as do topo da árvore."""
    unexamined = _unexamined_schema_operations(iter_effective_routes(app.routes))
    assert not unexamined, (
        f"o gate da ADR-109 não examinou {len(unexamined)} operação(ões) do openapi.json "
        f"commitado (ex.: {sorted(unexamined)[:3]}) — iteração de rotas perdeu parte da árvore"
    )


def test_gate_blindness_is_detected() -> None:
    """Contrafactual da guarda: tirar uma rota, ou todas, aparece como operação não examinada."""
    routes = iter_effective_routes(app.routes)
    dropped = next(
        r
        for r in routes
        if r.path == "/api/v1/workspaces/{workspace_id}/documents" and "GET" in (r.methods or ())
    )
    remaining = [r for r in routes if r is not dropped]
    assert _unexamined_schema_operations(remaining) == {("GET", dropped.path)}
    assert _unexamined_schema_operations([]) == openapi_snapshot_operations()
