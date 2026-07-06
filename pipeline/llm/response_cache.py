"""Cache de resposta LLM opt-in no choke-point (ADR-307).

``pipeline/**`` não importa redis (``check_pipeline_boundaries``); o backend
injeta a implementação concreta (``RedisLLMCache``) via
``WorkspaceContext.llm_response_cache`` — mesmo padrão de ``LLMCallHooks``.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Optional, Protocol

#: 7 dias — bound de retenção LGPD; a invalidação real é por content-hash.
LLM_RESPONSE_CACHE_TTL_S = 7 * 24 * 60 * 60

_CACHE_NAMESPACE = "mathoms:llm:resp"

# Telemetria de hit/miss (ADR-307 D5): labels stage/prompt_version, NUNCA o
# payload — valor cacheado carrega conteúdo financeiro (LGPD).
_cache_metrics_logger = logging.getLogger("mathoms.llm.response_cache")

# Separador de campos no material hasheado — evita ambiguidade de concatenação
# ("ab"+"c" vs "a"+"bc").
_FIELD_SEP = "\x1f"


class LLMResponseCache(Protocol):
    """Contrato injetado no ``LLMService`` — implementado pelo backend (Redis)."""

    def get(self, key: str) -> Optional[str]:
        """Retorna JSON cacheado ou ``None`` em miss."""
        ...

    def set(self, key: str, value: str, ttl_s: int = LLM_RESPONSE_CACHE_TTL_S) -> None:
        """Persiste JSON com TTL em segundos."""
        ...


def build_response_cache_key(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema_name: str,
    temperature: float,
    max_tokens: int,
    seed: int | None,
    image_bytes: bytes | None,
    stage: str | None,
    prompt_version: str | None,
) -> str:
    """Key canônica — construída SOMENTE aqui (ADR-307 D2).

    ``stage``/``prompt_version`` ficam fora do material hasheado (prefixo
    legível para scan/flush); o hash cobre tudo que muda o output do modelo.
    ``user_prompt`` deve ser o texto pós-``sanitize_and_wrap`` (o que
    realmente vai ao modelo — invariante de determinismo, ADR-175).
    """
    image_sha = hashlib.sha256(image_bytes).hexdigest() if image_bytes else ""
    material = _FIELD_SEP.join(
        [
            model,
            system_prompt,
            user_prompt,
            schema_name,
            f"{temperature:.4f}",
            str(max_tokens),
            str(seed),
            image_sha,
        ]
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return f"{_CACHE_NAMESPACE}:{stage or 'unknown'}:{prompt_version or 'unversioned'}:{digest}"


def fetch_cached_output(cache: LLMResponseCache, key: str, output_schema, *, stage: str | None):
    """Retorna instância validada do schema ou ``None``; payload inválido é miss."""
    cached_json = cache.get(key)
    if cached_json is None:
        return None
    try:
        return output_schema.model_validate_json(cached_json)
    except Exception as parse_exc:  # noqa: BLE001 — payload stale/corrompido vira miss
        _cache_metrics_logger.warning(
            "llm cache payload invalid — treating as miss",
            extra={"stage": stage or "unknown", "error": str(parse_exc)[:200]},
        )
        return None


def record_cache_event(*, hit: bool, stage: str | None, prompt_version: str | None) -> None:
    """Contador estruturado de hit/miss — ``LLMCallLog`` continua verdade de custo."""
    event = "cache_hit" if hit else "cache_miss"
    _cache_metrics_logger.info(
        "llm response cache event",
        extra={
            "event": event,
            "stage": stage or "unknown",
            "prompt_version": prompt_version or "unversioned",
        },
    )
