"""Pydantic schema for the /health endpoint.

Contract explícito e language-neutral (A6f.2 · ADR-102 R18): qualquer cliente
(Go, TS, curl) sabe os campos do health sem inspecionar o código Python.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Health check payload do backend.

    Campos derivados (``redis``, ``celery``, ``database``) contêm ``"ok"`` se
    saudável, ``"no_workers"`` para Celery sem workers ativos, ou
    ``"error: <mensagem>"`` em caso de falha. O status agregado em ``status``
    é ``"ok"`` sse todos os checks não-informativos estão ``"ok"``.
    """

    # ``extra="allow"`` preserva compat caso o endpoint adicione novos
    # checks no futuro sem exigir bump de versão da API.
    model_config = ConfigDict(extra="allow")

    api: Literal["ok"]
    version: str
    # ADR-362/363 — revisão do processo que responde. NULL ≡ desconhecido (subiu
    # sem MATHOMS_BUILD_SHA). Campo NOVO em vez de sobrecarregar `version`: este é
    # `str` required non-nullable e o healthcheck é `curl -fsS`, então um valor
    # nullable ali daria 500 e marcaria o container unhealthy.
    executor_revision: Optional[str] = None
    redis: str
    celery: str
    database: str
    artifact_store_mode: Literal["db", "disk"]
    # A6f.1 (ADR-112): pipeline-service HTTP boundary. Ambos campos são
    # ``None`` quando ``MATHOMS_PIPELINE_SERVICE_URL`` não está setada
    # (fallback para InProcessPipelineClient).
    pipeline_service_url: Optional[str] = None
    pipeline_service_reachable: Optional[bool] = None
    status: Literal["ok", "degraded"]
