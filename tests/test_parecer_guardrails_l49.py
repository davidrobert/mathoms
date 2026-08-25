"""A40.l49 — guardrails que passam a poder falhar (MC lemma/S7, ano, needs_review)."""

from __future__ import annotations

from backend.app.services.parecer_pos_llm_guardrails import (
    REASON_SPURIOUS,
    downgrade_confianca_fallback,
    filter_campos_faltantes,
    guardrails_summary,
)
from pipeline.llm.schemas.parecer_planejador import Ancora, CampoFaltante, Risco
from tests.test_parecer_guardrails_pos_llm import (
    E5_PARCIAL,
    WS,
    _generate,
    _risco_mc,
    make_output,
)


def _filtra(output, e5, *, catalogo=None):
    """Wrapper de teste. Por default assume que TODO path pedido era citável — assim o
    teste que não é sobre o catálogo mede exatamente o que media antes da A40.l83, e só
    quem quer exercitar `out_of_catalog` passa `catalogo` explícito."""
    paths = (
        catalogo
        if catalogo is not None
        else frozenset(
            c.field_path
            for c in (output.campos_faltantes_pediria_se_iterasse or [])
            if c.field_path
        )
    )
    return filter_campos_faltantes(output, e5, WS, catalog_paths=paths)


class TestDowngradePorLemmaS7:
    def test_s7_lemma_without_mc_anchor_downgrades(self):
        risco = _risco_mc("alta").model_copy(
            update={"ancoras": [Ancora(path="$.patrimonio.bruto", rotulo="patrimonio")]}
        )
        result, count = downgrade_confianca_fallback(make_output(riscos=[risco]), E5_PARCIAL, WS)
        assert count == 1
        assert result.riscos[0].confianca == "media"

    def test_s7_theme_alone_without_lemma_untouched(self):
        risco = Risco(
            severidade="Alta",
            titulo="Cobertura de yield abaixo da meta de despesa essencial",
            descricao="A renda observada não cobre o custo de vida recorrente da família.",
            ancora_metodologica="convergencia",
            tema_canonico="Renda passiva",
            section_id="S7",
            ancoras=[Ancora(path="$.patrimonio.bruto", rotulo="patrimonio")],
            confianca="alta",
        )
        result, count = downgrade_confianca_fallback(make_output(riscos=[risco]), E5_PARCIAL, WS)
        assert count == 0
        assert result.riscos[0].confianca == "alta"


class TestNeedsReviewEspelhaEstado:
    def test_summary_mirrors_needs_review_when_passed(self):
        summary = guardrails_summary(confianca_rebaixada=0, audit=[], needs_review_triggered=True)
        assert summary["needs_review_triggered"] is True

    def test_evidencia_alta_mirrors_needs_review_triggered(self):
        raw = make_output(
            riscos=[
                _risco_mc("alta").model_copy(
                    update={
                        "ancoras": [
                            Ancora(path="$.reserva_emergencia.total_liquida", rotulo="patrimonio")
                        ]
                    }
                )
            ]
        )
        e5 = {**E5_PARCIAL, "reserva_emergencia": {"total_liquida": 84_000.0}}
        result = _generate(raw, e5)
        assert result.status == "needs_review"
        assert result.pos_llm_guardrails is not None
        assert result.pos_llm_guardrails["needs_review_triggered"] is True


def _e5_irpf(*, por_ano: dict[str, str]) -> dict:
    return {
        **E5_PARCIAL,
        "irpf_kpis": {
            **E5_PARCIAL["irpf_kpis"],
            "renda_tributavel_total_brl": 720_000.0,
            "ano_base_default": 2024,
            "ano_base_completude": "completo",
            "anos_completude_por_ano": por_ano,
        },
    }


def _pedido(motivo: str) -> list[CampoFaltante]:
    return [CampoFaltante(field_path="$.irpf_kpis.renda_tributavel_total_brl", motivo=motivo)]


class TestFieldRequestAno:
    def test_year_in_motivo_uncovered_is_kept_not_spurious(self):
        e5 = _e5_irpf(por_ano={"2024": "completo", "2025": "incompleto"})
        output = make_output(campos=_pedido("KPI de renda tributável para 2025 está indisponível"))
        result, audit = _filtra(output, e5)
        assert audit == []
        kept = result.campos_faltantes_pediria_se_iterasse
        assert [c.field_path for c in kept] == ["$.irpf_kpis.renda_tributavel_total_brl"]

    def test_year_in_motivo_when_year_completo_still_spurious(self):
        e5 = _e5_irpf(por_ano={"2024": "completo"})
        output = make_output(campos=_pedido("detalhar o KPI de renda tributável de 2024"))
        _, audit = _filtra(output, e5)
        assert [a["reason"] for a in audit] == [REASON_SPURIOUS]
