"""Rate limit por janela fixa — Redis ``INCR``+``EXPIRE`` (W4-T04 · SR-018).

Stateless rigoroso (ADR-111): nenhum token bucket em memória — o contador
vive no Redis. **Falha aberta**: sem Redis (dev local, outage) a request
passa e logamos ``fallback`` — rate limit é proteção de abuso, não controle
de acesso; negar tráfego legítimo por outage de cache seria pior que a
janela de exposição (mesma calibração do ``category_cache``).

Uso (dependency FastAPI):
    dependencies=[rate_limited("login", key=client_ip_key)]
Limites configuráveis por env: ``MATHOMS_RATE_LIMIT_<SCOPE>`` = "N/window_s".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status

from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = logging.getLogger(__name__)
_rl_metrics = get_logger("rate_limit")


@dataclass(frozen=True)
class RateLimitPolicy:
    """Limite fixo por janela — ``limit`` requests a cada ``window_s`` segundos."""

    scope: str
    limit: int
    window_s: int


# Defaults de produção (override por env MATHOMS_RATE_LIMIT_<SCOPE>="N/seg").
# login: per-IP — complementa o lockout per-conta (brute_force_lockout).
# upload/pipeline: per-workspace — endpoints que disparam custo LLM/CPU.
# cpf_view_full: per-workspace — freia scraping do "ver completo" (ADR-259 §4).
_DEFAULT_POLICIES: dict[str, RateLimitPolicy] = {
    "login": RateLimitPolicy("login", limit=10, window_s=60),
    "upload": RateLimitPolicy("upload", limit=30, window_s=300),
    "pipeline_run": RateLimitPolicy("pipeline_run", limit=5, window_s=600),
    "cpf_view_full": RateLimitPolicy("cpf_view_full", limit=10, window_s=60),
}


def resolve_policy(scope: str) -> RateLimitPolicy:
    """Policy do scope, com override por env ``MATHOMS_RATE_LIMIT_<SCOPE>``."""
    raw = getattr(settings, f"RATE_LIMIT_{scope.upper()}", "") or ""
    if raw:
        try:
            limit_str, window_str = raw.split("/", 1)
            return RateLimitPolicy(scope, limit=int(limit_str), window_s=int(window_str))
        except ValueError:
            logger.warning("rate limit override inválido para %s: %r", scope, raw)
    return _DEFAULT_POLICIES[scope]


def _denied(policy: RateLimitPolicy, client, redis_key: str) -> tuple[bool, int]:
    ttl = client.ttl(redis_key)
    retry_after = int(ttl) if ttl and ttl > 0 else policy.window_s
    _rl_metrics.warning(
        "rate limit exceeded",
        extra={"scope": policy.scope, "result": "denied", "retry_after": retry_after},
    )
    return False, retry_after


def check_rate_limit(policy: RateLimitPolicy, key: str) -> tuple[bool, int]:
    """(allowed, retry_after_s). Falha aberta quando Redis indisponível."""
    client = _get_redis_safe()
    if client is None:
        _rl_metrics.info("rate limit fallback", extra={"scope": policy.scope, "result": "fallback"})
        return True, 0
    redis_key = f"ratelimit:{policy.scope}:{key}"
    try:
        count = client.incr(redis_key)
        if count == 1:
            client.expire(redis_key, policy.window_s)
        if count <= policy.limit:
            return True, 0
        return _denied(policy, client, redis_key)
    except Exception as exc:
        logger.warning("rate limit redis error (%s): %s — fail-open", policy.scope, exc)
        return True, 0


def client_ip_key(request: Request) -> str:
    """IP do cliente respeitando X-Forwarded-For (proxy Coolify/Traefik)."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def workspace_key(request: Request) -> str:
    """``workspace_id`` do path (endpoints tenant-scoped); IP como fallback."""
    ws_id = request.path_params.get("workspace_id")
    return str(ws_id) if ws_id else client_ip_key(request)


def rate_limited(scope: str, key: Callable[[Request], str] = client_ip_key) -> Any:
    """Dependency FastAPI — 429 + ``Retry-After`` quando o limite estoura."""

    async def _dependency(request: Request) -> None:
        policy = resolve_policy(scope)
        allowed, retry_after = check_rate_limit(policy, key(request))
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Limite de requisições atingido — tente novamente em {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )

    return Depends(_dependency)


def _get_redis_safe() -> Any:
    try:
        from backend.app.services.pipeline.events import _get_redis

        return _get_redis()
    except Exception:
        return None
