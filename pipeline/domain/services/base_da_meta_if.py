"""Base da meta de IF — o que foi descontado da renda-alvo antes de capitalizar ([[ADR-418]]).

Split de ``if_projector`` quando ele cruzou o teto de 500 linhas por arquivo. O bloco é
coeso: vocabulário da base, procedência do termo, e a composição — as três coisas que a
[[ADR-418]] §D3 exige que viajem juntas para que a base seja auditável só pelo payload.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# Vocabulário PRÓPRIO, interseção vazia com `BaseFinanceira` (ADR-412, eixo de
# posições) e com `kpi_targets[].base`. Lá a base é um conjunto de ativos; aqui é
# o que foi descontado da renda-alvo antes de capitalizar.
class BaseDaMetaIF(str, Enum):
    """De que base saiu a meta publicada em ``if_meta`` ([[ADR-418]] §D3)."""

    renda_alvo_bruta = "renda_alvo_bruta"
    renda_alvo_liquida_de_renda_externa = "renda_alvo_liquida_de_renda_externa"
    # A renda de fora cobre o alvo sozinha: a meta clampa em zero e o progresso
    # deixa de ser mensurável — `investivel_efetivo ÷ 0` não é 100%, é indefinido
    # (co-design `financial-planner`, [[ADR-418]] §D5).
    renda_externa_cobre_alvo = "renda_externa_cobre_alvo"


# A procedência viaja com o número ([[ADR-412]]): sem ela, "descontei X" é
# indistinguível de "descontei X vindo de um balde residual contaminado".
class OrigemRendaFora(str, Enum):
    """De onde saiu o termo descontado da meta."""

    cat2_no_numerador = "cat2_no_numerador"
    sem_gerador_excluido = "sem_gerador_excluido"
    residual_irpf_com_haircut = "residual_irpf_com_haircut"


# O campo é `mensal`, não `mensal_brl`: este módulo inteiro é domínio `float` legado
# (`if_meta`, `if_gap`, `investivel`), e um único campo em `Decimal` criaria fronteira
# mista no meio da capitalização. A chave PUBLICADA segue
# `renda_passiva_fora_do_investivel_mensal_brl` — o wire é JSON `number` (ADR-090
# §consequências), igual a `renda_passiva_anual_observada_brl` no mesmo bloco.
@dataclass(frozen=True)
class RendaPassivaFora:
    """Renda mensal (BRL) de ativo que o numerador exclui, com a procedência do número."""

    mensal: float
    origem: OrigemRendaFora


# O invariante é o par, não a fórmula ([[ADR-418]] §D1): renda de ativo DENTRO do
# numerador não desconta (dupla-contagem, ADR-142) e renda de ativo FORA desconta
# (senão a exclusão é cobrada duas vezes). Capitalização é linear, então descontar a
# renda e capitalizar equivale a capitalizar o termo e subtrair da bruta.
def compor_meta_if(
    *, meta_bruta: float, renda_passiva_fora_do_investivel_mensal: float | None, if_trs_pct: float
) -> float:
    """Meta operacional: a bruta menos o que ativo FORA do numerador já paga."""
    if if_trs_pct <= 0 or not renda_passiva_fora_do_investivel_mensal:
        return meta_bruta
    capitalizacao = 12.0 / (if_trs_pct / 100.0)
    return max(0.0, meta_bruta - renda_passiva_fora_do_investivel_mensal * capitalizacao)


# `cfg.if_meta` tem `exclusiveMinimum: 0` no Goal, então `meta <= 0` era ramo morto — até a
# [[ADR-418]] tornar a meta descontável. Nem 0% nem 100% servem ali: 0% contradiz `if_gap` e
# `prazo_anos_realista` (que já dizem "chegou"), e 100% concederia a banda de topo de um
# componente de peso 2,0 a uma família cuja carteira financeira pode ser ZERO — a renda que
# cobre o alvo vem de ativo que o próprio workspace excluiu por não sustentar retirada a TRS
# ([[ADR-418]] §D5, co-design `financial-planner`). Ausência propaga, como em [[ADR-373]].
def base_da_meta(*, meta: float, meta_bruta: float) -> BaseDaMetaIF:
    """Qual base produziu ``meta`` — nunca inferida pelo leitor ([[ADR-418]] §D3)."""
    if meta <= 0 < meta_bruta:
        return BaseDaMetaIF.renda_externa_cobre_alvo
    return (
        BaseDaMetaIF.renda_alvo_bruta
        if meta == meta_bruta
        else BaseDaMetaIF.renda_alvo_liquida_de_renda_externa
    )


def progresso_if_pct(*, investivel: float, meta: float) -> float | None:
    """Percentual da meta operacional; ``None`` quando a meta clampou em zero."""
    return investivel / meta * 100 if meta > 0 else None
