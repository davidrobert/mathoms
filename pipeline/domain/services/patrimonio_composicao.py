"""Composição patrimonial publicada — categorias visíveis + percentuais.

Extraído de `patrimonio_calculator.py` (A40.l80): o arquivo chegou ao teto de 500
linhas, e a composição é responsabilidade própria — monta o rótulo exibido e
distribui percentual, sem tocar em agregado nenhum.
"""

from __future__ import annotations

from pipeline.domain.services.patrimonio_types import MemberIdentity


def build_composicao(
    *,
    identity: MemberIdentity,
    residencia: float,
    imoveis_investimento: float,
    investimentos_titular: float,
    investimentos_conjuge: float,
    caixa: float,
    veiculos: float,
    nao_atribuidos: float = 0.0,
) -> list[dict]:
    """Categorias visíveis + percentuais via largest-remainder (soma = 100%).

    Paridade legado: materializa 6 das 7 buckets de [[ADR-145]] — Residência (#1),
    Outros imóveis (#2), Investimentos Titular (#3), Investimentos Cônjuge (#4),
    Caixa + ME (#6), Veículos (#7). Bucket #5 (Criptoativos) consolida em #3/#6
    conforme [[ADR-145]]; com extrato de exchange a separação visual aparece no
    doughnut de ``investimentos_classes``, não aqui.
    """
    composicao = _categorias(
        identity=identity,
        residencia=residencia,
        imoveis_investimento=imoveis_investimento,
        investimentos_titular=investimentos_titular,
        investimentos_conjuge=investimentos_conjuge,
        caixa=caixa,
        veiculos=veiculos,
    )
    # Só aparece quando existe: categoria permanente com 0,00 em todo run sadio
    # seria ruído no donut de toda família bem resolvida.
    if nao_atribuidos:
        composicao.append(
            {"categoria": "Investimentos sem titular identificado", "valor": nao_atribuidos}
        )
    aplicar_percentuais_maior_resto(composicao)
    composicao.sort(key=lambda x: x["valor"], reverse=True)
    return composicao


# [[ADR-215]] P3 renomeou o bucket cat_2 de "Imóveis Investimento" para "Imóveis de
# Renda", "que comunica o critério econômico real (geração de caixa)". [[ADR-420]] §D1
# mediu que essa justificativa é FALSA para este balde: cat_2 contém `uso_pessoal` e
# `nu_proprietario`, que não geram renda nenhuma — o rename de 2025 foi o vetor de uma
# afirmação que o número não sustenta, e não a sua correção.
#
# "Outros imóveis" desde 2026-09-01: subtrai o qualificador falso em vez de inventar
# um novo, e diz literalmente o que o balde é — todo imóvel que não é a residência
# principal, que é a linha logo acima. Quem quiser o critério econômico tem
# `ratios.concentracao_imobiliaria` (rebalanceáveis) e `imobilizacao_patrimonial_pct`.
# ⚠️ Copy de superfície visível: escolhida por subtração, não por design — confirmar
# com `product-designer` na próxima passada de copy do relatório.
#
# `template_key` interno (`imoveis_investimento`) é estável ([[ADR-145]] proíbe
# rename de key); só o label exibido muda.
def _categorias(
    *,
    identity: MemberIdentity,
    residencia: float,
    imoveis_investimento: float,
    investimentos_titular: float,
    investimentos_conjuge: float,
    caixa: float,
    veiculos: float,
) -> list[dict]:
    return [
        {"categoria": "Residência", "valor": residencia},
        {"categoria": "Outros imóveis", "valor": imoveis_investimento},
        {"categoria": f"Investimentos {identity.titular_nome}", "valor": investimentos_titular},
        {"categoria": f"Investimentos {identity.conjuge_nome}", "valor": investimentos_conjuge},
        {"categoria": "Caixa e Moeda Estrangeira", "valor": caixa},
        {"categoria": "Veículos", "valor": veiculos},
    ]


def aplicar_percentuais_maior_resto(composicao: list[dict]) -> None:
    """Percentuais pelo método do maior resto (soma exata = 100%); muta in-place."""
    total = sum(c["valor"] for c in composicao)
    if total <= 0:
        for comp in composicao:
            comp["pct"] = 0.0
        return
    brutos = [(c["valor"] / total) * 100 for c in composicao]
    truncados = [int(p * 100) / 100.0 for p in brutos]
    passos = int(round(round(100.0 - sum(truncados), 2) / 0.01))
    restos = sorted(((brutos[i] - truncados[i], i) for i in range(len(composicao))), reverse=True)
    for _, idx in restos[: max(0, min(passos, len(restos)))]:
        truncados[idx] += 0.01
    for i, comp in enumerate(composicao):
        comp["pct"] = round(truncados[i], 2)
