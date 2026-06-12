"""Parecer planejador — orchestrator slim (ADR-199/200/201/203/207)."""
# Wire-up: persona + manifest + cache + LLMService + tools de drill-down +
# validador anti-token + finalize. Split em parecer_manifest.py / _distiller.py /
# _finalization.py para respeitar P1/P2 (CLAUDE.md §Code style — 4-20 linhas / ≤500 linhas).

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, replace
from typing import Any, Mapping, Optional

from backend.app.services.parecer_distiller import distill_exec_context
from backend.app.services.parecer_evidencia import (
    EVIDENCIA_VERIFICATION_VERSION,
    EvidenciaVerification,
    resolve_evidencia_mode,
    verify_evidencia,
)
from backend.app.services.parecer_finalization import (
    compute_suggestion_dedup_key,
    empty_needs_review_output,
    finalize_output,
    severity_from_prioridade,
    validate_anti_sigilo,
)
from backend.app.services.parecer_manifest import ManifestData, load_manifest, load_persona
from pipeline.llm.models_catalog import PARECER_MODEL
from pipeline.llm.prompts.parecer_planejador import (
    PROMPT_VERSION,
    SYSTEM_PROMPT_TEMPLATE,
    USER_PROMPT_TEMPLATE,
)
from pipeline.llm.schemas.parecer_planejador import ParecerPlanejadorOutput
from pipeline.llm.tools.planner_drill_down import PlannerDrillDown

logger = logging.getLogger("mathoms.llm.parecer_planejador")
_SCHEMA_VERSION = "1.0"  # bump em mudança breaking do output schema (ADR-202)


@dataclass
class ParecerGenerationResult:
    """Resultado da geração — consumido pelo stage wrapper."""

    output: ParecerPlanejadorOutput
    persona_hash: str
    manifest_version: str
    schema_version: str
    model_id: str
    tier_at_generation: str
    tokens_in: int = 0
    tokens_out: int = 0
    # WHY float (ADR-090): valor em USD vindo do LLM provider (Anthropic API);
    # persistência converte para cents (BigInteger) em PlannerReview.cost_usd_cents.
    cost_usd: float = 0.0  # rate USD from LLM provider — converted to cents on persist (ADR-090)
    latency_ms: int = 0
    tool_iterations: int = 0
    tool_trace: list[dict] = None  # type: ignore[assignment]
    cache_hit: bool = False
    status: str = "Gerado"
    error_detail: Optional[str] = None
    evidencia_summary: Optional[dict] = None
    evidencia_entries: Optional[list[dict]] = None

    def __post_init__(self) -> None:
        if self.tool_trace is None:
            self.tool_trace = []


@dataclass
class ParecerOrchestratorConfig:
    """Configuração da geração (injetada pelo stage wrapper)."""

    workspace_id: str
    tier: str = "premium"
    cache_ttl_s: int = 7 * 24 * 3600
    model_id: str = PARECER_MODEL
    api_key: Optional[str] = None
    schema_version: str = _SCHEMA_VERSION
    max_tokens: int = 16_384
    temperature: float = 0.1


# ----------------------------------------------------------------------
# Cache key + cache backend wiring
# ----------------------------------------------------------------------


def compute_cache_key(
    *,
    e5_data: Mapping[str, Any],
    manifest_version: str,
    schema_version: str,
    model_id: str,
    workspace_id: str,
) -> str:
    """Chave Redis canônica do parecer (ADR-199 §pattern ADR-144)."""
    e5_raw = json.dumps(e5_data, sort_keys=True, ensure_ascii=False, default=str)
    e5_hash = hashlib.sha256(e5_raw.encode("utf-8")).hexdigest()[:16]
    # ev{N} invalida caches pré-F4 (sem citação verificada — ADR-279 §E).
    composite = (
        f"{workspace_id}:{e5_hash}:{manifest_version}:{schema_version}:{model_id}"
        f":ev{EVIDENCIA_VERIFICATION_VERSION}"
    )
    digest = hashlib.sha256(composite.encode("utf-8")).hexdigest()
    return f"mathoms:llm:parecer_planejador:{digest}"


def _build_cache():
    from backend.app.services.llm_cache import get_default_llm_cache

    return get_default_llm_cache()


def _try_cache(cache: Any, key: str) -> Optional[ParecerPlanejadorOutput]:
    """Lê cache; retorna output deserializado ou ``None``."""
    raw = cache.get(key)
    return ParecerPlanejadorOutput.model_validate_json(raw) if raw else None


def _write_cache(cache: Any, key: str, output: ParecerPlanejadorOutput, ttl_s: int) -> None:
    """Best-effort cache write (ADR-144 — fail open)."""
    try:
        cache.set(key, output.model_dump_json(), ttl_s=ttl_s)
    except Exception as exc:  # noqa: BLE001 — cache write é best-effort
        logger.warning("parecer_planejador_cache_write_failed: %s", exc)


# ----------------------------------------------------------------------
# LLM wiring
# ----------------------------------------------------------------------


def _build_llm_service(config: ParecerOrchestratorConfig):
    """Wire LiteLLM/Instructor — ``None`` se key indisponível."""
    api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    from pipeline.llm.litellm_client import LLMConfig, LLMService

    provider, model_name = "anthropic", config.model_id
    if "/" in config.model_id:
        provider, model_name = config.model_id.split("/", 1)
    return LLMService(
        LLMConfig(
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )
    )


def _extract_last_call_metrics(llm: Any) -> tuple[int, int, float]:
    """Extrai métricas do último call do LLMService — defensivo p/ fakes."""
    summary = getattr(llm, "summary", None)
    if summary is None or not getattr(summary, "calls", None):
        return 0, 0, 0.0
    last = summary.calls[-1]
    return (
        getattr(last, "tokens_in", 0) or 0,
        getattr(last, "tokens_out", 0) or 0,
        float(getattr(last, "cost_estimate_usd", 0.0) or 0.0),
    )


def _invoke_llm(
    *, llm: Any, system_prompt: str, user_prompt: str, max_tokens: int
) -> ParecerPlanejadorOutput:
    """Chama LLM com Instructor — output já validado pelo schema Pydantic."""
    return llm.call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        output_schema=ParecerPlanejadorOutput,
        stage="review_finances_holistic",
        max_tokens=max_tokens,
    ).output


# ----------------------------------------------------------------------
# Result builders
# ----------------------------------------------------------------------


def _base_result(
    *,
    output: ParecerPlanejadorOutput,
    persona_hash: str,
    manifest: ManifestData,
    config: ParecerOrchestratorConfig,
) -> ParecerGenerationResult:
    """Skeleton com campos imutáveis; caller adiciona métricas via ``dataclasses.replace``."""
    return ParecerGenerationResult(
        output=output,
        persona_hash=persona_hash,
        manifest_version=manifest.version,
        schema_version=config.schema_version,
        model_id=config.model_id,
        tier_at_generation=config.tier,
    )


def _needs_review(
    *,
    reason: str,
    persona_hash: str,
    manifest: ManifestData,
    config: ParecerOrchestratorConfig,
    elapsed_ms: int,
) -> ParecerGenerationResult:
    """Resultado em ``status='needs_review'`` (não publica artifact)."""
    placeholder = empty_needs_review_output(
        persona_hash=persona_hash,
        manifest_version=manifest.version,
        model_id=config.model_id,
        tier=config.tier,
    )
    base = _base_result(
        output=placeholder, persona_hash=persona_hash, manifest=manifest, config=config
    )
    return replace(base, status="needs_review", error_detail=reason, latency_ms=elapsed_ms)


def _hit_result(
    *,
    cached: ParecerPlanejadorOutput,
    persona_hash: str,
    manifest: ManifestData,
    config: ParecerOrchestratorConfig,
    elapsed_ms: int,
) -> ParecerGenerationResult:
    """Resultado de cache hit — sem custo, sem tokens."""
    base = _base_result(output=cached, persona_hash=persona_hash, manifest=manifest, config=config)
    return replace(base, cache_hit=True, latency_ms=elapsed_ms)


def _success_result(
    *,
    output: ParecerPlanejadorOutput,
    persona_hash: str,
    manifest: ManifestData,
    config: ParecerOrchestratorConfig,
    tools: PlannerDrillDown,
    llm: Any,
    elapsed_ms: int,
) -> ParecerGenerationResult:
    """Empacota sucesso com métricas extraídas do LLM."""
    tokens_in, tokens_out, cost_usd = _extract_last_call_metrics(llm)
    base = _base_result(output=output, persona_hash=persona_hash, manifest=manifest, config=config)
    return replace(
        base,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        latency_ms=elapsed_ms,
        tool_iterations=tools.iterations_count,
        tool_trace=tools.to_trace_dicts(),
    )


# ----------------------------------------------------------------------
# Main entrypoint
# ----------------------------------------------------------------------


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def _resolve_runtime(
    config: ParecerOrchestratorConfig, llm_service: Any, cache: Any
) -> tuple[ManifestData, str, str, Any, Any]:
    """Carrega manifest + persona + resolve LLM service e cache backend."""
    manifest = load_manifest()
    persona_body, persona_hash = load_persona()
    resolved_cache = cache if cache is not None else _build_cache()
    resolved_llm = llm_service or _build_llm_service(config)
    return manifest, persona_body, persona_hash, resolved_llm, resolved_cache


def generate_parecer(
    *,
    e5_data: Mapping[str, Any],
    config: ParecerOrchestratorConfig,
    llm_service: Any = None,
    cache: Any = None,
) -> ParecerGenerationResult:
    """Gera parecer end-to-end — orquestra cache, LLM, tools, validador, finalize."""
    start = time.monotonic()
    manifest, persona_body, persona_hash, llm, cache = _resolve_runtime(config, llm_service, cache)
    key = compute_cache_key(
        e5_data=e5_data,
        manifest_version=manifest.version,
        schema_version=config.schema_version,
        model_id=config.model_id,
        workspace_id=config.workspace_id,
    )
    cached = _try_cache(cache, key)
    if cached is not None:
        logger.info("parecer_planejador_cache_hit", extra={"workspace_id": config.workspace_id})
        return _hit_result(
            cached=cached,
            persona_hash=persona_hash,
            manifest=manifest,
            config=config,
            elapsed_ms=_elapsed_ms(start),
        )
    if llm is None:
        return _needs_review(
            reason="LLM service unavailable (ANTHROPIC_API_KEY missing)",
            persona_hash=persona_hash,
            manifest=manifest,
            config=config,
            elapsed_ms=_elapsed_ms(start),
        )
    return _generate_with_llm(
        llm=llm,
        cache=cache,
        cache_key=key,
        manifest=manifest,
        persona_body=persona_body,
        persona_hash=persona_hash,
        e5_data=e5_data,
        config=config,
        start=start,
    )


def _call_llm_safe(
    *,
    llm: Any,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    workspace_id: str,
) -> tuple[Optional[ParecerPlanejadorOutput], Optional[str]]:
    """Invoca LLM; retorna ``(output, None)`` ou ``(None, error_msg)``."""
    try:
        return _invoke_llm(
            llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=max_tokens
        ), None
    except Exception as exc:  # noqa: BLE001 — todas exceções viram needs_review
        logger.warning(
            "parecer_planejador_llm_call_failed",
            extra={"workspace_id": workspace_id, "error": str(exc)[:200]},
        )
        return None, f"LLM call failed: {exc}"


def _build_prompts(
    *, manifest: ManifestData, persona_body: str, e5_data: Mapping[str, Any]
) -> tuple[str, str]:
    """Constrói (system_prompt, user_prompt) via persona + manifest distillado."""
    exec_context = distill_exec_context(manifest, e5_data)
    return (
        SYSTEM_PROMPT_TEMPLATE.format(persona_body=persona_body),
        USER_PROMPT_TEMPLATE.format(exec_context=exec_context),
    )


def _check_sigilo(raw: ParecerPlanejadorOutput, config: ParecerOrchestratorConfig) -> Optional[str]:
    """Retorna mensagem de erro se sigilo §13 violado; senão None."""
    violations = validate_anti_sigilo(raw)
    if not violations:
        return None
    logger.warning(
        "parecer_planejador_sigilo_violations",
        extra={"workspace_id": config.workspace_id, "violations_count": len(violations)},
    )
    return f"sigilo §13 violations: {violations[:3]}"


def _check_evidencia(
    raw: ParecerPlanejadorOutput,
    manifest: ManifestData,
    e5_data: Mapping[str, Any],
    config: ParecerOrchestratorConfig,
) -> tuple[EvidenciaVerification, Optional[str]]:
    """Citação verificada E5→E6 (ADR-279 §E) — strict + violação → motivo de needs_review."""
    drill = PlannerDrillDown(
        e5_data=e5_data, section_whitelist=manifest.tools_section_whitelist, format_hints={}
    )
    verification = verify_evidencia(output=raw, drill=drill)
    if not verification.violations:
        return verification, None
    mode = resolve_evidencia_mode(manifest.evidencia_verification_mode)
    logger.warning(
        "parecer_planejador_evidencia_violations",
        extra={"workspace_id": config.workspace_id, "mode": mode},
    )
    if mode != "strict":
        return verification, None
    return verification, f"evidencia unverified: {verification.violations[0]}"


def _generate_with_llm(
    *,
    llm: Any,
    cache: Any,
    cache_key: str,
    manifest: ManifestData,
    persona_body: str,
    persona_hash: str,
    e5_data: Mapping[str, Any],
    config: ParecerOrchestratorConfig,
    start: float,
) -> ParecerGenerationResult:
    """Sub-path quando LLM está disponível — chama, valida sigilo, finaliza, cacheia."""
    system_prompt, user_prompt = _build_prompts(
        manifest=manifest, persona_body=persona_body, e5_data=e5_data
    )
    tools = PlannerDrillDown(
        e5_data=e5_data,
        section_whitelist=manifest.tools_section_whitelist,
        format_hints=manifest.format_hints,
    )
    raw, err = _call_llm_safe(
        llm=llm,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=config.max_tokens,
        workspace_id=config.workspace_id,
    )
    if raw is None:
        return _needs_review(
            reason=err or "LLM call failed",
            persona_hash=persona_hash,
            manifest=manifest,
            config=config,
            elapsed_ms=_elapsed_ms(start),
        )
    sigilo_err = _check_sigilo(raw, config)
    if sigilo_err:
        return _needs_review(
            reason=sigilo_err,
            persona_hash=persona_hash,
            manifest=manifest,
            config=config,
            elapsed_ms=_elapsed_ms(start),
        )
    evidencia, evidencia_err = _check_evidencia(raw, manifest, e5_data, config)
    if evidencia_err:
        base = _needs_review(
            reason=evidencia_err,
            persona_hash=persona_hash,
            manifest=manifest,
            config=config,
            elapsed_ms=_elapsed_ms(start),
        )
        return replace(
            base,
            evidencia_summary=evidencia.summary(needs_review_triggered=True),
            evidencia_entries=evidencia.entries,
        )
    final = finalize_output(
        output=raw,
        workspace_id=config.workspace_id,
        tier=config.tier,
        model_id=config.model_id,
        persona_hash=persona_hash,
        manifest_version=manifest.version,
    )
    _write_cache(cache, cache_key, final, ttl_s=config.cache_ttl_s)
    success = _success_result(
        output=final,
        persona_hash=persona_hash,
        manifest=manifest,
        config=config,
        tools=tools,
        llm=llm,
        elapsed_ms=_elapsed_ms(start),
    )
    return replace(
        success,
        evidencia_summary=evidencia.summary(needs_review_triggered=False),
        evidencia_entries=evidencia.entries,
    )


__all__ = [
    "PROMPT_VERSION",
    "ParecerGenerationResult",
    "ParecerOrchestratorConfig",
    "compute_cache_key",
    "compute_suggestion_dedup_key",
    "distill_exec_context",
    "generate_parecer",
    "load_manifest",
    "load_persona",
    "severity_from_prioridade",
    "validate_anti_sigilo",
]
