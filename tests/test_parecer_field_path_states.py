"""Predicado de 3 estados de field_path do guardrail pós-LLM (PE-3 · r7).

Separado de ``test_parecer_guardrails_pos_llm`` porque mede a UNIDADE (o
predicado), não a decisão do filtro. Fixtures sintéticas PII-zero.
"""

from __future__ import annotations

from typing import Any

from backend.app.services.parecer_pos_llm_guardrails import classify_field_path

E5_PARCIAL: dict[str, Any] = {
    "premissas_economicas": {"status": "parcial"},
    "irpf_kpis": {"dependentes": {"count": 2, "por_relacao": {"filho": 2}}},
    "patrimonio": {"bruto": 1_000_000},
}


class TestClassifyFieldPath3Estados:
    """O predicado em si — ``missing`` (nenhum ramo existe) vs ``empty`` (existe e
    não rende dado) vs ``present``. Só ``present`` autoriza remover o pedido."""

    def test_missing_quando_nenhum_ramo_existe(self):
        assert classify_field_path(E5_PARCIAL, "$.composicao_familiar.membros") == "missing"

    def test_missing_quando_folha_nao_existe_sob_chave_existente(self):
        assert classify_field_path(E5_PARCIAL, "$.patrimonio.liquido") == "missing"

    def test_empty_para_colecao_vazia(self):
        e5 = {"protecao_patrimonial": {"bens_com_gap_cobertura": []}}
        assert classify_field_path(e5, "$.protecao_patrimonial.bens_com_gap_cobertura") == "empty"
        assert (
            classify_field_path(e5, "$.protecao_patrimonial.bens_com_gap_cobertura[*]") == "empty"
        )

    def test_empty_para_null_e_sentinela(self):
        e5 = {"ratios": {"rentabilidade_pct": "N/D", "janela_referencia": "", "juros": None}}
        assert classify_field_path(e5, "$.ratios.rentabilidade_pct") == "empty"
        assert classify_field_path(e5, "$.ratios.janela_referencia") == "empty"
        assert classify_field_path(e5, "$.ratios.juros") == "empty"

    def test_present_inclui_zero_e_false(self):
        """Zero é dado — o count=0 do IRPF é justamente o lado fiscal do PE-3."""
        e5 = {"irpf_kpis": {"dependentes": {"count": 0}}, "flags": {"ativo": False}}
        assert classify_field_path(e5, "$.irpf_kpis.dependentes.count") == "present"
        assert classify_field_path(e5, "$.flags.ativo") == "present"

    def test_path_fora_do_subset_e_missing(self):
        assert classify_field_path(E5_PARCIAL, "patrimonio.bruto") == "missing"
