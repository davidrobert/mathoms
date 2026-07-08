"""Guardrails determinísticos pós-LLM do parecer (A28.l11 · ADR-294/295).

Fixtures sintéticas PII-zero. Cobre: (1) rebaixamento de confiança sob premissa
fallback do Monte Carlo (incl. interação com o drop de impacto_estimado quando
confianca != alta); (2) filtro 3-vias de campos_faltantes_pediria_se_iterasse;
(3) invariante do critério de aceite — nenhum guardrail marca needs_review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.services.parecer_orchestrator import (
    ParecerOrchestratorConfig,
    generate_parecer,
)
from backend.app.services.parecer_pos_llm_guardrails import (
    REASON_SPURIOUS,
    REASON_WRONG_PATH,
    downgrade_confianca_fallback,
    filter_campos_faltantes,
    guardrails_summary,
)
from backend.app.services.storage.llm_cache import InMemoryLLMCache
from pipeline.llm.schemas.parecer_planejador import (
    Ancora,
    CampoFaltante,
    ImpactoEstimado,
    Metadata,
    ParecerPlanejadorOutput,
    PontoForte,
    Risco,
    Sugestao,
)

WS = "ws-guardrails-test"

# E5 sintético PII-zero: premissas em fallback + dado de dependentes presente
# no path canônico ($.irpf_kpis) e ausente no path errado ($.composicao_familiar).
E5_PARCIAL: dict[str, Any] = {
    "premissas_economicas": {"status": "parcial"},
    "if_monte_carlo": {"prob_sucesso_pct": 31.0},
    "irpf_kpis": {"dependentes": {"count": 2, "por_relacao": {"filho": 2}}},
    "patrimonio": {"bruto": 1_000_000},
}

E5_COMPLETO: dict[str, Any] = {**E5_PARCIAL, "premissas_economicas": {"status": "completo"}}


def _metadata() -> Metadata:
    return Metadata(
        persona_hash="0" * 64,
        manifest_version="1.0.0",
        model_id="placeholder",
        tier_at_generation="premium",
        generated_at="2026-07-06T12:00:00+00:00",
    )


def _pontos_fortes() -> list[PontoForte]:
    return [
        PontoForte(
            titulo=f"Ponto forte {i}",
            descricao="Descrição neutra do ponto forte, sem ticker e sem citar metodologia.",
            ancora_metodologica="convergencia",
            tema_canonico="Saúde de balanço",
            section_id="S10",
        )
        for i in range(3)
    ]


def _ancora_mc() -> Ancora:
    return Ancora(path="$.if_monte_carlo.prob_sucesso_pct", rotulo="if_monte_carlo")


def _risco_mc(confianca: str = "alta") -> Risco:
    return Risco(
        severidade="Alta",
        titulo="Probabilidade de atingir a independência abaixo do desejável",
        descricao="A projeção de longo prazo indica probabilidade reduzida de sucesso.",
        ancora_metodologica="convergencia",
        tema_canonico="Renda passiva",
        section_id="S7",
        ancoras=[_ancora_mc()],
        confianca=confianca,  # type: ignore[arg-type]
    )


def _impacto_fluxo_anual() -> ImpactoEstimado:
    return ImpactoEstimado(
        valor_estimado_brl=120_000.0,
        unidade="ano",
        caveat="Projeção condicionada às premissas vigentes do modelo.",
        tipo="fluxo_anual",
    )


def _sugestao_mc(confianca: str = "alta", *, com_impacto: bool = True) -> Sugestao:
    impacto = _impacto_fluxo_anual() if com_impacto else None
    return Sugestao(
        prioridade="P1",
        acao="Revisar a política de alocação-alvo considerando o horizonte projetado.",
        impacto_qualitativo="Aumenta a robustez do plano de longo prazo frente às premissas.",
        ancora_metodologica="convergencia",
        tema_canonico="Alocação",
        confianca=confianca,  # type: ignore[arg-type]
        section_id="S7",
        suggestion_dedup_key="0" * 64,
        impacto_estimado=impacto,
        ancoras=[_ancora_mc()],
    )


def _sugestao_sem_mc() -> Sugestao:
    return Sugestao(
        prioridade="P2",
        acao="Consolidar o acompanhamento mensal das despesas essenciais da família.",
        impacto_qualitativo="Melhora a visibilidade do orçamento e a disciplina de execução.",
        ancora_metodologica="convergencia",
        tema_canonico="Saúde de balanço",
        confianca="alta",
        section_id="S2",
        suggestion_dedup_key="0" * 64,
        impacto_estimado=ImpactoEstimado(
            valor_estimado_brl=6_000.0,
            unidade="ano",
            caveat="Estimativa baseada no padrão de gastos observado no período.",
            tipo="outro",
        ),
        ancoras=[Ancora(path="$.patrimonio.bruto", rotulo="patrimonio")],
    )


_DIAGNOSTICO = (
    "Família com estrutura patrimonial consolidada e projeção de longo prazo "
    "sensível às premissas econômicas vigentes no período analisado."
)


def make_output(
    *,
    riscos: list[Risco] | None = None,
    sugestoes: list[Sugestao] | None = None,
    campos: list[CampoFaltante] | None = None,
) -> ParecerPlanejadorOutput:
    return ParecerPlanejadorOutput(
        version="2.0",
        metadata=_metadata(),
        diagnostico_geral=_DIAGNOSTICO,
        pontos_fortes=_pontos_fortes(),
        riscos=riscos or [],
        sugestoes_execucao=sugestoes or [],
        sugestoes_taticas=[],
        sugestoes_estrategicas=[],
        metricas=[],
        notas_metodologicas=[],
        campos_faltantes_pediria_se_iterasse=campos,
    )


# -----------------------------------------------------------------------
# (1) Rebaixamento de confiança sob premissa fallback
# -----------------------------------------------------------------------


class TestDowngradeConfiancaFallback:
    def test_parcial_downgrades_anchored_items_and_drops_impacto(self):
        """Critério de aceite: parcial + alta ancorado em $.if_monte_carlo.* →
        confianca=media E impacto_estimado is None (interação com ADR-294)."""
        output = make_output(riscos=[_risco_mc("alta")], sugestoes=[_sugestao_mc("alta")])
        result, count = downgrade_confianca_fallback(output, E5_PARCIAL, WS)
        assert count == 2
        assert result.riscos[0].confianca == "media"
        assert result.sugestoes_execucao[0].confianca == "media"
        assert result.sugestoes_execucao[0].impacto_estimado is None

    def test_completo_keeps_output_intact(self):
        output = make_output(riscos=[_risco_mc("alta")], sugestoes=[_sugestao_mc("alta")])
        result, count = downgrade_confianca_fallback(output, E5_COMPLETO, WS)
        assert count == 0
        assert result is output
        assert result.sugestoes_execucao[0].confianca == "alta"
        assert result.sugestoes_execucao[0].impacto_estimado is not None

    def test_premissas_absent_keeps_output_intact(self):
        output = make_output(sugestoes=[_sugestao_mc("alta")])
        result, count = downgrade_confianca_fallback(output, {"patrimonio": {"bruto": 1}}, WS)
        assert count == 0
        assert result is output

    def test_item_not_anchored_on_monte_carlo_untouched(self):
        output = make_output(sugestoes=[_sugestao_sem_mc()])
        result, count = downgrade_confianca_fallback(output, E5_PARCIAL, WS)
        assert count == 0
        assert result.sugestoes_execucao[0].confianca == "alta"
        assert result.sugestoes_execucao[0].impacto_estimado is not None

    def test_confianca_media_not_promoted_nor_touched(self):
        """Rebaixar, nunca promover (ADR-294 'dropar > promover')."""
        output = make_output(sugestoes=[_sugestao_mc("media", com_impacto=False)])
        result, count = downgrade_confianca_fallback(output, E5_PARCIAL, WS)
        assert count == 0
        assert result.sugestoes_execucao[0].confianca == "media"


# -----------------------------------------------------------------------
# (2) Filtro 3-vias de campos_faltantes
# -----------------------------------------------------------------------


def _campos_3_vias() -> list[CampoFaltante]:
    return [
        CampoFaltante(
            field_path="$.patrimonio.bruto", motivo="detalhar a composição do patrimônio"
        ),
        CampoFaltante(
            field_path="$.composicao_familiar.dependentes",
            motivo="quantos dependentes a família possui",
        ),
        CampoFaltante(
            field_path="$.protecao_patrimonial.apolices",
            motivo="apólices vigentes por categoria",
        ),
    ]


class TestFilterCamposFaltantes3Vias:
    def test_spurious_removed_wrong_path_reannotated_absent_kept(self):
        output = make_output(campos=_campos_3_vias())
        result, audit = filter_campos_faltantes(output, E5_PARCIAL, WS)

        kept = result.campos_faltantes_pediria_se_iterasse
        assert [c.field_path for c in kept] == ["$.protecao_patrimonial.apolices"]

        by_reason = {a["reason"]: a for a in audit}
        assert set(by_reason) == {REASON_SPURIOUS, REASON_WRONG_PATH}
        assert by_reason[REASON_SPURIOUS]["field_path"] == "$.patrimonio.bruto"
        wrong = by_reason[REASON_WRONG_PATH]
        assert wrong["field_path"] == "$.composicao_familiar.dependentes"
        assert wrong["alias_path"] == "$.irpf_kpis.dependentes"
        assert "[reanotado: dado presente em $.irpf_kpis.dependentes]" in wrong["motivo"]

    def test_alias_null_in_e5_keeps_entry(self):
        """Alias conhecido mas dado ausente no E5 → genuinamente faltante, mantém."""
        e5_sem_irpf = {"premissas_economicas": {"status": "completo"}}
        output = make_output(
            campos=[
                CampoFaltante(
                    field_path="$.composicao_familiar.dependentes",
                    motivo="quantos dependentes a família possui",
                )
            ]
        )
        result, audit = filter_campos_faltantes(output, e5_sem_irpf, WS)
        assert audit == []
        assert len(result.campos_faltantes_pediria_se_iterasse) == 1

    def test_coerced_none_path_kept(self):
        """Path coercido → None (ADR-292): motivo carrega o sinal, entrada mantida."""
        output = make_output(
            campos=[CampoFaltante(field_path=None, motivo="path fora do subset suportado")]
        )
        result, audit = filter_campos_faltantes(output, E5_PARCIAL, WS)
        assert audit == []
        assert len(result.campos_faltantes_pediria_se_iterasse) == 1

    def test_absent_campos_is_noop(self):
        output = make_output(campos=None)
        result, audit = filter_campos_faltantes(output, E5_PARCIAL, WS)
        assert result is output
        assert audit == []

    def test_summary_counts_and_never_needs_review(self):
        output = make_output(campos=_campos_3_vias())
        _, audit = filter_campos_faltantes(output, E5_PARCIAL, WS)
        summary = guardrails_summary(confianca_rebaixada=2, audit=audit)
        assert summary == {
            "confianca_rebaixada": 2,
            "field_requests_spurious": 1,
            "field_requests_wrong_path": 1,
            "needs_review_triggered": False,
        }


# -----------------------------------------------------------------------
# (3) End-to-end via generate_parecer (LLM fake) — nunca needs_review
# -----------------------------------------------------------------------


@dataclass
class _FakeLLMCallResult:
    output: Any
    tokens_in: int = 100
    tokens_out: int = 50
    cost_estimate_usd: float = 0.01  # rate USD mock (ADR-090 — prod converte p/ cents)


@dataclass
class _FakeLLMSummary:
    calls: list = field(default_factory=list)


class _FakeLLMService:
    def __init__(self, output: ParecerPlanejadorOutput) -> None:
        self._output = output
        self.summary = _FakeLLMSummary()

    def call(self, **kwargs) -> _FakeLLMCallResult:
        result = _FakeLLMCallResult(output=self._output)
        self.summary.calls.append(result)
        return result


def _generate(output: ParecerPlanejadorOutput, e5: dict):
    config = ParecerOrchestratorConfig(workspace_id=WS, tier="premium")
    return generate_parecer(
        e5_data=e5, config=config, llm_service=_FakeLLMService(output), cache=InMemoryLLMCache()
    )


class TestGuardrailsEndToEnd:
    def test_fallback_downgrade_applied_before_finalize(self):
        raw = make_output(riscos=[_risco_mc("alta")], sugestoes=[_sugestao_mc("alta")])
        result = _generate(raw, E5_PARCIAL)

        assert result.status == "Gerado"  # guardrail nunca marca needs_review
        assert result.output.riscos[0].confianca == "media"
        assert result.output.sugestoes_execucao[0].confianca == "media"
        assert result.output.sugestoes_execucao[0].impacto_estimado is None
        assert result.pos_llm_guardrails["confianca_rebaixada"] == 2
        assert result.pos_llm_guardrails["needs_review_triggered"] is False

    def test_completo_leaves_confianca_intact_end_to_end(self):
        raw = make_output(riscos=[_risco_mc("alta")], sugestoes=[_sugestao_mc("alta")])
        result = _generate(raw, E5_COMPLETO)

        assert result.status == "Gerado"
        assert result.output.riscos[0].confianca == "alta"
        assert result.output.sugestoes_execucao[0].impacto_estimado is not None
        assert result.pos_llm_guardrails["confianca_rebaixada"] == 0

    def test_3_vias_filters_output_and_emits_audit(self):
        raw = make_output(campos=_campos_3_vias())
        result = _generate(raw, E5_PARCIAL)

        assert result.status == "Gerado"
        kept = result.output.campos_faltantes_pediria_se_iterasse
        assert [c.field_path for c in kept] == ["$.protecao_patrimonial.apolices"]
        assert {a["reason"] for a in result.field_request_audit} == {
            REASON_SPURIOUS,
            REASON_WRONG_PATH,
        }
        assert result.pos_llm_guardrails["field_requests_spurious"] == 1
        assert result.pos_llm_guardrails["field_requests_wrong_path"] == 1
        assert result.pos_llm_guardrails["needs_review_triggered"] is False
