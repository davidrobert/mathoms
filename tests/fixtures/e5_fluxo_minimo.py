"""``fluxo_caixa`` mínimo que satisfaz os required do schema E5.

Vive fora dos testes porque três arquivos de validação de schema montam payload
E5 sintético e todos precisam do mesmo bloco. Duplicado, ele viraria a fixture
que inventa o payload: o schema ganha um required, um dos arquivos não atualiza,
e o teste passa a concordar com o bug em vez de acusá-lo.
"""

from __future__ import annotations

from typing import Any

# `data_corte` + `provisionado` são required desde o corte de provisionado
# (ADR-377 · A40.l41): o E5 sempre emite os dois, derivados do `reference_date`.
FLUXO_CAIXA_MINIMO: dict[str, Any] = {
    "janela": "full",
    "janela_meses": 0,
    "data_corte": "2026-01-31",
    "provisionado": {
        "data_corte": "2026-01-31",
        "receita_brl": 0.0,
        "despesa_brl": 0.0,
        "por_fonte": {},
        "por_categoria": {},
        "transacoes": 0,
        "primeiro_mes": None,
        "ultimo_mes": None,
    },
}

_CABECA_E5: dict[str, Any] = {
    "score": {"valor": 6.8, "classificacao": "Bom"},
    "patrimonio": {"bruto": 5000000, "liquido": 4000000},
}


def e5_com_top_ativos(*items: dict) -> dict:
    """Payload E5 sintético mínimo com ``investimentos.top_ativos``."""
    return {
        **_CABECA_E5,
        "fluxo_caixa": {**FLUXO_CAIXA_MINIMO, "receita_total": 80000},
        "investimentos": {
            "tabela_classes": [{"categoria": "Renda Fixa", "valor": 800000, "pct": 80.0}],
            "total": 1000000,
            "top_ativos": list(items),
        },
    }


def e5_com_instituicoes(por_membro: list, n_imoveis: int = 0) -> dict:
    """Payload E5 sintético mínimo com ``investimentos.instituicoes_por_membro``."""
    return {
        **_CABECA_E5,
        "fluxo_caixa": FLUXO_CAIXA_MINIMO,
        "investimentos": {
            "instituicoes_por_membro": por_membro,
            "n_imoveis_total": n_imoveis,
        },
    }
