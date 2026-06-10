"""Harness de localização de bug via lineage (ADR-281 · A25.l4 F7) — consumido pelo eval de injeção (nightly) e por agente de debug sobre goldens: 1 conversa LLM com loop de tools capado (max_tool_iterations=6), structured output ``LineageDebugStep``; parse-fail 2× = miss (nunca crash); model/temp pinados em ``config/prompts/lineage_debug.yaml``."""

from __future__ import annotations

import json
import logging
from dataclasses import MISSING, dataclass, field
from pathlib import Path

import yaml

from pipeline.domain.services.lineage_debug_tools import LineageDebugTools
from pipeline.domain.services.lineage_render_llm import render_lineage_linear
from pipeline.domain.services.lineage_resolver import LineageResolver
from pipeline.llm.litellm_client import LLMValidationError
from pipeline.llm.schemas.lineage_debug import LineageDebugStep, LocalizationResult

logger = logging.getLogger("mathoms.llm.lineage_eval")

_DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "prompts" / "lineage_debug.yaml"
)
_MAX_PARSE_FAILURES = 2
# Sentinela de _advance: a conversa continua (≠ terminou com miss_reason).
_CONTINUE = object()


@dataclass(frozen=True)
class LineageDebugConfig:
    """Config pinada do harness (model literal, temp=0 — ver YAML)."""

    version: str
    model_id: str
    temperature: float
    max_tokens: int
    max_tool_iterations: int
    trials_per_case: int
    accuracy_floor: float
    regression_band_pp: float
    usd_cap_run: float  # gasto estimado de API LLM (rate USD), não money de domínio (ADR-090)
    usd_cap_call_soft: float  # idem — soft cap por call (rate USD)
    system_prompt: str
    seed: int | None = None  # best-effort (provider sem suporte descarta via drop_params)


def load_lineage_debug_config(path: Path | None = None) -> LineageDebugConfig:
    raw = yaml.safe_load((path or _DEFAULT_CONFIG_PATH).read_text(encoding="utf-8"))
    fields = LineageDebugConfig.__dataclass_fields__
    missing = [n for n, f in fields.items() if f.default is MISSING and n not in raw]
    if missing:
        raise ValueError(f"lineage_debug.yaml sem campo obrigatório: {missing}")
    return LineageDebugConfig(**{n: raw[n] for n in fields if n in raw})


@dataclass
class LocalizationOutcome:
    """Resultado de 1 trial de localize — telemetria p/ métricas do eval."""

    result: LocalizationResult | None = None
    miss_reason: str | None = None
    llm_calls: int = 0
    tool_iterations: int = 0
    parse_failures: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    usd_spent: float = 0.0  # rate USD estimado (paridade LLMCallResult.cost_estimate_usd)
    tool_trace: list[dict] = field(default_factory=list)

    @property
    def localized(self) -> bool:
        return self.result is not None


@dataclass
class _Conversation:
    transcript: list[str]
    outcome: LocalizationOutcome
    forced_final: bool = False


def localize(
    *,
    complaint: str,
    entry_field: str,
    tools: LineageDebugTools,
    llm_service,
    config: LineageDebugConfig,
) -> LocalizationOutcome:
    """Roda a conversa de localização; retorna outcome mesmo em miss."""
    conversation = _Conversation(
        transcript=[_initial_context(complaint, entry_field, tools)],
        outcome=LocalizationOutcome(),
    )
    max_llm_calls = config.max_tool_iterations + 2
    while conversation.outcome.llm_calls < max_llm_calls:
        verdict = _advance(conversation, tools, llm_service, config)
        if verdict is not _CONTINUE:
            return _finish(conversation.outcome, tools, miss_reason=verdict)
    return _finish(conversation.outcome, tools, miss_reason="llm_call_budget_exhausted")


def _advance(conversation: _Conversation, tools, llm_service, config) -> object:
    """1 passo da conversa: ``_CONTINUE`` | miss_reason (str) | ``None`` (sucesso)."""
    outcome = conversation.outcome
    step = _next_step(conversation, llm_service, config)
    if step is None:
        return "parse_failure" if outcome.parse_failures >= _MAX_PARSE_FAILURES else _CONTINUE
    if step.action == "localize":
        outcome.result = step.localization
        return None
    if conversation.forced_final:
        return "tool_budget_exhausted"
    if tools.iterations_count >= config.max_tool_iterations:
        conversation.forced_final = True
        conversation.transcript.append(
            "Limite de tools atingido. Responda action='localize' agora."
        )
        return _CONTINUE
    conversation.transcript.append(_run_tool(tools, step))
    return _CONTINUE


def _initial_context(complaint: str, entry_field: str, tools: LineageDebugTools) -> str:
    tree = LineageResolver(tools.store).resolve(tools.stage, tools.artifact_key, entry_field)
    rendered = render_lineage_linear(tree)
    return (
        f"Reclamação: {complaint}\n\n"
        f"Árvore de lineage de {tools.stage}/{tools.artifact_key} :: {entry_field}:\n{rendered}"
    )


def _next_step(
    conversation: _Conversation, llm_service, config: LineageDebugConfig
) -> LineageDebugStep | None:
    """1 chamada LLM; ``None`` = parse failure (registrada no outcome)."""
    outcome = conversation.outcome
    outcome.llm_calls += 1
    try:
        call = llm_service.call(
            system_prompt=config.system_prompt,
            user_prompt="\n\n".join(conversation.transcript),
            output_schema=LineageDebugStep,
            max_retries=0,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            stage="lineage-debug",
            seed=config.seed,
        )
    except LLMValidationError as exc:
        outcome.parse_failures += 1
        logger.warning("lineage-debug parse failure %d: %s", outcome.parse_failures, str(exc)[:200])
        conversation.transcript.append(
            "Resposta anterior inválida — responda JSON conforme o schema."
        )
        return None
    _record_usage(outcome, call, config)
    return call.output


def _record_usage(outcome: LocalizationOutcome, call, config: LineageDebugConfig) -> None:
    outcome.tokens_in += getattr(call, "tokens_in", 0)
    outcome.tokens_out += getattr(call, "tokens_out", 0)
    spent = getattr(call, "cost_estimate_usd", 0.0)
    outcome.usd_spent += spent
    if spent > config.usd_cap_call_soft:
        logger.warning(
            "lineage-debug call custou $%.4f > soft cap $%.2f", spent, config.usd_cap_call_soft
        )


def _run_tool(tools: LineageDebugTools, step: LineageDebugStep) -> str:
    if step.action == "expand_node":
        result = tools.expand_node(
            step.stage or tools.stage, step.artifact_key or tools.artifact_key, step.field or ""
        )
    else:
        result = tools.trace_source(step.field or "")
    payload = json.dumps(result, ensure_ascii=False, default=str)
    return f"Resultado de {step.action}({step.field}):\n{payload}"


def _finish(
    outcome: LocalizationOutcome, tools: LineageDebugTools, *, miss_reason: str | None
) -> LocalizationOutcome:
    outcome.miss_reason = miss_reason
    outcome.tool_iterations = tools.iterations_count
    outcome.tool_trace = tools.to_trace_dicts()
    return outcome
