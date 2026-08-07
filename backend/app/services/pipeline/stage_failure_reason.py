"""Classe da não-entrega de um stage — descritiva, nunca dispositiva (ADR-357 §2)."""

# **Descritivo, nunca dispositivo.** `reason_class` entra em copy, log e alerta;
# NENHUMA ramificação de status o consulta. É essa a diferença verificável entre
# ele e o contrato `{"degraded": True}` que a §2 rejeitou: lá o produtor nomeava o
# próprio raio de explosão, aqui ele só descreve o que aconteceu. A mutação que o
# teste paramétrico mata é `if reason_class == "budget_exhausted": failed`.
#
# **Nunca derivado de match de string sobre a mensagem** — isso seria classificação
# fabricada, e o repo já tem uma: `output_summary["error_type"]` é hoje
# `exc_error.split(":")[0]`, o primeiro segmento da MENSAGEM, renderizado ao
# usuário como "tipo" no `FailedRunCard`. Aqui a fonte é `type(exc)` (isinstance
# primeiro) e `exc.error_type` (o enum tipado do classificador).

from __future__ import annotations

import enum

from pipeline.llm.error_classification import LLMErrorType


class StageFailureReason(str, enum.Enum):
    """Por que o stage não entregou. Fechado; membro sem produtor é vocabulário pré-pago."""

    enforcement = "enforcement"
    output_invalid = "output_invalid"
    provider_error = "provider_error"
    network = "network"
    timeout = "timeout"
    budget_exhausted = "budget_exhausted"
    llm_unavailable = "llm_unavailable"
    missing_input = "missing_input"
    internal_error = "internal_error"
    unknown = "unknown"


# Mapa TOTAL sobre `LLMErrorType` — gateado por teste. Função parcial aqui
# significa que uma classe de falha real cai em `unknown` e o card de
# `/admin/metrics` mente por omissão.
#
# `validation` → `output_invalid`, e não `internal_error`: é o modo de falha mais
# frequente do parecer (o reask storm da ADR-292/294), e é output REJEITADO pelo
# schema, não bug nosso. `context_length` → `internal_error` porque o prompt
# estourar a janela é defeito do builder. `auth` → `llm_unavailable`: sem
# credencial válida o provider é inalcançável, e é isso que a copy precisa dizer.
_REASON_BY_LLM_ERROR: dict[LLMErrorType, StageFailureReason] = {
    LLMErrorType.auth: StageFailureReason.llm_unavailable,
    LLMErrorType.rate_limit: StageFailureReason.provider_error,
    LLMErrorType.timeout: StageFailureReason.timeout,
    LLMErrorType.network: StageFailureReason.network,
    LLMErrorType.validation: StageFailureReason.output_invalid,
    LLMErrorType.context_length: StageFailureReason.internal_error,
    LLMErrorType.provider_error: StageFailureReason.provider_error,
    LLMErrorType.unknown: StageFailureReason.unknown,
}

# Motivos declarados pelos stages determinísticos da cauda, no campo `reason` do
# retorno. `missing_input` existe porque colapsá-los em `internal_error`
# classificaria lacuna de UPSTREAM como bug nosso.
_REASON_BY_STAGE_REASON: dict[str, StageFailureReason] = {
    "e5_not_found": StageFailureReason.missing_input,
    "missing_narrativas": StageFailureReason.missing_input,
    "validation_failed": StageFailureReason.output_invalid,
    "unknown_mode": StageFailureReason.internal_error,
}


def reason_from_exception(exc: BaseException) -> StageFailureReason:
    """Classe a partir do objeto de exceção — `isinstance` primeiro, `error_type` depois."""
    # `LLMBudgetExceededError` é `Exception` pura e **não tem** `error_type`: um
    # classificador escrito só sobre `error_type` jogaria o hard-stop de budget
    # (ADR-173) em `unknown` — e `budget_exhausted` é justamente o membro cuja
    # copy o cliente não pode confundir com falha técnica transitória.
    from pipeline.llm.call_hooks import LLMBudgetExceededError

    if isinstance(exc, LLMBudgetExceededError):
        return StageFailureReason.budget_exhausted
    error_type = getattr(exc, "error_type", None)
    if isinstance(error_type, LLMErrorType):
        return _REASON_BY_LLM_ERROR[error_type]
    return StageFailureReason.internal_error


def reason_from_stage_detail(detail) -> StageFailureReason:
    """Classe a partir do `detail` do stage que declarou não-entrega."""
    if not isinstance(detail, dict):
        return StageFailureReason.unknown
    if detail.get("retention_reason"):
        # Projeção de `ParecerRetentionReason` (ADR-366), não canal concorrente:
        # `retention_reason` presente ⇒ juízo de política sobre o conteúdo. Derivar
        # em vez de duplicar é o que impede os dois de discordarem.
        return StageFailureReason.enforcement
    declared = detail.get("reason")
    if isinstance(declared, str) and declared in _REASON_BY_STAGE_REASON:
        return _REASON_BY_STAGE_REASON[declared]
    return StageFailureReason.unknown
