"""Deprecation + Sunset headers no alias legado `/api/*` (A6e.5 · ADR-108).

Canônico vive em `settings.API_PREFIX` (/api/v1). O alias legado
`settings.LEGACY_API_PREFIX` (/api) permanece funcional até F7A para não
quebrar clientes existentes — mas cada response ganha headers RFC 8594
(Sunset) + IETF draft-dalal-deprecation-header (Deprecation) + RFC 8288
(Link: rel="successor-version") apontando para o prefix novo.

Remoção do alias: F7A (nginx/traefik + cutover coordenado).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from backend.app.core.config import settings


class LegacyApiDeprecationMiddleware(BaseHTTPMiddleware):
    """Adiciona Deprecation + Sunset em respostas do prefix legado."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if _is_legacy_path(request.url.path):
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = settings.LEGACY_SUNSET_DATE
            response.headers["Link"] = (
                f'<{settings.API_PREFIX}>; rel="successor-version"'
            )
        return response


def _is_legacy_path(path: str) -> bool:
    """True se path bate no alias legado mas NÃO no canônico.

    Guard contra matching falso-positivo quando API_PREFIX é um extensão
    do LEGACY_API_PREFIX (ex.: /api vs /api/v1): /api/v1/foo começa com
    /api, mas é canônico — não deve marcar Deprecation.
    """
    legacy = settings.LEGACY_API_PREFIX
    canonical = settings.API_PREFIX
    return path.startswith(legacy) and not path.startswith(canonical)
