"""ADR-447 — a falha técnica do parecer leva a classe do objeto da exceção; a retenção não.

`_call_llm_safe` era o segundo achatamento: o objeto vivo virava o rótulo
`"LLM call failed: <tipo>"` e o stage declarava `reason` em prosa, que nenhum mapa
lê — `reason_class: unknown` para budget, timeout e provider do único stage
degradável com LLM, justamente o que o card de `/admin/metrics` observa.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app.models.planner_review import ParecerRetentionReason
from backend.app.services.parecer_manifest import load_manifest, load_persona
from backend.app.services.parecer_orchestrator import (
    LLMCallMetrics,
    ParecerOrchestratorConfig,
    _needs_review,
    generate_parecer,
)
from backend.app.services.storage.llm_cache import InMemoryLLMCache
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.llm.call_hooks import LLMBudgetExceededError
from pipeline.llm.error_classification import LLMError, LLMErrorType
from pipeline.stage_failure_reason import (
    FAILURE_CLASS_KEY,
    StageFailureReason,
    reason_from_stage_detail,
)
from pipeline.stages.parecer_planejador import _needs_review_return
from tests.fakes.parecer import (
    FailingLLM,
    FakeLLMService,
    ValidationFailingLLM,
    make_valid_parecer_output,
)

_E5 = {"patrimonio": {"bruto": 1}}


def _gerar(llm_service, ws: str = "ws-failure-class"):
    return generate_parecer(
        e5_data=_E5,
        config=ParecerOrchestratorConfig(workspace_id=ws, tier="premium"),
        llm_service=llm_service,
        cache=InMemoryLLMCache(),
    )


def _sigilo_output():
    """Output que o check de sigilo §13 retém — retenção por política, não falha técnica."""
    return make_valid_parecer_output().model_copy(
        update={
            "diagnostico_geral": (
                "Família segue metodologia consagrada do mercado financeiro brasileiro "
                "ainda com gaps. Aplicação direta de princípios Perini ajudaria."
            )
        }
    )


_FALHAS_TECNICAS = [
    pytest.param(
        LLMBudgetExceededError("ws-sintetico", Decimal("11.00"), Decimal("10.00")),
        "budget_exhausted",
        id="budget",
    ),
    pytest.param(
        LLMError("LLM call failed after 4 attempts (600412ms): timed out", LLMErrorType.timeout),
        "timeout",
        id="timeout",
    ),
    pytest.param(
        LLMError("LLM call failed after 4 attempts: overloaded", LLMErrorType.provider_error),
        "provider_error",
        id="provider",
    ),
    pytest.param(RuntimeError("provider exploded"), "internal_error", id="generica"),
]


@pytest.mark.parametrize(("exc", "esperado"), _FALHAS_TECNICAS)
def test_falha_tecnica_leva_a_classe_do_objeto(exc, esperado):
    result = _gerar(FailingLLM(exc))

    assert result.status == "needs_review"
    assert result.retention_reason is None
    assert result.failure_class == esperado


def test_validacao_esgotada_e_output_invalido():
    """O reask storm (ADR-292/294) é output rejeitado pelo schema, não bug nosso."""
    assert _gerar(ValidationFailingLLM("campo x")).failure_class == "output_invalid"


def test_llm_indisponivel_e_llm_unavailable(monkeypatch):
    """Sem exceção para classificar: a constante tipada, nunca a prosa do motivo."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = _gerar(llm_service=None)

    assert result.retention_reason is None
    assert result.failure_class == StageFailureReason.llm_unavailable.value


def test_retencao_por_politica_nao_leva_classe_tecnica():
    result = _gerar(FakeLLMService(output=_sigilo_output()))

    assert result.status == "needs_review"
    assert result.retention_reason is not None
    assert result.failure_class is None


@pytest.mark.parametrize(
    ("reason_code", "failure_class"),
    [(None, None), (ParecerRetentionReason.sigilo, StageFailureReason.timeout)],
    ids=["nenhuma", "as-duas"],
)
def test_needs_review_exige_exatamente_uma_classificacao(reason_code, failure_class):
    """Retenção e falha técnica são XOR — o decoder nunca precisa desempatar."""
    with pytest.raises(ValueError, match="exatamente um"):
        _needs_review(
            reason="x",
            reason_code=reason_code,
            failure_class=failure_class,
            persona_hash=load_persona()[1],
            manifest=load_manifest(),
            config=ParecerOrchestratorConfig(workspace_id="ws-xor", tier="premium"),
            elapsed_ms=0,
            metrics=LLMCallMetrics(),
        )


@pytest.mark.parametrize(("exc", "esperado"), _FALHAS_TECNICAS)
def test_stage_leva_a_classe_no_detail(exc, esperado):
    """O retorno do stage é o que o executor repassa ao loop — a classe tem de estar nele."""
    detail = _needs_review_return(_gerar(FailingLLM(exc)), "ws-x", InMemoryArtifactStore())

    assert detail[FAILURE_CLASS_KEY] == esperado
    assert reason_from_stage_detail(detail).value == esperado


def test_stage_retido_nao_leva_a_chave():
    detail = _needs_review_return(
        _gerar(FakeLLMService(output=_sigilo_output())), "ws-x", InMemoryArtifactStore()
    )

    assert FAILURE_CLASS_KEY not in detail
    assert reason_from_stage_detail(detail) is StageFailureReason.enforcement
