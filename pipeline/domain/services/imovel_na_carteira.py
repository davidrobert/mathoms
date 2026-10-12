"""Onde cada imóvel entra na carteira de investimentos — produtor único do roteamento.

Tabela de classes e ranking decidiam "é a residência?" por `pid in set`, cada um do seu
jeito, e a alocação reconhecia imóvel por um literal próprio. O roteamento passa pelo
mesmo `classificacao_do_imovel` dos splitters do patrimônio ([[ADR-433]] §D3).
"""

from __future__ import annotations

from typing import Any, Mapping

from pipeline.domain.services.patrimonio_imovel_classifier import (
    CLASSIFICATION_DESCONHECIDO,
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    CLASSIFICATIONS_FORA_DA_ALOCACAO,
    classificacao_do_imovel,
)

CLASSE_IMOVEIS_INVESTIMENTO = "Imóveis Investimento"
# [[ADR-444]] D3: imóvel que pode ser a residência entra com valor e SEM PESO. O nome é
# chave gravada no artefato e rótulo exibido ao mesmo tempo — renomear custa duas fases.
CLASSE_IMOVEIS_USO_NAO_APURADO = "Imóveis com uso não apurado"

# Imóvel físico fica fora da carteira financeira (A37.l9) e entra na alocação como imóvel.
# Um conjunto só: classe de imóvel que fique fora dele some calada de um dos leitores.
CLASSES_IMOVEL_FISICO: frozenset[str] = frozenset(
    {CLASSE_IMOVEIS_INVESTIMENTO, CLASSE_IMOVEIS_USO_NAO_APURADO}
)
# Fora de `total` e de toda base de carteira: publica valor, nunca percentual.
CLASSES_SEM_PESO: frozenset[str] = frozenset({CLASSE_IMOVEIS_USO_NAO_APURADO})

# [[ADR-444]] D9: carteira é o que o próximo aporte move — a residência e o que a família
# declarou não rebalanceável (uso pessoal, nu-propriedade) ficam fora. A lista é a MESMA do
# numerador da concentração ([[ADR-420]] §D1): duas listas divergiriam caladas.
_FORA_DA_CARTEIRA: frozenset[str] = (
    frozenset({CLASSIFICATION_RESIDENCIA_PRINCIPAL}) | CLASSIFICATIONS_FORA_DA_ALOCACAO
)


# Com a residência identificada (ou a família alugando), o desconhecido é não-residência por
# ELIMINAÇÃO do bem identificado e fica em "Imóveis Investimento" — o resíduo da cota do
# cônjuge sem id é o `piso` da [[ADR-439]] D2, declarado no schema ([[ADR-444]] D6).
def classe_do_imovel_na_carteira(
    imovel: Mapping[str, Any],
    overrides_by_property_id: Mapping[str, str],
    *,
    residencia_no_desconhecido: bool = False,
) -> str | None:
    """`None` fora da carteira; o desconhecido que pode ser a residência entra sem peso."""
    classificacao = classificacao_do_imovel(imovel, overrides_by_property_id)
    if classificacao in _FORA_DA_CARTEIRA:
        return None
    if classificacao == CLASSIFICATION_DESCONHECIDO and residencia_no_desconhecido:
        return CLASSE_IMOVEIS_USO_NAO_APURADO
    return CLASSE_IMOVEIS_INVESTIMENTO


__all__ = [
    "CLASSES_IMOVEL_FISICO",
    "CLASSES_SEM_PESO",
    "CLASSE_IMOVEIS_INVESTIMENTO",
    "CLASSE_IMOVEIS_USO_NAO_APURADO",
    "classe_do_imovel_na_carteira",
]
