"""σ do cone de IF agregado das premissas vigentes pelos pesos do alvo (ADR-374)."""

# O argumento de D1 não é "é mais precisa": `σ_p ≤ Σ wᵢ σᵢ` vale para QUALQUER
# matriz de correlação (desigualdade triangular em L²), logo a soma ponderada é
# limite superior demonstrável — afirmação verdadeira sem conhecer o insumo que
# falta. O defeito que isso corrige não é o nível (0,11 é plausível para carteira
# balanceada) e sim a INVARIÂNCIA: hoje uma família 80% Tesouro Selic e uma 90%
# ações recebem o mesmo cone.

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

# D1 — o mapa é EXPLÍCITO porque 3 das 7 chaves NÃO derivam por sufixo:
# `key.removesuffix("_pct")` produziria `rf_ipca`, `acoes_int` e `fiis`, que não
# existem em `economic_asset_class`. As três cairiam como "classe sem σ vigente",
# D4 abortaria, e o resultado seria fallback em 100% dos runs com a feature
# parecendo entregue.
_CLASSE_POR_CHAVE_DO_ALVO: Mapping[str, str] = {
    "rf_pos_pct": "rf_pos",
    "rf_pre_pct": "rf_pre",
    "rf_ipca_pct": "rf_inflacao",
    "acoes_br_pct": "acoes_br",
    "acoes_int_pct": "acoes_intl",
    "fiis_pct": "fii",
    "caixa_pct": "caixa",
}

CLASSE_IMOVEIS = "imoveis_diretos"

# D6 — valores ENUMERADOS, não string livre: senão cada call-site inventa a sua.
AGREGACAO_SOMA_PONDERADA = "soma_ponderada_sem_desconto_de_correlacao"
BASE_ALVO_DECLARADO = "alocacao_alvo_declarada"
BASE_ALVO_MAIS_IMOVEIS_OBSERVADOS = "alocacao_alvo_declarada_mais_imoveis_observados"

PROCEDENCIA_GLOBAL = "global"
PROCEDENCIA_WORKSPACE_OVERRIDE = "workspace_override"

_CEM = Decimal("100")
# Teto duro da §Critério de aceite. Asserido no DECIMAL que
# `IFMonteCarloConfig.sigma_anual` de fato recebe — a redação anterior da ADR dizia
# que a invariante pegava o erro pct↔decimal de 100× e NÃO pegava: em pct,
# `1,5 ≤ 10,8 ≤ 22` passa, e o erro nasce no handoff para o config, que é decimal.
_TETO_SIGMA_DECIMAL = Decimal("0.30")


@dataclass(frozen=True)
class PremissaDeClasse:
    """σ vigente de uma classe, como o snapshot da [[ADR-219]] o publica."""

    # `None` = sem premissa vigente (classe `indisponivel`, ou `effective_to`
    # vencido sem sucessor). Dispara D4 se a classe tiver peso positivo.
    sigma_anual_pct: Decimal | None
    veio_de_override: bool = False


@dataclass(frozen=True)
class SigmaAgregado:
    """σ anual em DECIMAL (o que o config consome) + campos de auditoria (D6)."""

    sigma_anual: Decimal
    procedencia: str
    base_pesos: str
    # R2 do co-design: o conjunto contribuinte é DECLARADO, não re-derivado por
    # quem precisar dele depois — o gatilho da nota de recalibração precisa saber
    # quais classes de fato pesaram, e re-calcular peso fora de
    # `pipeline/domain/services/` duplicaria domínio.
    classes_contribuintes: tuple[tuple[str, Decimal], ...]
    agregacao: str = AGREGACAO_SOMA_PONDERADA


def _escala_do_alvo(soma_declarada: Decimal, peso_imoveis: Decimal) -> Decimal:
    """Fator que normaliza o alvo a `1 - peso_imoveis` (D9 renormaliza o restante)."""
    return (Decimal(1) - peso_imoveis) / soma_declarada


def _classes_declaradas(alvo_pct: Mapping[str, Decimal]) -> dict[str, Decimal]:
    """Chaves do alvo v2 traduzidas para `economic_asset_class.code`, sem os zeros."""
    return {
        _CLASSE_POR_CHAVE_DO_ALVO[chave]: valor
        for chave, valor in alvo_pct.items()
        if chave in _CLASSE_POR_CHAVE_DO_ALVO and valor > 0
    }


# Os `inputs` CRUS normalizados a 100 **incluindo caixa**. Não reusar
# `_normalize_alvo` de `alocacao_alvo_deviation`: ele exclui caixa (ADR-141 §Emenda
# item 1) porque responde outra pergunta, e reusá-lo apaga o único amortecedor de
# volatilidade do pool — no alvo padrão dá 11,94% em vez de 10,80%.
def _pesos_do_alvo(
    alvo_pct: Mapping[str, Decimal], peso_imoveis: Decimal
) -> dict[str, Decimal] | None:
    """Pesos finais por `economic_asset_class.code`; ``None`` sem alvo declarado (D3)."""
    declarados = _classes_declaradas(alvo_pct)
    soma = sum(declarados.values(), Decimal(0))
    if soma <= 0:
        return {CLASSE_IMOVEIS: peso_imoveis} if peso_imoveis > 0 else None
    escala = _escala_do_alvo(soma, peso_imoveis)
    pesos = {classe: valor * escala for classe, valor in declarados.items()}
    if peso_imoveis > 0:
        pesos[CLASSE_IMOVEIS] = peso_imoveis
    return {classe: peso for classe, peso in pesos.items() if peso > 0}


def _sigmas_contribuintes(
    pesos: Mapping[str, Decimal], premissas: Mapping[str, PremissaDeClasse]
) -> dict[str, Decimal] | None:
    """σ de cada classe de peso positivo; ``None`` se qualquer uma faltar (D4)."""
    # A agregação é definida SE E SOMENTE SE toda classe de peso positivo tem σ
    # vigente. As duas alternativas são piores e na direção errada: excluir e
    # renormalizar enviesa σ para BAIXO quando a faltante é a volátil (cone mais
    # estreito por ausência de dado), e default por classe é a mentira de
    # procedência que esta lane está deletando, com granularidade maior.
    sigmas: dict[str, Decimal] = {}
    for classe in pesos:
        premissa = premissas.get(classe)
        if premissa is None or premissa.sigma_anual_pct is None:
            return None
        sigmas[classe] = premissa.sigma_anual_pct
    return sigmas


def _procedencia(pesos: Mapping[str, Decimal], premissas: Mapping[str, PremissaDeClasse]) -> str:
    """`workspace_override` se QUALQUER classe contribuinte veio de override (D6)."""
    contribuiu_override = any(
        premissas[classe].veio_de_override for classe in pesos if classe in premissas
    )
    return PROCEDENCIA_WORKSPACE_OVERRIDE if contribuiu_override else PROCEDENCIA_GLOBAL


def _exige_sanidade(sigma_decimal: Decimal, sigmas: Mapping[str, Decimal]) -> None:
    """Invariante da §Critério de aceite, no decimal que o config consome."""
    piso, teto = min(sigmas.values()) / _CEM, max(sigmas.values()) / _CEM
    if not (piso <= sigma_decimal <= teto):
        raise ValueError(
            f"σ agregado fora do envelope das classes contribuintes: "
            f"esperado {piso} <= σ <= {teto}, got {sigma_decimal}"
        )
    if not (Decimal(0) < sigma_decimal <= _TETO_SIGMA_DECIMAL):
        raise ValueError(
            f"σ agregado fora do teto duro (ADR-374): esperado "
            f"0 < σ <= {_TETO_SIGMA_DECIMAL} em DECIMAL, got {sigma_decimal} — "
            f"suspeite de pct tratado como decimal (erro de 100×)"
        )


def _base_pesos(peso_imoveis: Decimal) -> str:
    """Base mista tem nome próprio: um valor único mentiria sobre a composição."""
    return BASE_ALVO_MAIS_IMOVEIS_OBSERVADOS if peso_imoveis > 0 else BASE_ALVO_DECLARADO


def _com_auditoria(
    sigma_anual: Decimal,
    pesos: Mapping[str, Decimal],
    premissas: Mapping[str, PremissaDeClasse],
    peso_imoveis: Decimal,
) -> SigmaAgregado:
    """Empacota σ com os campos de auditoria da D6."""
    return SigmaAgregado(
        sigma_anual=sigma_anual,
        procedencia=_procedencia(pesos, premissas),
        base_pesos=_base_pesos(peso_imoveis),
        classes_contribuintes=tuple(sorted(pesos.items())),
    )


def _soma_ponderada(pesos: Mapping[str, Decimal], sigmas: Mapping[str, Decimal]) -> Decimal:
    """`Σ wᵢ σᵢ` de pct para DECIMAL, que é a unidade que o config consome."""
    return sum((pesos[classe] * sigmas[classe] for classe in pesos), Decimal(0)) / _CEM


# ``peso_imoveis`` é ``cat2_efetivo / investivel_efetivo`` quando o imóvel de renda
# está no pool simulado (D9) — peso OBSERVADO, porque prédio não se rebalanceia por
# aporte e para ele prospectivo ≡ observado.
def agregar_sigma_do_alvo(
    *,
    alvo_pct: Mapping[str, Decimal],
    premissas: Mapping[str, PremissaDeClasse],
    peso_imoveis: Decimal = Decimal(0),
) -> SigmaAgregado | None:
    """σ do cone pelos pesos do alvo declarado; ``None`` ⇒ o caller mantém o fallback."""
    pesos = _pesos_do_alvo(alvo_pct, peso_imoveis)
    if not pesos:
        return None
    sigmas = _sigmas_contribuintes(pesos, premissas)
    if sigmas is None:
        return None
    sigma_decimal = _soma_ponderada(pesos, sigmas)
    _exige_sanidade(sigma_decimal, sigmas)
    return _com_auditoria(sigma_decimal, pesos, premissas, peso_imoveis)
