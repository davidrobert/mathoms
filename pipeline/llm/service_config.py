"""Value objects do ``LLMService`` — moraram em ``litellm_client.py`` até
ADR-307 estourar o teto de 500 linhas (P2, mesmo movimento do ``LLMRunSummary``
em A20.l11); call-sites continuam importando de lá (re-export)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pipeline.llm.call_hooks import LLMCallHooks
from pipeline.llm.metrics import LLMMetricsEmitter
from pipeline.llm.models_catalog import default_model_for
from pipeline.llm.response_cache import LLMResponseCache


@dataclass
class LLMCallResult:
    """Result of a single LLM call with usage metrics."""

    output: Any
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    total_tokens: int = 0
    # Telemetria, não contábil — o registro fiscal é llm_call_log.cost_usd (Numeric).
    cost_estimate_usd: float = 0.0  # estimativa via rate table de pricing (ADR-173)
    duration_ms: int = 0
    retries_used: int = 0
    # False quando o modelo não está em ``_MODEL_PRICING``: ``cost_estimate_usd``
    # é 0.0 por convenção mas representa "desconhecido", não "grátis". Distingue
    # provedor sem custo (Ollama local) de pricing missing (modelo novo não-mapeado).
    cost_known: bool = True


@dataclass
class LLMConfig:
    """Configuration for LLM calls (from DB or dict)."""

    provider: str = "anthropic"
    api_key: str = ""
    model_name: str = default_model_for("anthropic")
    max_tokens: int = 4096
    temperature: float = 0.1
    # ADR-173 — injetado pelo call-site com WorkspaceContext (nunca vem do
    # JSON de config); ``dataclasses.replace`` de variantes de modelo preserva.
    call_hooks: LLMCallHooks | None = field(default=None, repr=False, compare=False)
    # ADR-307 — cache de resposta opt-in; injetado como os hooks, nunca do JSON.
    response_cache: LLMResponseCache | None = field(default=None, repr=False, compare=False)
    # A33.l7 (ADR-110) — métricas OTLP ``mathoms.llm.*``; ``None`` = no-op
    # (opt-in preservado: sem endpoint OTLP o backend nem injeta).
    metrics_emitter: LLMMetricsEmitter | None = field(default=None, repr=False, compare=False)
