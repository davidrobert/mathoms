"""FP-4 — piso de prescrição sob dívida de taxa desconhecida + auto-contradição.

D3-A: com `endividamento.dividas[].taxa_juros_aa` nulo as DUAS direções ficam
proibidas — prescrever aporte fabrica que a dívida é barata, prescrever quitação
fabrica que é cara. E o parecer passa a PEDIR a taxa: o distiller omite folha nula
(`tests/test_parecer_distiller_flatten.py`), então o LLM nunca soube que o campo
existe. O piso não olha o TIPO da dívida — `descricao` é fabricada pelo produtor
(`f"Financiamento imobiliário ({nome})"`), e piso sobre rótulo inventado é
prescrição sobre invenção.

D3-B: o mesmo `(section_id, tema_canonico)` não pode ser ponto forte E risco; a
liquidez excessiva é o caso nomeado (R2). D5 degrada com ressalva no piso de 3.

Fixtures sintéticas PII-zero.
"""

from __future__ import annotations

import pytest

from backend.app.services.parecer_guardrails_divida import (
    _SECAO_LIQUIDEZ,
    neutralize_autocontradicao,
    piso_prescricao_divida,
)
from backend.app.services.parecer_pos_llm_guardrails import PONTOS_FORTES_MIN
from pipeline.llm.schemas.parecer_planejador import (
    Metadata,
    ParecerPlanejadorOutput,
    PontoForte,
    Risco,
    Sugestao,
)

WS = "ws-divida-test"

E5_TAXA_NULA = {
    "endividamento": {
        "total_dividas": 500_000.0,
        "dividas": [
            {"descricao": "Financiamento", "saldo_devedor": 500_000.0, "taxa_juros_aa": None}
        ],
    },
    "reserva_emergencia": {"cobertura_meses": 12.0, "avaliacao_liquidity": "Adequada"},
}
E5_TAXA_CONHECIDA = {
    **E5_TAXA_NULA,
    "endividamento": {
        "total_dividas": 500_000.0,
        "dividas": [
            {"descricao": "Financiamento", "saldo_devedor": 500_000.0, "taxa_juros_aa": 11.5}
        ],
    },
}
E5_SEM_DIVIDA = {
    **E5_TAXA_NULA,
    "endividamento": {"total_dividas": 0.0, "dividas": []},
}
E5_LIQUIDEZ_EXCESSIVA = {
    **E5_TAXA_CONHECIDA,
    "reserva_emergencia": {"cobertura_meses": 30.0, "avaliacao_liquidity": "Excessiva"},
}

_TAXA_PATH_0 = "$.endividamento.dividas[0].taxa_juros_aa"


def _pf(tema: str = "Saúde de balanço", section: str = "S10", i: int = 0) -> PontoForte:
    return PontoForte(
        titulo=f"Ponto forte {i}",
        descricao="Descrição neutra do ponto forte, sem ticker e sem citar metodologia.",
        ancora_metodologica="convergencia",
        tema_canonico=tema,  # type: ignore[arg-type]
        section_id=section,  # type: ignore[arg-type]
    )


def _risco(tema: str = "Liquidez", section: str = _SECAO_LIQUIDEZ) -> Risco:
    return Risco(
        severidade="Média",
        titulo="Risco identificado na seção",
        descricao="Descrição factual do risco, sem ticker.",
        ancora_metodologica="convergencia",
        tema_canonico=tema,  # type: ignore[arg-type]
        section_id=section,  # type: ignore[arg-type]
        confianca="alta",
    )


def _sug(acao: str, tema: str = "Saúde de balanço", section: str = "S4") -> Sugestao:
    return Sugestao(
        prioridade="P1",
        acao=acao,
        impacto_qualitativo="Efeito descrito de forma qualitativa e neutra.",
        ancora_metodologica="convergencia",
        tema_canonico=tema,  # type: ignore[arg-type]
        confianca="media",
        section_id=section,  # type: ignore[arg-type]
        suggestion_dedup_key="0" * 64,
    )


def _metadata() -> Metadata:
    return Metadata(
        persona_hash="a" * 64,
        manifest_version="1.0.0",
        model_id="test-model",
        tier_at_generation="premium",
        generated_at="2026-08-19T12:00:00+00:00",
    )


def _output(*, pontos=None, riscos=None, execucao=None, taticas=None):
    return ParecerPlanejadorOutput(
        version="2.0",
        metadata=_metadata(),
        diagnostico_geral=(
            "Quadro patrimonial descrito de forma neutra, sem afirmação sobre evolução "
            "e sem citar metodologia de terceiros."
        ),
        pontos_fortes=pontos or [_pf(i=i) for i in range(4)],
        riscos=riscos or [],
        sugestoes_execucao=execucao or [],
        sugestoes_taticas=taticas or [],
        sugestoes_estrategicas=[],
        metricas=[],
        notas_metodologicas=[],
    )


# ─── D3-A: pedir a taxa ────────────────────────────────────────────────


class TestInjecaoDoPedidoDeTaxa:
    def test_taxa_nula_injeta_pedido(self):
        out, tel = piso_prescricao_divida(_output(), E5_TAXA_NULA, WS)
        paths = [c.field_path for c in out.campos_faltantes_pediria_se_iterasse or []]
        assert paths == [_TAXA_PATH_0]
        assert tel["taxa_divida_injetada_paths"] == [_TAXA_PATH_0]

    def test_taxa_conhecida_nao_injeta(self):
        out, tel = piso_prescricao_divida(_output(), E5_TAXA_CONHECIDA, WS)
        assert out.campos_faltantes_pediria_se_iterasse in (None, [])
        assert tel["taxa_divida_injetada_paths"] == []

    def test_sem_divida_nao_injeta(self):
        _, tel = piso_prescricao_divida(_output(), E5_SEM_DIVIDA, WS)
        assert tel["taxa_divida_injetada_paths"] == []

    def test_saldo_zero_nao_injeta(self):
        """Dívida liquidada não tem prescrição pendente — pedir a taxa é ruído."""
        e5 = {
            "endividamento": {
                "dividas": [{"descricao": "Quitada", "saldo_devedor": 0.0, "taxa_juros_aa": None}]
            }
        }
        _, tel = piso_prescricao_divida(_output(), e5, WS)
        assert tel["taxa_divida_injetada_paths"] == []

    def test_injecao_nao_duplica_pedido_do_llm(self):
        out0 = _output()
        out0 = out0.model_copy(
            update={
                "campos_faltantes_pediria_se_iterasse": [
                    __import__(
                        "pipeline.llm.schemas.parecer_planejador", fromlist=["CampoFaltante"]
                    ).CampoFaltante(field_path=_TAXA_PATH_0, motivo="LLM já pediu esta taxa.")
                ]
            }
        )
        out, tel = piso_prescricao_divida(out0, E5_TAXA_NULA, WS)
        paths = [c.field_path for c in out.campos_faltantes_pediria_se_iterasse or []]
        assert paths == [_TAXA_PATH_0]
        assert tel["taxa_divida_injetada_paths"] == []


# ─── D3-A: as duas direções de prescrição ──────────────────────────────


class TestPisoDeDuasDirecoes:
    def test_prescricao_de_quitacao_sai(self):
        sug = _sug("Amortizar o saldo devedor do financiamento com o excedente de caixa.")
        out, tel = piso_prescricao_divida(_output(taticas=[sug]), E5_TAXA_NULA, WS)
        assert out.sugestoes_taticas == []
        assert tel["prescricao_divida_removida"] == 1

    def test_prescricao_de_manter_a_divida_sai(self):
        sug = _sug("Manter o financiamento e direcionar o caixa para a carteira financeira.")
        out, tel = piso_prescricao_divida(_output(taticas=[sug]), E5_TAXA_NULA, WS)
        assert out.sugestoes_taticas == []
        assert tel["prescricao_divida_removida"] == 1

    def test_renegociar_sobrevive(self):
        """Renegociar é o movimento de DESCOBERTA da taxa — o único conselho que a
        taxa desconhecida não contradiz."""
        sug = _sug("Renegociar as condições do contrato junto à instituição credora.")
        out, tel = piso_prescricao_divida(_output(taticas=[sug]), E5_TAXA_NULA, WS)
        assert len(out.sugestoes_taticas) == 1
        assert tel["prescricao_divida_removida"] == 0

    def test_com_taxa_conhecida_a_prescricao_fica(self):
        """Polaridade: o piso é sobre DESCONHECIMENTO, não sobre a dívida existir."""
        sug = _sug("Amortizar o saldo devedor do financiamento com o excedente de caixa.")
        out, tel = piso_prescricao_divida(_output(taticas=[sug]), E5_TAXA_CONHECIDA, WS)
        assert len(out.sugestoes_taticas) == 1
        assert tel["prescricao_divida_removida"] == 0

    def test_sugestao_alheia_a_divida_fica(self):
        sug = _sug("Categorizar as despesas sem classificação do período analisado.")
        out, tel = piso_prescricao_divida(_output(taticas=[sug]), E5_TAXA_NULA, WS)
        assert len(out.sugestoes_taticas) == 1
        assert tel["prescricao_divida_removida"] == 0


# ─── D3-B: auto-contradição ────────────────────────────────────────────


class TestAutocontradicao:
    def test_r2_liquidez_excessiva_remove_ponto_forte_de_liquidez(self):
        """O sinal vem do E5 — contradição sobre o MESMO objeto medido."""
        pontos = [_pf(i=i) for i in range(4)] + [_pf("Liquidez", _SECAO_LIQUIDEZ, 9)]
        out, tel = neutralize_autocontradicao(_output(pontos=pontos), E5_LIQUIDEZ_EXCESSIVA, WS)
        assert len(out.pontos_fortes) == 4
        assert all(p.tema_canonico != "Liquidez" for p in out.pontos_fortes)
        assert tel["autocontradicao_removidos"] == 1

    def test_liquidez_adequada_nao_dispara(self):
        pontos = [_pf(i=i) for i in range(4)] + [_pf("Liquidez", _SECAO_LIQUIDEZ, 9)]
        out, tel = neutralize_autocontradicao(_output(pontos=pontos), E5_TAXA_CONHECIDA, WS)
        assert len(out.pontos_fortes) == 5
        assert tel["autocontradicao_removidos"] == 0

    def test_par_secao_tema_e_so_contado_nao_removido(self):
        """R1 refutada por medição no r7: o par (seção, tema) é BALDE, não assunto —
        casava 2/5 pontos fortes com 1 falso-positivo (S2 + "Equilíbrio presente-futuro"
        aproxima poupança alta de gasto com saúde alto). Vira contagem para o r8."""
        pontos = [_pf(i=i) for i in range(4)] + [_pf("Liquidez", _SECAO_LIQUIDEZ, 9)]
        out, tel = neutralize_autocontradicao(
            _output(pontos=pontos, riscos=[_risco()]), E5_TAXA_CONHECIDA, WS
        )
        assert len(out.pontos_fortes) == 5
        assert tel["autocontradicao_removidos"] == 0
        assert tel["autocontradicao_pares_secao_tema"] == 1

    def test_par_e_contado_mesmo_quando_r2_ja_removeu(self):
        pontos = [_pf(i=i) for i in range(4)] + [_pf("Liquidez", _SECAO_LIQUIDEZ, 9)]
        _, tel = neutralize_autocontradicao(
            _output(pontos=pontos, riscos=[_risco()]), E5_LIQUIDEZ_EXCESSIVA, WS
        )
        assert tel["autocontradicao_removidos"] == 1
        assert tel["autocontradicao_pares_secao_tema"] == 1

    def test_piso_degrada_com_ressalva(self):
        pontos = [_pf(i=0), _pf(i=1), _pf("Liquidez", _SECAO_LIQUIDEZ, 2)]
        out, tel = neutralize_autocontradicao(_output(pontos=pontos), E5_LIQUIDEZ_EXCESSIVA, WS)
        assert len(out.pontos_fortes) == PONTOS_FORTES_MIN
        assert tel["autocontradicao_removidos"] == 0
        assert tel["autocontradicao_ressalvados"] == 1
        assert "também consta como risco" in out.pontos_fortes[2].descricao
        assert out.pontos_fortes[2].section_id == _SECAO_LIQUIDEZ

    def test_saida_revalida_no_schema(self):
        pontos = [_pf(i=0), _pf(i=1), _pf("Liquidez", _SECAO_LIQUIDEZ, 2)]
        out, _ = neutralize_autocontradicao(_output(pontos=pontos), E5_LIQUIDEZ_EXCESSIVA, WS)
        ParecerPlanejadorOutput.model_validate(out.model_dump())


# ─── Nunca bloqueia ────────────────────────────────────────────────────


def test_piso_prescricao_nunca_marca_needs_review():
    _, tel = piso_prescricao_divida(_output(), E5_TAXA_NULA, WS)
    assert "needs_review_triggered" not in tel


def test_autocontradicao_nunca_marca_needs_review():
    _, tel = neutralize_autocontradicao(_output(), E5_TAXA_NULA, WS)
    assert "needs_review_triggered" not in tel


# ─── Call-site + atribuição na telemetria ──────────────────────────────


class TestCallSiteOrchestrator:
    def _resultado(self):
        from tests.test_parecer_guardrails_pos_llm import _generate

        pontos = [_pf(i=i) for i in range(4)] + [_pf("Liquidez", _SECAO_LIQUIDEZ, 9)]
        sug = _sug("Amortizar o saldo devedor do financiamento com o excedente de caixa.")
        e5 = {**E5_TAXA_NULA, "reserva_emergencia": {"avaliacao_liquidity": "Excessiva"}}
        return _generate(_output(pontos=pontos, riscos=[_risco()], taticas=[sug]), e5)

    def test_orchestrator_aplica_as_duas_regras(self):
        result = self._resultado()
        assert result.status == "Gerado"  # coerce, nunca needs_review
        tel = result.pos_llm_guardrails
        assert tel["prescricao_divida_removida"] == 1
        assert tel["taxa_divida_injetada_paths"] == [_TAXA_PATH_0]
        assert tel["autocontradicao_removidos"] == 1
        assert len(result.output.pontos_fortes) == 4
        assert result.output.sugestoes_taticas == []

    def test_pedido_injetado_sobrevive_ao_filtro_3_vias(self):
        """Injeção acontece ANTES do filtro; path nulo no E5 é sinal verdadeiro."""
        kept = self._resultado().output.campos_faltantes_pediria_se_iterasse or []
        assert [c.field_path for c in kept] == [_TAXA_PATH_0]

    def test_persistencia_nao_atribui_ao_llm_o_que_o_guardrail_pediu(self):
        from backend.app.models.planner_field_request import VALID_FIELD_REQUEST_REASONS
        from backend.app.services.planner_review_persistence import _iter_field_requests

        result = self._resultado()
        content = result.output.model_dump()
        content["_meta"] = {"pos_llm_guardrails": result.pos_llm_guardrails}
        rows = list(_iter_field_requests(content))
        assert [(r["field_path"], r["reason"]) for r in rows] == [
            (_TAXA_PATH_0, "guardrail_injected")
        ]
        assert "guardrail_injected" in VALID_FIELD_REQUEST_REASONS

    def test_telemetria_valida_contra_o_json_schema(self):
        import json
        from pathlib import Path

        import jsonschema

        result = self._resultado()
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root / "config/schemas/parecer_planejador.schema.json").read_text())
        jsonschema.validate(
            result.pos_llm_guardrails,
            schema["properties"]["_meta"]["properties"]["pos_llm_guardrails"],
        )


# ---------------------------------------------------------------------------
# A40.l80 — guardrail não arma em seção que o modelo nunca vê
# ---------------------------------------------------------------------------


# `_SECAO_LIQUIDEZ` valeu `"S4"` desde que o guardrail nasceu. O manifest projeta seções
# alinhadas a S1/S2/S3/S7/S8/S9/S10 — **S4 nunca** —, e a reserva vive em `saude_balanco`
# (`aligned_with_layout: "S1"`). Resultado medido: com o sinal do E5 VIVO no golden
# (`avaliacao_liquidity == "Excessiva"`), o guardrail não disparava. A [[ADR-412]] §Emenda
# E3 apoia-se nele para NÃO suprimir `avaliacao_liquidity`.
#
# Este teste é o que separa o conserto da tautologia: os testes acima importam a constante,
# logo passariam com qualquer valor — inclusive `"S4"` de volta.
def test_guardrail_arma_em_secao_que_o_manifest_projeta():
    """Seção que o manifest não projeta é seção que o modelo não rotula — regra morta."""
    from backend.app.services.parecer_manifest import load_manifest

    projetadas = {
        s.get("aligned_with_layout")
        for s in load_manifest().sections
        if s.get("aligned_with_layout")
    }

    assert projetadas, "manifest sem seções alinhadas — o teste ficaria vacuoso"
    assert _SECAO_LIQUIDEZ in projetadas, (
        f"o guardrail arma em `{_SECAO_LIQUIDEZ}`, que o manifest não projeta — "
        f"o modelo nunca rotula assim e a regra nasce morta. Projetadas: {sorted(projetadas)}"
    )
