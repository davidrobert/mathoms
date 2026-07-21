"""PE-01 (R3.3): blocos key_value achatam dict folha-a-folha — zeros estruturais
no fim não são mais cortados pelo _short(300) do dump raw."""

from __future__ import annotations

import json

from backend.app.services.parecer_distiller import render_block

_RESERVA = {
    "reserva_emergencia": {
        "total_liquida": 150000.0,
        "cobertura_meses": 8.5,
        "avaliacao_liquidity": "Adequada",
        "meses_alvo": 12,
        "alvo_brl": 180000.0,
        "gap_brl": 30000.0,
        "perfil_renda": "pj_dominante",
        "nivel_6_meses": 90000.0,
        "nivel_12_meses": 180000.0,
        "composicao_liquida": {"investimentos_titular": 100000.0, "caixa_moeda_estrangeira": 0.0},
        "excluido_da_reserva": {"investimentos_nao_liquidos": 0.0, "caixa_nao_classificado": 0.0},
    }
}
_BLOCK = {
    "format": "key_value",
    "title": "Reserva",
    "fields": [{"path": "$.reserva_emergencia", "label": "reserva", "format": "raw"}],
}


def test_key_value_flattens_nested_dict_no_truncation():
    # Precondição: o dump raw estouraria os 300 chars do _short e cortaria a cauda.
    assert len(json.dumps(_RESERVA["reserva_emergencia"])) > 300
    out = render_block(_BLOCK, _RESERVA)
    # Cabeça (citada pelo hint :186) e cauda (zeros estruturais) ambas presentes.
    assert "total_liquida: 150000.0" in out
    assert "excluido_da_reserva.caixa_nao_classificado: 0.0" in out
    assert "composicao_liquida.caixa_moeda_estrangeira: 0.0" in out


def test_key_value_secao_ausente_omite_bloco():
    # Seção ausente (workspace sem IRPF, ADR-157) → bloco omitido, sem header órfão.
    block = {
        "format": "key_value",
        "title": "KPIs IRPF",
        "fields": [{"path": "$.irpf_kpis", "label": "irpf_kpis", "format": "raw"}],
    }
    assert render_block(block, {}) == ""


def test_key_value_scalar_field_unchanged():
    e5 = {"score": {"valor": 6.5}}
    block = {
        "format": "key_value",
        "title": "Score",
        "fields": [{"path": "$.score.valor", "label": "valor", "format": "raw"}],
    }
    assert render_block(block, e5) == "**Score**:\n  - valor: 6.5"


# A37.l4: dívida com parcela/taxa desconhecidas emitidas como null pelo produtor.
_ENDIVIDAMENTO_COM_NULLS = {
    "endividamento": {
        "total_dividas": 500000.0,
        "dividas": [
            {
                "descricao": "Financiamento imobiliário",
                "saldo_devedor": 500000.0,
                "parcela_mensal": None,
                "taxa_juros": None,
            }
        ],
    }
}
_ENDIVIDAMENTO_BLOCK = {
    "format": "key_value",
    "title": "Endividamento",
    "fields": [{"path": "$.endividamento", "label": "endividamento", "format": "raw"}],
}


def test_key_value_flatten_skips_null_leaves():
    """A37.l4: null é ausência — folha None não vira linha "None" no exec context
    (paridade com on_null:skip dos blocos escalares)."""
    out = render_block(_ENDIVIDAMENTO_BLOCK, _ENDIVIDAMENTO_COM_NULLS)
    assert "total_dividas: 500000.0" in out
    assert "taxa_juros" not in out
    assert "parcela_mensal" not in out
    assert "None" not in out


def test_key_value_all_null_leaves_omits_block():
    e5 = {"endividamento": {"total_dividas": None}}
    assert render_block(_ENDIVIDAMENTO_BLOCK, e5) == ""
