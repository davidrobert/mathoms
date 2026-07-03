"""Round-trip por tipo do valor_renderizado das âncoras (A28.l10 · ADR-296).

Dogfood 72883bde: o finalize aplicava BRL a toda folha citada —
``prob_if_ate_idade_meta=0.31`` virava "R$ 0,31" e ``idade_meta_usada=53``
virava "R$ 53,00". O dispatch agora vem de ``ancora_format_hint`` (catálogo
de citação — a folha conhece seu campo), nunca de heurística sobre o valor.
Determinístico, sem LLM: opera sobre o output pós-geração.
"""

from __future__ import annotations

from backend.app.services.parecer_finalization import (
    empty_needs_review_output,
    stamp_ancora_values,
)
from pipeline.llm.schemas.parecer_planejador import Ancora, Risco
from pipeline.llm.tools.planner_drill_down import PlannerDrillDown

_E5 = {
    "if_monte_carlo": {"prob_if_ate_idade_meta": 0.31, "idade_meta_usada": 53},
    "reserva_emergencia": {"total_liquida": 84_000.0, "cobertura_meses": 4.2},
}
_WHITELIST = frozenset({"if_monte_carlo", "reserva_emergencia"})

_PROB = "$.if_monte_carlo.prob_if_ate_idade_meta"
_IDADE = "$.if_monte_carlo.idade_meta_usada"
_MOEDA = "$.reserva_emergencia.total_liquida"
_MESES = "$.reserva_emergencia.cobertura_meses"


def _risco(paths: list[str]) -> Risco:
    return Risco(
        severidade="Alta",
        titulo="Risco sintético para round-trip de âncoras",
        descricao="Prosa sem número autorado, conforme contrato ADR-296.",
        ancora_metodologica="convergencia",
        tema_canonico="Liquidez",
        section_id="S1",
        confianca="alta",
        ancoras=[Ancora(path=p, rotulo=p[2:].split(".", 1)[0]) for p in paths],
    )


def _stamped_values(paths: list[str]) -> dict[str, str | None]:
    base = empty_needs_review_output(
        persona_hash="0" * 64, manifest_version="1.0.0", model_id="m", tier="premium"
    )
    output = base.model_copy(update={"riscos": [_risco(paths)]})
    drill = PlannerDrillDown(e5_data=_E5, section_whitelist=_WHITELIST, format_hints={})
    stamped = stamp_ancora_values(output, drill)
    return {a.path: a.valor_renderizado for a in stamped.riscos[0].ancoras}


class TestRoundTripPorTipo:
    def test_probabilidade_renderiza_percentual(self):
        assert _stamped_values([_PROB])[_PROB] == "31%"

    def test_idade_renderiza_anos(self):
        assert _stamped_values([_IDADE])[_IDADE] == "53 anos"

    def test_moeda_renderiza_brl(self):
        assert _stamped_values([_MOEDA])[_MOEDA] == "R$ 84.000,00"

    def test_cobertura_renderiza_meses(self):
        assert _stamped_values([_MESES])[_MESES] == "4 meses"

    def test_zero_campo_nao_monetario_com_prefixo_brl(self):
        """Critério de aceite A28.l10: nenhum campo não-monetário ganha "R$"."""
        values = _stamped_values([_PROB, _IDADE, _MESES])
        for path, rendered in values.items():
            assert rendered is not None, path
            assert not rendered.startswith("R$"), f"{path} renderizou monetário: {rendered!r}"

    def test_path_nao_resolvido_permanece_sem_valor(self):
        path = "$.reserva_emergencia.campo_inexistente"
        assert _stamped_values([path])[path] is None
