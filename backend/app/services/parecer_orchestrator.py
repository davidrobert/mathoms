"""Parecer planejador — orchestrator slim (ADR-199/200/201/203/207)."""
# Wire-up: persona + manifest + cache + LLMService + tools de drill-down +
# validador anti-token + finalize. Split em parecer_manifest.py / _distiller.py /
# _finalization.py para respeitar P1/P2 (CLAUDE.md §Code style — 4-20 linhas / ≤500 linhas).

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Optional

from backend.app.core.llm_metrics import get_llm_metrics_emitter
from backend.app.models.planner_review import ParecerRetentionReason
from backend.app.services.parecer_context_sanitizer import sanitize_e5_for_parecer
from backend.app.services.parecer_distiller import distill_exec_context
from backend.app.services.parecer_evidencia import (
    EVIDENCIA_VERIFICATION_VERSION,
    EvidenciaVerification,
    log_evidencia_kpi,
    resolve_evidencia_mode,
    verify_evidencia,
)
from backend.app.services.parecer_finalization import (
    compute_suggestion_dedup_key,
    empty_needs_review_output,
    finalize_output,
    severity_from_prioridade,
    stamp_ancora_values,
    validate_anti_sigilo,
)
from backend.app.services.parecer_manifest import ManifestData, load_manifest, load_persona
from backend.app.services.parecer_pos_llm_guardrails import (
    downgrade_confianca_fallback,
    filter_campos_faltantes,
    guardrails_summary,
)
from backend.app.services.parecer_red_lines import RED_LINES_VERSION, check_red_lines
from backend.app.services.parecer_strict_enforcement import (
    StrictDecision,
    enforce_strict_per_item,
    no_enforcement,
)
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
# Allowlist de forma p/ o código de classificação em `_exc_label` — o valor vem de
# `LLMErrorType`, mas a asserção de forma é barata e fecha a classe de vazamento inteira.
_SAFE_ERROR_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


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
    # False ⇒ `cost_usd` 0.0 significa desconhecido, não grátis (modelo fora da rate
    # table, ou chamada que falhou pós-cobrança e não deixou entry em summary.calls).
    cost_known: bool = True
    latency_ms: int = 0
    # Telemetria de invocações do PlannerDrillDown — inclui cache hits e o
    # stamping pós-LLM de âncoras (ADR-296), então pode exceder o cap
    # max_tool_iterations. Semântica canônica: PlannerDrillDown.iterations_count
    # (OBS-1 · A37.l1).
    tool_iterations: int = 0
    tool_trace: list[dict] = None  # type: ignore[assignment]
    cache_hit: bool = False
    status: str = "Gerado"
    error_detail: Optional[str] = None
    # Classe fechada client-facing (ADR-366 §D3). `None` em `needs_review` significa
    # INDISPONIBILIDADE técnica: nada foi gerado, logo não há desfecho retido a
    # persistir — o leitor responde 404, não 200 (§D6).
    retention_reason: Optional[str] = None
    evidencia_summary: Optional[dict] = None
    evidencia_entries: Optional[list[dict]] = None
    red_lines_summary: Optional[dict] = None
    # A28.l11 — guardrails pós-LLM: entradas removidas do campos_faltantes (audit
    # p/ PlannerFieldRequest) + telemetria (rebaixamento de confiança, 3-vias).
    field_request_audit: Optional[list[dict]] = None
    pos_llm_guardrails: Optional[dict] = None

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
    # Geração mais longa do pipeline (16k max_tokens) estourou o cap global de
    # 120s pós-migração claude-sonnet-4-6 — emenda ADR-270 (2026-06-12).
    llm_timeout_s: float = 240.0
    # ADR-173: hooks de budget/telemetria — stage wrapper injeta ctx.llm_call_hooks.
    llm_hooks: Optional[Any] = None
    # CTO-03 (ADR-332): mapa (nome, papel) do family_members p/ o sanitizer de PII
    # do contexto do parecer. repr=False: nunca ecoa nome próprio em log/exceção.
    name_role_pairs: tuple[tuple[str, str], ...] = field(default=(), repr=False)


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
    prompt_version: str = PROMPT_VERSION,
) -> str:
    """Chave Redis canônica do parecer (ADR-199 §pattern ADR-144)."""
    e5_raw = json.dumps(e5_data, sort_keys=True, ensure_ascii=False, default=str)
    e5_hash = hashlib.sha256(e5_raw.encode("utf-8")).hexdigest()[:16]
    # ev{N}: ADR-279 §E. p{prompt_version}: bump de prompt auto-invalida (emenda ADR-199).
    # rl{N}: ADR-300 — parecer cacheado sob rl antigo não passou pela red line nova.
    composite = (
        f"{workspace_id}:{e5_hash}:{manifest_version}:{schema_version}:{model_id}"
        f":ev{EVIDENCIA_VERIFICATION_VERSION}:p{prompt_version}:rl{RED_LINES_VERSION}"
    )
    digest = hashlib.sha256(composite.encode("utf-8")).hexdigest()
    return f"mathoms:llm:parecer_planejador:{digest}"


def _build_cache():
    from backend.app.services.storage.llm_cache import get_default_llm_cache

    return get_default_llm_cache()


# O cache guardava o output NU. Como ele é gravado já pós-enforcement, um hit servia
# a mutilação sem repopular a verificação — e o contador de retidos sairia 0 para um
# parecer que perdeu itens. O envelope carrega a verificação junto (ADR-366 §D7); o
# shape antigo fica ilegível e o bump de `ev` garante que nenhum hit o alcance.
@dataclass(frozen=True)
class _CachedParecer:
    """Envelope do cache: output + a verificação que o hit precisa repopular."""

    output: ParecerPlanejadorOutput
    evidencia_summary: Optional[dict]
    evidencia_entries: Optional[list[dict]]
    retention_reason: Optional[str]


# Fail-open é simetria load-bearing com o write: LLMCacheBackend não tem `delete` e o
# TTL é 7 dias, então entrada envenenada (Redis fora, shape alheio, payload truncado)
# que subisse como exceção derrubaria o stage em todo retry até o TTL expirar.
def _try_cache(cache: Any, key: str) -> Optional[_CachedParecer]:
    """Lê cache; ``None`` em miss. Fail-open como o write (ADR-144)."""
    try:
        raw = cache.get(key)
        if not raw:
            return None
        envelope = json.loads(raw)
        return _CachedParecer(
            output=ParecerPlanejadorOutput.model_validate(envelope["output"]),
            evidencia_summary=envelope.get("evidencia_summary"),
            evidencia_entries=envelope.get("evidencia_entries"),
            retention_reason=envelope.get("retention_reason"),
        )
    except Exception as exc:  # noqa: BLE001 — leitura de cache é best-effort
        logger.warning(
            "parecer_planejador_cache_read_failed",
            extra={"error": _exc_label(exc)},
        )
        return None


def _write_cache(cache: Any, key: str, cached: _CachedParecer, ttl_s: int) -> None:
    """Best-effort cache write (ADR-144 — fail open)."""
    try:
        payload = {
            "output": cached.output.model_dump(mode="json"),
            "evidencia_summary": cached.evidencia_summary,
            "evidencia_entries": cached.evidencia_entries,
            "retention_reason": cached.retention_reason,
        }
        cache.set(key, json.dumps(payload, ensure_ascii=False), ttl_s=ttl_s)
    except Exception as exc:  # noqa: BLE001 — cache write é best-effort
        logger.warning(
            "parecer_planejador_cache_write_failed",
            extra={"error": _exc_label(exc)},
        )


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
            call_hooks=config.llm_hooks,
            metrics_emitter=get_llm_metrics_emitter(),
        )
    )


@dataclass(frozen=True)
class LLMCallMetrics:
    """Custo/tokens de uma chamada. ``cost_known=False`` ⇒ ``cost_usd`` é 0.0 por
    ignorância (pricing ausente ou chamada sem registro), não por gasto zero."""

    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0  # rate USD do provider — persistência converte p/ cents (ADR-090)
    cost_known: bool = True


# Sentinela para o caminho em que nenhuma chamada foi tentada: zero é fato, não lacuna.
_NO_LLM_CALL = LLMCallMetrics()


def _extract_last_call_metrics(llm: Any, *, call_attempted: bool = True) -> LLMCallMetrics:
    """Métricas do último call do LLMService — defensivo p/ fakes."""
    # `LLMService.call` só faz `summary.calls.append` DEPOIS de `create()` retornar
    # (litellm_client.py), então falha pós-cobrança (reask storm, timeout) não deixa
    # entry. Ausência após tentativa é DESCONHECIDO — reportar 0.0 como certo mentiria
    # exatamente na classe mais cara. Recuperar o valor exige mudar o choke-point.
    summary = getattr(llm, "summary", None)
    calls = getattr(summary, "calls", None) if summary is not None else None
    if not calls:
        return LLMCallMetrics(cost_known=not call_attempted)
    last = calls[-1]
    return LLMCallMetrics(
        tokens_in=getattr(last, "tokens_in", 0) or 0,
        tokens_out=getattr(last, "tokens_out", 0) or 0,
        cost_usd=float(getattr(last, "cost_estimate_usd", 0.0) or 0.0),
        cost_known=bool(getattr(last, "cost_known", True)),
    )


# ----------------------------------------------------------------------
# Result builders
# ----------------------------------------------------------------------


# `metrics` default = _NO_LLM_CALL (zero conhecido): correto p/ cache hit e llm-None;
# caminhos pós-chamada DEVEM passar as métricas reais — rejeição já cobrada reportava
# zero (A40.l17).
def _base_result(
    *,
    output: ParecerPlanejadorOutput,
    persona_hash: str,
    manifest: ManifestData,
    config: ParecerOrchestratorConfig,
    metrics: LLMCallMetrics = _NO_LLM_CALL,
) -> ParecerGenerationResult:
    return ParecerGenerationResult(
        output=output,
        persona_hash=persona_hash,
        manifest_version=manifest.version,
        schema_version=config.schema_version,
        model_id=config.model_id,
        tier_at_generation=config.tier,
        tokens_in=metrics.tokens_in,
        tokens_out=metrics.tokens_out,
        cost_usd=metrics.cost_usd,
        cost_known=metrics.cost_known,
    )


def _placeholder_output(
    persona_hash: str, manifest: ManifestData, config: ParecerOrchestratorConfig
) -> ParecerPlanejadorOutput:
    return empty_needs_review_output(
        persona_hash=persona_hash,
        manifest_version=manifest.version,
        model_id=config.model_id,
        tier=config.tier,
    )


def _needs_review_overrides(
    reason: str,
    # Sem default de propósito: `None` é valor SIGNIFICATIVO (indisponibilidade
    # técnica, sem row) e um default o tornaria o silêncio de quem esqueceu.
    reason_code: Optional[ParecerRetentionReason],
    elapsed_ms: int,
) -> dict:
    """Campos que distinguem o desfecho retido do resultado base."""
    return {
        "status": "needs_review",
        "error_detail": reason,
        "retention_reason": reason_code.value if reason_code else None,
        "latency_ms": elapsed_ms,
    }


# `reason_code` é obrigatório de propósito (ADR-366 §D3): produtor novo não compila sem
# classificar, e assim não existe ramo que caia em parse da prosa de `error_detail`.
def _needs_review(
    *,
    reason: str,
    reason_code: Optional[ParecerRetentionReason],
    persona_hash: str,
    manifest: ManifestData,
    config: ParecerOrchestratorConfig,
    elapsed_ms: int,
    metrics: LLMCallMetrics,
) -> ParecerGenerationResult:
    """Resultado ``needs_review`` carregando o custo da chamada; não publica artifact."""
    base = _base_result(
        output=_placeholder_output(persona_hash, manifest, config),
        persona_hash=persona_hash,
        manifest=manifest,
        config=config,
        metrics=metrics,
    )
    return replace(base, **_needs_review_overrides(reason, reason_code, elapsed_ms))


def _hit_result(
    *,
    cached: _CachedParecer,
    persona_hash: str,
    manifest: ManifestData,
    config: ParecerOrchestratorConfig,
    elapsed_ms: int,
) -> ParecerGenerationResult:
    """Resultado de cache hit — sem custo, sem tokens, mas com a verificação intacta."""
    base = _base_result(
        output=cached.output, persona_hash=persona_hash, manifest=manifest, config=config
    )
    return replace(
        base,
        cache_hit=True,
        latency_ms=elapsed_ms,
        evidencia_summary=cached.evidencia_summary,
        evidencia_entries=cached.evidencia_entries,
        retention_reason=cached.retention_reason,
    )


def _success_result(
    *,
    output: ParecerPlanejadorOutput,
    persona_hash: str,
    manifest: ManifestData,
    config: ParecerOrchestratorConfig,
    tools: PlannerDrillDown,
    metrics: LLMCallMetrics,
    elapsed_ms: int,
) -> ParecerGenerationResult:
    """Empacota sucesso com as métricas da chamada."""
    base = _base_result(
        output=output, persona_hash=persona_hash, manifest=manifest, config=config, metrics=metrics
    )
    return replace(
        base,
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
    # CTO-03 (ADR-332): sanitiza PII ANTES do cache-key → e5_hash reflete o E5 já
    # sanitizado (um choke point cobre distiller + tools; re-gen única no deploy).
    e5_data = sanitize_e5_for_parecer(e5_data, config.name_role_pairs)
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
            reason_code=None,  # indisponibilidade: nada gerado, nada cobrado (ADR-366 §D6)
            persona_hash=persona_hash,
            manifest=manifest,
            config=config,
            elapsed_ms=_elapsed_ms(start),
            metrics=_NO_LLM_CALL,
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
    *, llm: Any, system_prompt: str, user_prompt: str, config: ParecerOrchestratorConfig
) -> tuple[Optional[ParecerPlanejadorOutput], Optional[str]]:
    """Invoca LLM com Instructor (output validado pelo schema); exceção vira ``(None, error_msg)``."""
    try:
        output = _invoke_parecer_llm(
            llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, config=config
        )
        _emit_riscos_truncados(output)
        return output, None
    except Exception as exc:  # noqa: BLE001 — todas exceções viram needs_review
        label = _exc_label(exc)
        logger.warning(
            "parecer_planejador_llm_call_failed",
            extra={"workspace_id": config.workspace_id, "error": label},
        )
        return None, f"LLM call failed: {label}"


def _exc_label(exc: Exception) -> str:
    """Rótulo PII-safe da exceção: tipo + classificação + nº de erros de validação."""
    # NUNCA `str(exc)`: o `ValidationError` do Instructor ecoa `input_value` — prosa que
    # o LLM derivou de dado do cliente, com valor monetário real — e a
    # `LLMValidationError` re-embrulha esse texto na própria `message`, então truncar não
    # resolve. O destino não é só o log: este rótulo vira `error_detail`, persistido em
    # `_meta` do artifact e re-logado pelo stage. Padrão de `NumberInProseWarning`:
    # contagem + rótulo estático, nunca o valor.
    parts = [type(exc).__name__]
    code = getattr(getattr(exc, "error_type", None), "value", None)
    if isinstance(code, str) and _SAFE_ERROR_CODE_RE.match(code):
        parts.append(code)
    count = _validation_error_count(exc)
    if count is not None:
        parts.append(f"{count} erro(s) de validação")
    return " · ".join(parts)


def _validation_error_count(exc: Exception) -> Optional[int]:
    """Nº de erros de validação quando a exceção os expõe estruturalmente; senão ``None``."""
    errors = getattr(exc, "validation_errors", None)  # LLMValidationError
    if isinstance(errors, list):
        return len(errors)
    counter = getattr(exc, "error_count", None)  # pydantic ValidationError
    if not callable(counter):
        return None
    try:
        return int(counter())
    except Exception:  # noqa: BLE001 — rótulo de log nunca derruba o parecer
        return None


def _invoke_parecer_llm(
    *, llm: Any, system_prompt: str, user_prompt: str, config: ParecerOrchestratorConfig
) -> ParecerPlanejadorOutput:
    return llm.call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        output_schema=ParecerPlanejadorOutput,
        stage="review_finances_holistic",
        max_tokens=config.max_tokens,
        timeout_s=config.llm_timeout_s,
        prompt_version=PROMPT_VERSION,
        prompt_name="parecer_planejador",
    ).output


def _emit_riscos_truncados(output: ParecerPlanejadorOutput) -> None:
    """A33.l7: counter OTLP que calibra o cap ≤12 riscos — best-effort, no-op sem OTLP."""
    dropped = int(getattr(output, "riscos_truncados", 0) or 0)
    if dropped <= 0:
        return
    try:
        emitter = get_llm_metrics_emitter()
        if emitter is not None:
            emitter.record_riscos_truncados(
                dropped=dropped, prompt_name="parecer_planejador", prompt_version=PROMPT_VERSION
            )
    except Exception as metrics_exc:  # noqa: BLE001 — telemetria nunca derruba o parecer
        logger.warning(
            "parecer_riscos_truncados_metric_failed",
            extra={"error": _exc_label(metrics_exc)},
        )


def _build_prompts(
    *, manifest: ManifestData, persona_body: str, e5_data: Mapping[str, Any]
) -> tuple[str, str]:
    """Constrói (system_prompt, user_prompt) via persona + manifest distillado."""
    exec_context = distill_exec_context(manifest, e5_data)
    return (
        SYSTEM_PROMPT_TEMPLATE.format(persona_body=persona_body),
        USER_PROMPT_TEMPLATE.format(exec_context=exec_context),
    )


def _check_red_lines(
    raw: ParecerPlanejadorOutput,
    e5_data: Mapping[str, Any],
    config: ParecerOrchestratorConfig,
) -> tuple[Optional[str], dict]:
    """Red lines de conselho (ADR-300): ≥1 hard-block → needs_review global; roda 1º."""
    result = check_red_lines(raw.model_dump(mode="python"), e5_data)
    reason = result.block_reason()
    if result.violations:
        ids = [v.rl_id for v in result.violations]
        logger.warning(
            "parecer_planejador_red_line_triggered",
            extra={
                "workspace_id": config.workspace_id,
                "red_lines": ids,
                "blocked": result.blocked,
                "red_lines_version": RED_LINES_VERSION,
            },
        )
    return reason, result.summary(needs_review_triggered=reason is not None)


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
) -> tuple[EvidenciaVerification, Optional[str], ParecerPlanejadorOutput, StrictDecision]:
    """Citação verificada E5→E6 (ADR-279 §E). Strict aplica enforcement per-item (ADR-295):
    item ofensor sai; needs_review só se severidade alta. Retorna (verificação, motivo de
    needs_review|None, output possivelmente com itens removidos, decisão do enforcement)."""
    # Devolve a StrictDecision inteira, não `len(dropped)`: era aqui que a camada e a
    # severidade morriam, e é delas que o desfecho persistido precisa (ADR-366 §D3).
    drill = PlannerDrillDown(
        e5_data=e5_data, section_whitelist=manifest.tools_section_whitelist, format_hints={}
    )
    verification = verify_evidencia(output=raw, drill=drill)
    log_evidencia_kpi(verification, config.workspace_id)
    if not verification.violations:
        return verification, None, raw, no_enforcement(raw)
    mode = resolve_evidencia_mode(manifest.evidencia_verification_mode)
    logger.warning(
        "parecer_planejador_evidencia_violations",
        extra={"workspace_id": config.workspace_id, "mode": mode},
    )
    if mode != "strict":
        return verification, None, raw, no_enforcement(raw)
    decision = enforce_strict_per_item(raw, verification.violations)
    if decision.needs_review_reason:
        return verification, decision.needs_review_reason, raw, decision
    if decision.dropped:
        logger.warning(
            "parecer_planejador_items_dropped",
            extra={"workspace_id": config.workspace_id, "count": len(decision.dropped)},
        )
    return verification, None, decision.output, decision


def _apply_pos_llm_guardrails(
    raw: ParecerPlanejadorOutput,
    e5_data: Mapping[str, Any],
    config: ParecerOrchestratorConfig,
) -> tuple[ParecerPlanejadorOutput, list[dict], dict]:
    """Guardrails determinísticos A28.l11 — rebaixam/removem, nunca needs_review."""
    raw, downgraded = downgrade_confianca_fallback(raw, e5_data, config.workspace_id)
    raw, audit = filter_campos_faltantes(raw, e5_data, config.workspace_id)
    return raw, audit, guardrails_summary(confianca_rebaixada=downgraded, audit=audit)


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
        llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, config=config
    )
    metrics = _extract_last_call_metrics(llm, call_attempted=True)
    if raw is None:
        return _needs_review(
            reason=err or "LLM call failed",
            reason_code=None,  # indisponibilidade: nenhum output válido (ADR-366 §D6)
            persona_hash=persona_hash,
            manifest=manifest,
            config=config,
            elapsed_ms=_elapsed_ms(start),
            metrics=metrics,
        )
    red_lines_err, red_lines_summary = _check_red_lines(raw, e5_data, config)
    if red_lines_err:
        base = _needs_review(
            reason=red_lines_err,
            reason_code=ParecerRetentionReason.conselho_vedado,
            persona_hash=persona_hash,
            manifest=manifest,
            config=config,
            elapsed_ms=_elapsed_ms(start),
            metrics=metrics,
        )
        return replace(base, red_lines_summary=red_lines_summary)
    sigilo_err = _check_sigilo(raw, config)
    if sigilo_err:
        return replace(
            _needs_review(
                reason=sigilo_err,
                reason_code=ParecerRetentionReason.sigilo,
                persona_hash=persona_hash,
                manifest=manifest,
                config=config,
                elapsed_ms=_elapsed_ms(start),
                metrics=metrics,
            ),
            red_lines_summary=red_lines_summary,
        )
    evidencia, evidencia_err, raw, decision = _check_evidencia(raw, manifest, e5_data, config)
    if evidencia_err:
        base = _needs_review(
            reason=evidencia_err,
            reason_code=decision.retention_reason,
            persona_hash=persona_hash,
            manifest=manifest,
            config=config,
            elapsed_ms=_elapsed_ms(start),
            metrics=metrics,
        )
        return replace(
            base,
            evidencia_summary=evidencia.summary(
                needs_review_triggered=True,
                retention_trigger=(
                    decision.retention_trigger.as_dict() if decision.retention_trigger else None
                ),
            ),
            evidencia_entries=evidencia.entries,
            red_lines_summary=red_lines_summary,
        )
    # A28.l11 — pós-validação, pré-finalize: rebaixamento de confiança sob premissa
    # fallback + filtro 3-vias de campos_faltantes. Coerce, nunca needs_review.
    raw, field_request_audit, pos_llm_guardrails = _apply_pos_llm_guardrails(raw, e5_data, config)
    final = finalize_output(
        output=stamp_ancora_values(raw, tools),  # ADR-296: snapshot path→valor_renderizado
        workspace_id=config.workspace_id,
        tier=config.tier,
        model_id=config.model_id,
        persona_hash=persona_hash,
        manifest_version=manifest.version,
    )
    evidencia_summary = evidencia.summary(
        needs_review_triggered=False,
        dropped_items=[d.as_dict() for d in decision.dropped],
    )
    _write_cache(
        cache,
        cache_key,
        _CachedParecer(
            output=final,
            evidencia_summary=evidencia_summary,
            evidencia_entries=evidencia.entries,
            retention_reason=(
                decision.retention_reason.value if decision.retention_reason else None
            ),
        ),
        ttl_s=config.cache_ttl_s,
    )
    success = _success_result(
        output=final,
        persona_hash=persona_hash,
        manifest=manifest,
        config=config,
        tools=tools,
        metrics=metrics,
        elapsed_ms=_elapsed_ms(start),
    )
    return replace(
        success,
        evidencia_summary=evidencia_summary,
        evidencia_entries=evidencia.entries,
        red_lines_summary=red_lines_summary,
        field_request_audit=field_request_audit or None,
        pos_llm_guardrails=pos_llm_guardrails,
        retention_reason=decision.retention_reason.value if decision.retention_reason else None,
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
