"""Pydantic schema for the /health endpoint.

Contract explícito e language-neutral (A6f.2 · ADR-102 R18): qualquer cliente
(Go, TS, curl) sabe os campos do health sem inspecionar o código Python.
"""

from __future__ import annotations

from typing import Literal

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
    redis: str
    celery: str
    database: str
    artifact_store_mode: Literal["db", "disk"]
    status: Literal["ok", "degraded"]
