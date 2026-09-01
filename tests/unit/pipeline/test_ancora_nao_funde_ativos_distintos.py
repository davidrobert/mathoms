"""Regressão P0 — a âncora sozinha identifica a CONTRAPARTE, não o ativo ([[A42.l15]])."""

# `("cnpj", raiz)` como perna forte fundia ativos distintos da mesma instituição, e o merge
# cross-year resolve conflito de mesmo-ano por `max()` — logo o menor valor SOME. Medido em
# `origin/main` (`5903fcc2`) antes deste fix:
#
#     conta corrente R$ 3.000 + poupança R$ 5.000, mesmo banco  ->  1 entrada, R$ 5.000
#     CDB R$ 50.000 + FII R$ 50.000, mesma corretora            ->  1 entrada, R$ 50.000
#
# O único sinal era `outcome.warnings`, que `consolidate_baseline` converte num `print` de
# contagem: não vira `review_reason`, não entra no artefato, `_dedup_warning` fica `None`.
#
# É a classe que a [[ADR-271]] §Calibração nomeia como a pior — "fundir ativos distintos some
# patrimônio real (silencioso); na dúvida, não funde" —, e é a MESMA que esta lane já tinha
# evitado ao manter `instituicao` na perna fraca. A âncora reintroduziu por outro caminho:
# CNPJ raiz identifica quem emite, não o que foi emitido.
#
# Custo medido do conserto, 836 artefatos / 28 grupos (pooled |A∩B|/|A∪B|):
#   (tipo,inst,desc) pré-lane        37,68%  card 9,7  funde 0/3
#   ("cnpj",raiz) — a que regrediu   61,78%  card 9,4  funde 3/3
#   ("cnpj",raiz,tipo)               56,64%  card 9,7  funde 1/3
#   ("cnpj",raiz,tipo,desc) — esta   42,38%  card 9,7  funde 0/3
#
# Estabilidade não é o eixo que decide: a §Calibração decide.

from __future__ import annotations

import pytest

from pipeline.domain.services.investimentos_dedup import dedup_investimentos_consolidados

_CNPJ_TXT = "CNPJ 12.345.678/0001-95"


def _entrada(descricao: str, tipo: str, serie_31_12: dict) -> dict:
    """`valores_31_12` é `number` no wire (`baseline_patrimonial.schema.json`) — a série
    entra pronta em vez de por escalar monetário, que a regra P5 proíbe tipar como float."""
    return {
        "descricao": f"{descricao} {_CNPJ_TXT}",
        "tipo": tipo,
        "proprietario": "david",
        "valores_31_12": dict(serie_31_12),
    }


def _soma(entradas: list[dict]):
    return sum(sum(e["valores_31_12"].values()) for e in entradas)


_DISTINTOS = [
    (
        "conta corrente x poupanca",
        ("CONTA CORRENTE", "conta_bancaria", {"2024": 3000.0}),
        ("POUPANCA", "poupanca", {"2024": 5000.0}),
    ),
    (
        "cdb x fii",
        ("CDB BANCO X", "renda_fixa", {"2024": 50000.0}),
        ("FII XPML11", "fundo_investimento", {"2024": 50000.0}),
    ),
    (
        "dois cdbs do mesmo banco",
        ("CDB BANCO X 2027", "renda_fixa", {"2024": 10000.0}),
        ("CDB BANCO X 2030", "renda_fixa", {"2024": 20000.0}),
    ),
]


@pytest.mark.parametrize(("rotulo", "a", "b"), _DISTINTOS, ids=[c[0] for c in _DISTINTOS])
def test_mesma_instituicao_ativos_distintos_NAO_fundem(rotulo, a, b) -> None:
    entradas = [_entrada(*a), _entrada(*b)]
    r = dedup_investimentos_consolidados(entradas)
    assert r.count_after == 2, f"{rotulo}: fundiu ativos distintos da mesma instituição"


@pytest.mark.parametrize(("rotulo", "a", "b"), _DISTINTOS, ids=[c[0] for c in _DISTINTOS])
def test_e_o_patrimonio_nao_some(rotulo, a, b) -> None:
    """O count é o sintoma; o dano é o dinheiro — `_union_valores` resolve por `max()`."""
    entradas = [_entrada(*a), _entrada(*b)]
    esperado = sum(a[2].values()) + sum(b[2].values())
    assert _soma(dedup_investimentos_consolidados(entradas).investimentos) == esperado


def test_o_MESMO_ativo_ainda_funde_pela_ancora() -> None:
    """Anti-vacuidade: se nada mais funde, o fix comprou discriminação matando a âncora."""
    a = _entrada("CDB BANCO EXEMPLO", "renda_fixa", {"2024": 900.0})
    b = dict(a, descricao=f"CDB BANCO EXEMPLO {_CNPJ_TXT}", valores_31_12={"2025": 1000.0})
    r = dedup_investimentos_consolidados([a, b])
    assert r.count_after == 1


def test_a_ancora_ainda_sobrevive_a_rename_de_descricao_do_MESMO_ativo() -> None:
    # Com `desc` de volta na perna forte, o que aguenta é a variação que
    # `normalize_descricao` absorve (caixa, espaço) — não parafrase. Redução declarada.
    """A tese da lane: o extrator reescreve a prosa e a identidade tem de aguentar."""
    a = _entrada("CDB  BANCO   EXEMPLO", "renda_fixa", {"2024": 1000.0})
    b = _entrada("cdb banco exemplo", "renda_fixa", {"2024": 1000.0})
    assert dedup_investimentos_consolidados([a, b]).count_after == 1


def test_instituicoes_DIFERENTES_seguem_distintas() -> None:
    a = {
        "descricao": "CDB CNPJ 12.345.678/0001-95",
        "tipo": "renda_fixa",
        "proprietario": "d",
        "valores_31_12": {"2024": 1.0},
    }
    b = {
        "descricao": "CDB CNPJ 98.765.432/0001-10",
        "tipo": "renda_fixa",
        "proprietario": "d",
        "valores_31_12": {"2024": 1.0},
    }
    assert dedup_investimentos_consolidados([a, b]).count_after == 2
