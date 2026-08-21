#!/usr/bin/env python3
"""Fronteira de definição do KPI cambial entre dois runs (ADR-403).

Mora fora de ``compare_reviews`` porque o gate é do COMPARADOR, não do
produtor: marcador que só o produtor emite é decorativo — nada impede o leitor
de subtrair tier de v1 contra tier de v2.
"""

from __future__ import annotations


def _definicao(report_data: dict) -> int | None:
    bloco = report_data.get("exposicao_cambial")
    versao = bloco.get("definicao_versao") if isinstance(bloco, dict) else None
    return versao if isinstance(versao, int) else None


# Tier de v1 (só caixa FX) e de v2 (caixa FX + carteira) medem OBJETOS
# diferentes: o delta entre eles descreve a mudança de definição, não a mudança
# do patrimônio. Run pré-ADR-403 não declara versão — comparar com v1 também é
# atravessar a fronteira.
def serie_reiniciada_cambial(base_rd: dict, cur_rd: dict) -> str | None:
    """Nota quando as duas pontas não são comparáveis — nunca delta."""
    antes, agora = _definicao(base_rd), _definicao(cur_rd)
    if antes == agora:
        return None
    return (
        f"exposicao_cambial — série reiniciada: definicao_versao {antes} → {agora}. "
        "Tier e total medem componentes diferentes; delta entre as pontas não tem sentido."
    )
