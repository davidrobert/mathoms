"""Os dois lados da família chegam JUNTOS ao exec context (PE-3 · r7).

No r7 o parecer emitiu `riscos[0]` (S9, Crítica, confiança alta, ancorado em
dependentes menores) e `riscos[11]` (S_IRPF_OTIMIZACAO, Baixa, confiança baixa,
"dependendo da composição familiar real") — dois fatos verdadeiros da mesma
família, Δ de confiança 2, zero reconciliação. O manifest projetava só o lado
fiscal. Este gate mede o que o modelo VÊ, não o que ele responde: com o lado
civil e o fiscal no mesmo corpo orçado, a reconciliação passa a ser possível.

Co-locados de propósito na mesma seção (`previdencia_irpf`): assim os dois
evictam juntos (ADR-341 D2) e nunca sobra um sem o outro — que é exatamente o
estado que produz o hedge. Fixtures sintéticas PII-zero.
"""

from __future__ import annotations

from typing import Any

from backend.app.services.parecer_distiller import distill_exec_context
from backend.app.services.parecer_manifest import load_manifest

_MARKER_PREFIX = "[exec context truncado em max_exec_context_bytes"
_HINTS_HEADER = "### Diretrizes de leitura por seção (hints)"
_SECTION_ID = "previdencia_irpf"

# Assinatura do PE-3: filho menor no cadastro civil × zero dependentes no IRPF.
# Os dois fatos são verdadeiros e vivem em domínios distintos.
_E5_FILHO_MENOR_SEM_DEPENDENTE: dict[str, Any] = {
    "score": {"total": 70},
    "patrimonio": {"bruto": 1_000_000},
    "fluxo_caixa": {"janela_12m": {"receita_recorrente_mensal": 30_000}},
    "irpf_kpis": {"ano_base": 2024, "dependentes": {"count": 0, "por_relacao": {}}},
    "composicao_familiar": {
        "faixa_ref": "2024-12-31",
        "fonte": "cadastro_familia",
        "membros": [
            {"papel": "titular", "faixa_etaria": "25-59"},
            {"papel": "filho", "faixa_etaria": "0-17"},
        ],
    },
}


def _exec_context(e5: dict[str, Any]) -> str:
    return distill_exec_context(load_manifest(), e5)


def _body(e5: dict[str, Any]) -> str:
    """Só o corpo orçado. Hints são anexados APÓS o cap (ADR-341 D4) e citam
    ``$.composicao_familiar`` por definição — medir o corpo pelo texto inteiro
    daria verde por causa da guidance, não do dado."""
    return _exec_context(e5).split(_HINTS_HEADER, 1)[0]


class TestComposicaoFamiliarNoExecContext:
    def test_lado_civil_e_lado_fiscal_coexistem_no_corpo(self):
        """G1: a faixa do menor E o count fiscal zero, no mesmo exec context."""
        body = _body(_E5_FILHO_MENOR_SEM_DEPENDENTE)
        assert "0-17" in body
        assert "count: 0" in body or '"count": 0' in body

    def test_corpo_nao_sofre_truncagem_com_o_bloco_novo(self):
        """O bloco cabe na folga do budget — se estourar, encurta-se o label; o
        que não se faz é subir max_exec_context_bytes e inflar todo run."""
        assert _MARKER_PREFIX not in _exec_context(_E5_FILHO_MENOR_SEM_DEPENDENTE)

    def test_faixa_ref_viaja_junto_para_o_modelo(self):
        """Sem a data de corte o modelo não sabe contra qual relógio a banda foi
        cortada — e a de hoje produziria falso positivo em quem fez 22 no ano."""
        assert "2024-12-31" in _body(_E5_FILHO_MENOR_SEM_DEPENDENTE)

    def test_workspace_sem_bloco_civil_nao_ganha_placeholder(self):
        """``on_null: skip``: ausência do cadastro não vira linha prometendo dado."""
        e5 = {k: v for k, v in _E5_FILHO_MENOR_SEM_DEPENDENTE.items()}
        e5.pop("composicao_familiar")
        body = _body(e5)
        assert "composicao_familiar" not in body
        assert "0-17" not in body


class TestCoLocacaoDosDoisLados:
    def test_os_dois_paths_vivem_na_mesma_secao_do_manifest(self):
        """Co-locados ⇒ evictam juntos. Separados, a eviction pode deixar o lado
        fiscal sozinho — o estado exato que produziu o hedge no r7."""
        section = next(s for s in load_manifest().sections if s.get("id") == _SECTION_ID)
        paths = {b.get("path") for b in section.get("blocks", [])}
        assert "$.composicao_familiar" in paths
        assert "$.irpf_kpis.dependentes" in paths

    def test_hint_nao_afirma_mais_que_o_bloco_nao_existe(self):
        """A linha 'não existe $.composicao_familiar no E5' virou falsa pós-(a)."""
        section = next(s for s in load_manifest().sections if s.get("id") == _SECTION_ID)
        hints = " ".join(section.get("narrative_hints", []))
        assert "não existe $.composicao_familiar" not in hints
        assert "$.composicao_familiar" in hints
