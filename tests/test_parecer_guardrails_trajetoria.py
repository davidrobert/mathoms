"""FP-2 D1-B — parecer não afirma trajetória sem série que a sustente.

No r7 o parecer narrou aceleração patrimonial a partir de NÍVEL: o manifest do
parecer entrega médias de janela (`fluxo_caixa.janela_12m.*`), nunca série
temporal, e nunca o changelog. `PontoForte` sequer tem campo `ancoras` — logo
uma afirmação de evolução ali é inverificável por construção.

Coerce, nunca `raise`/`needs_review` (ADR-292/294 — reask storm).
Fixtures sintéticas PII-zero.
"""

from __future__ import annotations

from backend.app.services.parecer_pos_llm_guardrails import (
    PONTOS_FORTES_MIN,
    neutralize_trajetoria_sem_serie,
)
from pipeline.llm.schemas.parecer_planejador import (
    Metadata,
    ParecerPlanejadorOutput,
    PontoForte,
)

WS = "ws-trajetoria-test"

_NIVEL = "Cobertura líquida acima da meta calibrada para o perfil declarado."
_TRAJETORIA = "A taxa de poupança melhorou frente ao período anterior."
_CONDICIONAL = "Realocar o excedente pode acelerar o alcance da meta declarada."
_DIAG_NIVEL = (
    "Na foto atual a família apresenta estrutura patrimonial consolidada, com "
    "endividamento abaixo do teto prudencial adotado no relatório."
)
_DIAG_TRAJETORIA = (
    "O patrimônio líquido está em construção acelerada, com projeção de "
    "independência financeira no cenário central sob as premissas vigentes."
)


def _pf(descricao: str, i: int = 0) -> PontoForte:
    return PontoForte(
        titulo=f"Ponto forte {i}",
        descricao=descricao,
        ancora_metodologica="convergencia",
        tema_canonico="Saúde de balanço",
        section_id="S10",
    )


def _output(pontos: list[PontoForte], diagnostico: str = _DIAG_NIVEL):
    return ParecerPlanejadorOutput(
        version="2.0",
        metadata=Metadata(
            persona_hash="a" * 64,
            manifest_version="1.0.0",
            model_id="test-model",
            tier_at_generation="premium",
            generated_at="2026-08-19T12:00:00+00:00",
        ),
        diagnostico_geral=diagnostico,
        pontos_fortes=pontos,
        riscos=[],
        sugestoes_execucao=[],
        sugestoes_taticas=[],
        sugestoes_estrategicas=[],
        metricas=[],
        notas_metodologicas=[],
    )


def _quatro_niveis() -> list[PontoForte]:
    return [_pf(_NIVEL, i) for i in range(4)]


class TestPontosFortes:
    def test_remove_ponto_forte_que_afirma_trajetoria(self):
        pontos = _quatro_niveis() + [_pf(_TRAJETORIA, 9)]
        out, tel = neutralize_trajetoria_sem_serie(_output(pontos), WS)
        assert len(out.pontos_fortes) == 4
        assert all(_TRAJETORIA not in p.descricao for p in out.pontos_fortes)
        assert tel["trajetoria_pontos_fortes_removidos"] == 1

    def test_nivel_puro_nao_dispara(self):
        """Polaridade: descrever nível não é afirmar evolução."""
        out, tel = neutralize_trajetoria_sem_serie(_output(_quatro_niveis()), WS)
        assert len(out.pontos_fortes) == 4
        assert tel["trajetoria_pontos_fortes_removidos"] == 0

    def test_projecao_condicional_nao_dispara(self):
        """ "pode acelerar" projeta adiante — não afirma o passado (medido no r7)."""
        pontos = _quatro_niveis() + [_pf(_CONDICIONAL, 9)]
        out, tel = neutralize_trajetoria_sem_serie(_output(pontos), WS)
        assert len(out.pontos_fortes) == 5
        assert tel["trajetoria_pontos_fortes_removidos"] == 0


class TestPisoD5:
    def test_no_piso_degrada_com_ressalva_em_vez_de_remover(self):
        """D5: remover levaria a lista abaixo do piso ⇒ mantém e ressalva."""
        pontos = [_pf(_NIVEL, 0), _pf(_NIVEL, 1), _pf(_TRAJETORIA, 2)]
        out, tel = neutralize_trajetoria_sem_serie(_output(pontos), WS)
        assert len(out.pontos_fortes) == PONTOS_FORTES_MIN
        assert tel["trajetoria_pontos_fortes_removidos"] == 0
        assert tel["trajetoria_pontos_fortes_ressalvados"] == 1
        ressalvado = out.pontos_fortes[2]
        assert "série histórica" in ressalvado.descricao
        assert ressalvado.tema_canonico == "Saúde de balanço"
        assert ressalvado.section_id == "S10"

    def test_ressalva_respeita_o_cap_de_descricao(self):
        """model_copy não re-valida: o cap de 520 é responsabilidade daqui."""
        pontos = [_pf(_NIVEL, 0), _pf(_NIVEL, 1), _pf("x " * 250 + _TRAJETORIA, 2)]
        out, _ = neutralize_trajetoria_sem_serie(_output(pontos), WS)
        assert len(out.pontos_fortes[2].descricao) <= 520

    def test_saida_revalida_no_schema(self):
        """O hook de JSON Schema é warn local e strict no CI — revalide aqui."""
        pontos = [_pf(_NIVEL, 0), _pf(_NIVEL, 1), _pf(_TRAJETORIA, 2)]
        out, _ = neutralize_trajetoria_sem_serie(_output(pontos), WS)
        ParecerPlanejadorOutput.model_validate(out.model_dump())


class TestDiagnosticoGeral:
    def test_diagnostico_e_registrado_nao_removido(self):
        """Campo único: não há o que remover — o desfecho é medição para o r8."""
        out, tel = neutralize_trajetoria_sem_serie(_output(_quatro_niveis(), _DIAG_TRAJETORIA), WS)
        assert out.diagnostico_geral == _DIAG_TRAJETORIA
        assert tel["trajetoria_diagnostico_lemmas"] == ["acelera"]

    def test_diagnostico_de_nivel_nao_registra(self):
        _, tel = neutralize_trajetoria_sem_serie(_output(_quatro_niveis()), WS)
        assert tel["trajetoria_diagnostico_lemmas"] == []


class TestNuncaBloqueia:
    def test_guardrail_nunca_marca_needs_review(self):
        pontos = _quatro_niveis() + [_pf(_TRAJETORIA, 9)]
        out, tel = neutralize_trajetoria_sem_serie(_output(pontos, _DIAG_TRAJETORIA), WS)
        assert "needs_review_triggered" not in tel
        assert out.pontos_fortes  # nunca esvazia


# ─── Call-site: o orchestrator aplica a regra (função não chamada é inerte) ───


class TestCallSiteOrchestrator:
    def test_orchestrator_aplica_e_publica_telemetria(self):
        from tests.test_parecer_guardrails_pos_llm import E5_COMPLETO, _generate

        pontos = _quatro_niveis() + [_pf(_TRAJETORIA, 9)]
        result = _generate(_output(pontos, _DIAG_TRAJETORIA), E5_COMPLETO)

        assert result.status == "Gerado"  # coerce, nunca needs_review
        assert len(result.output.pontos_fortes) == 4
        tel = result.pos_llm_guardrails
        assert tel["trajetoria_pontos_fortes_removidos"] == 1
        assert tel["trajetoria_diagnostico_lemmas"] == ["acelera"]
        assert tel["needs_review_triggered"] is False

    def test_telemetria_valida_contra_o_json_schema(self):
        """`_meta.pos_llm_guardrails` tem additionalProperties:false — chave nova
        que não esteja no schema quebra em strict (CI), não aqui."""
        import json
        from pathlib import Path

        import jsonschema

        from tests.test_parecer_guardrails_pos_llm import E5_COMPLETO, _generate

        pontos = _quatro_niveis() + [_pf(_TRAJETORIA, 9)]
        result = _generate(_output(pontos, _DIAG_TRAJETORIA), E5_COMPLETO)
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root / "config/schemas/parecer_planejador.schema.json").read_text())
        jsonschema.validate(
            result.pos_llm_guardrails,
            schema["properties"]["_meta"]["properties"]["pos_llm_guardrails"],
        )
