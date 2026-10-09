"""Onde cada imóvel entra na carteira de investimentos — produtor único do roteamento.

Tabela de classes e ranking decidiam "é a residência?" por `pid in set`, cada um do seu
jeito, e a alocação reconhecia imóvel por um literal próprio. O roteamento passa pelo
mesmo `classificacao_do_imovel` dos splitters do patrimônio ([[ADR-433]] §D3).
"""

from __future__ import annotations

from typing import Any, Mapping

from pipeline.domain.services.patrimonio_imovel_classifier import (
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
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


def classe_do_imovel_na_carteira(
    imovel: Mapping[str, Any], overrides_by_property_id: Mapping[str, str]
) -> str | None:
    """`None` para a residência, que fica fora da carteira; senão a classe de imóvel."""
    classificacao = classificacao_do_imovel(imovel, overrides_by_property_id)
    if classificacao == CLASSIFICATION_RESIDENCIA_PRINCIPAL:
        return None
    return CLASSE_IMOVEIS_INVESTIMENTO


__all__ = [
    "CLASSES_IMOVEL_FISICO",
    "CLASSES_SEM_PESO",
    "CLASSE_IMOVEIS_INVESTIMENTO",
    "CLASSE_IMOVEIS_USO_NAO_APURADO",
    "classe_do_imovel_na_carteira",
]
