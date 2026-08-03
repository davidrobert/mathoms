"""Fakes e builders do parecer planejador — compartilhados pelos testes do stage E6.

Vive em ``tests/fakes/`` por CLAUDE.md §Testes ("mocks de I/O externo via fakes
nomeados, não MagicMock inline"). ``FailingLLM``/``ValidationFailingLLM`` guardam
``summary`` por INSTÂNCIA: como atributo de classe, o ``calls`` de ``FakeLLMSummary``
seria default mutável compartilhado entre testes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pipeline.llm.error_classification import LLMValidationError
from pipeline.llm.schemas.parecer_planejador import (
    Metadata,
    ParecerPlanejadorOutput,
    PontoForte,
    Risco,
    Sugestao,
)


def make_valid_parecer_output() -> ParecerPlanejadorOutput:
    """Output Pydantic válido (todos invariantes obedecidos)."""
    metadata = Metadata(
        persona_hash="0" * 64,
        manifest_version="1.0.0",
        model_id="placeholder",
        tier_at_generation="premium",
        generated_at="2026-05-13T12:00:00+00:00",
    )
    pontos = [
        PontoForte(
            titulo=f"Ponto forte {i}",
            descricao="Descrição neutra do ponto forte sem ticker e sem citar metodologia interna.",
            ancora_metodologica="convergencia",
            tema_canonico="Saúde de balanço",
            section_id="S10",
        )
        for i in range(3)
    ]
    sug1 = Sugestao(
        prioridade="P1",
        acao="Constituir reserva de emergência cobrindo seis meses de despesas essenciais.",
        impacto_qualitativo="Reduz dependência de crédito em caso de evento adverso e fortalece resiliência.",
        ancora_metodologica="convergencia",
        tema_canonico="Liquidez",
        confianca="alta",
        section_id="S1",
        suggestion_dedup_key="0" * 64,
    )
    return ParecerPlanejadorOutput(
        version="1.0",
        metadata=metadata,
        diagnostico_geral=(
            "Família com patrimônio bruto consolidado e taxa de poupança razoável; "
            "estrutura de proteção e reserva ainda apresenta gaps materiais."
        ),
        pontos_fortes=pontos,
        riscos=[
            Risco(
                severidade="Alta",
                titulo="Reserva de emergência insuficiente",
                descricao=(
                    "A cobertura atual da reserva fica abaixo do alvo recomendado de seis meses."
                ),
                ancora_metodologica="convergencia",
                tema_canonico="Liquidez",
                section_id="S1",
                evidencia_path="$.reserva_emergencia.cobertura_meses",
                confianca="alta",
            )
        ],
        sugestoes_execucao=[sug1],
        sugestoes_taticas=[],
        sugestoes_estrategicas=[],
        metricas=[],
        notas_metodologicas=[],
    )


@dataclass
class FakeLLMCallResult:
    output: Any
    tokens_in: int = 1234
    tokens_out: int = 567
    cost_estimate_usd: float = 0.0123  # rate USD mock (ADR-090 — production converts to cents)


@dataclass
class FakeLLMSummary:
    calls: list = field(default_factory=list)


class FakeLLMService:
    """LLM service que devolve output canned em vez de chamar API."""

    def __init__(self, output: ParecerPlanejadorOutput) -> None:
        self._output = output
        self.summary = FakeLLMSummary()
        self.last_call_kwargs: dict = {}

    def call(self, **kwargs) -> FakeLLMCallResult:
        self.last_call_kwargs = kwargs
        result = FakeLLMCallResult(output=self._output)
        self.summary.calls.append(result)
        return result


class FailingLLM:
    """Levanta na chamada — exercita o retorno needs_review por falha de LLM."""

    def __init__(self, exc: Exception | None = None) -> None:
        self.summary = FakeLLMSummary()
        self._exc = exc or RuntimeError("provider exploded")

    def call(self, **kwargs):
        raise self._exc


class ValidationFailingLLM:
    """Levanta ``LLMValidationError`` carregando prosa do cliente no texto."""

    def __init__(self, inner: str) -> None:
        self.summary = FakeLLMSummary()
        self._inner = inner

    def call(self, **kwargs):
        raise LLMValidationError(
            f"Output validation failed after 3 attempts: {self._inner}",
            validation_errors=[self._inner],
        )
