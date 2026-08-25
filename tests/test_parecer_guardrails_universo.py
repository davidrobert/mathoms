"""O universo que o predicado consulta, e o que conta como ausência (A40.l83 · RV8-16).

Módulo próprio porque ``tests/test_parecer_guardrails_pos_llm.py`` está no limite de 500
linhas do CLAUDE.md §Code style — mesmo precedente de
``tests/test_parecer_evidencia_inventario.py``.
"""

from __future__ import annotations

from backend.app.services.parecer_pos_llm_guardrails import (
    REASON_OUT_OF_CATALOG,
    REASON_SPURIOUS,
    guardrails_summary,
)
from pipeline.llm.schemas.parecer_planejador import CampoFaltante
from tests.test_parecer_guardrails_pos_llm import E5_PARCIAL, _filtra, make_output


class TestUniversoDoPredicado:
    """A40.l83 · RV8-16 — o modelo se pronuncia sobre o CATÁLOGO; o filtro perguntava ao
    E5. Taxa de falso-positivo medida no run r8: 2 de 2, ambos removidos do usuário."""

    def _campo(self, path: str):
        return make_output(campos=[CampoFaltante(field_path=path, motivo="fundamentar o valor")])

    def test_path_no_e5_mas_fora_do_catalogo_nao_e_espurio(self):
        """O pedido é legítimo: o modelo não tinha rota de citação. E o contador vira
        sinal de TRUNCAMENTO, não de alucinação."""
        output = self._campo("$.patrimonio.bruto")
        _result, audit = _filtra(output, E5_PARCIAL, catalogo=frozenset())
        assert [a["reason"] for a in audit] == [REASON_OUT_OF_CATALOG]
        assert (
            guardrails_summary(confianca_rebaixada=0, audit=audit)["field_requests_spurious"] == 0
        )

    def test_fora_do_catalogo_permanece_no_output_do_usuario(self):
        """Removê-lo apagava a única pista de que o contexto foi truncado."""
        output = self._campo("$.patrimonio.bruto")
        result, _audit = _filtra(output, E5_PARCIAL, catalogo=frozenset())
        kept = [c.field_path for c in result.campos_faltantes_pediria_se_iterasse]
        assert kept == ["$.patrimonio.bruto"]

    def test_citavel_e_presente_segue_espurio(self):
        """Polaridade não afrouxou: com rota de citação disponível, pedir é espúrio."""
        output = self._campo("$.patrimonio.bruto")
        _result, audit = _filtra(output, E5_PARCIAL, catalogo=frozenset({"$.patrimonio.bruto"}))
        assert [a["reason"] for a in audit] == [REASON_SPURIOUS]


class TestPlaceholderDeDominioEhAusencia:
    """A40.l83 · RV8-16 — o discriminador é a POSIÇÃO: sentinela ocupa o lugar do dado;
    valor categórico É o dado."""

    def test_faixa_etaria_desconhecida_e_ausencia(self):
        e5 = {**E5_PARCIAL, "composicao_familiar": {"membros": [{"faixa_etaria": "desconhecida"}]}}
        path = "$.composicao_familiar.membros[0].faixa_etaria"
        _result, audit = _filtra(
            make_output(campos=[CampoFaltante(field_path=path, motivo="faixa do membro")]), e5
        )
        assert audit == []

    def test_categoria_nao_identificado_e_dado_e_segue_espuria(self):
        """Deixado FORA das sentinelas de propósito: "não identificado" é um balde real de
        despesa. Marcá-lo como ausência faria o erro simétrico."""
        e5 = {**E5_PARCIAL, "consumo": {"linhas": [{"categoria": "nao_identificado"}]}}
        path = "$.consumo.linhas[0].categoria"
        _result, audit = _filtra(
            make_output(campos=[CampoFaltante(field_path=path, motivo="qual categoria")]), e5
        )
        assert [a["reason"] for a in audit] == [REASON_SPURIOUS]
