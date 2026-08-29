"""Registro de gatilho de risco — o limiar de DOUTRINA que emite ponto urgente ([[ADR-419]]).

Distinto de ``kpi_targets``, que publica o **alvo**. A [[ADR-399]] §D2 roteia os dois
canais na mesma frase: *"publica-se o declarado como ``target`` e o limiar vira
``risco``"*. ``pontos_urgentes`` é o canal risco, então o gatilho vem daqui e nunca do
alvo publicado — a [[ADR-367]] §D2 decide que o alvo **gradua sem mover o gatilho**.

Por que um registro e não uma leitura de ``kpi_targets``: o catálogo é resolvido sobre o
payload **final** (``analyze_finances`` chama ``build_kpi_targets(output, ...)`` depois de
``pontos_urgentes`` já existir). Ler o dict publicado seria circular. Todo limiar de
doutrina é payload-independente, que é exatamente o subconjunto de que esta superfície
precisa.

``kpi_key`` liga a regra ao vocabulário do catálogo — é o que o gate de cobertura usa para
provar que chave elegível nova não nasceu sem leitor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from pipeline.domain.services.kpi_target_catalog import METRICA_KEYS, ORFAOS_DOMINIO_KEYS

# Degraus REUSADOS, não inventados: são os que
# `parecer_red_lines._severidade_exigida_concentracao` já ratificou ([[ADR-340]]
# C11-Fase2), e o comentário de lá encoda a divergência metodológica — entre 40 e 60%
# Cerbasi (estabilidade) e AUVP (diversificar) legitimamente divergem, acima de 60% nem
# Cerbasi sustenta. `test_degraus_pareados_com_a_red_line` prova que os dois lados
# continuam de acordo, no gatilho E na severidade; divergir faria a superfície
# determinística contradizer o hard-block do parecer sobre o mesmo payload.
CONCENTRACAO_ALERTA_PCT = 50.0
CONCENTRACAO_SEVERA_PCT = 75.0

# §Fronteira: `<=` (conforme é `conc <= 50`), não `<`. O catálogo publica `operador: "<"`
# para o mesmo conceito e os dois divergem em **50,00 exato** — lá é rompido, aqui não.
# Sigo a red-line: é a doutrina ratificada e é ela que hard-blocka o parecer, então a
# superfície determinística não pode afirmar risco que o gate do parecer diz não existir.

_OPERADORES = {
    "<": lambda obs, lim: obs < lim,
    "<=": lambda obs, lim: obs <= lim,
    ">": lambda obs, lim: obs > lim,
    ">=": lambda obs, lim: obs >= lim,
}


@dataclass(frozen=True)
class RiskTrigger:
    """Limiar de doutrina que decide a EXISTÊNCIA de um ponto urgente."""

    kpi_key: str
    code: str
    operador: str
    ref: str
    limiar: float
    # Segundo degrau, quando a doutrina gradua a SEVERIDADE sem mover o gatilho
    # ([[ADR-367]] §D2). `None` quando a regra é binária.
    limiar_severo: Optional[float] = None

    def conforme(self, observado: float) -> bool:
        return _OPERADORES[self.operador](observado, self.limiar)

    def rompido(self, observado: float) -> bool:
        return not self.conforme(observado)

    def severo(self, observado: float) -> bool:
        if self.limiar_severo is None:
            return False
        return not _OPERADORES[self.operador](observado, self.limiar_severo)


# Chave sem regra de risco, com o motivo declarado. É a válvula obrigatória do gate de
# cobertura: forçar regra para todo limiar responderia por conta própria uma pergunta de
# domínio ([[ADR-419]] §D4).
DISPENSADAS: dict[str, str] = {
    # Decisão de domínio (financial-planner, 2026-08-27): é tier de confiança do
    # diagnóstico ([[ADR-353]]) — afirmação sobre o RELATÓRIO, não sobre o patrimônio. A
    # ação é do produto (learning loop, [[ADR-186]]/[[ADR-188]]), não do cliente.
    "despesas_nao_categorizadas": "confiança do diagnóstico; a ação é do produto, não do cliente",
    # Órfã dinâmica: o produtor suprime o limiar sem cobertura apurada (#1779). Volta a
    # ser elegível sozinha quando a cobertura for apurada, sem esta superfície mudar.
    "exposicao_cambial": "limiar suprimido pelo produtor enquanto a cobertura não é apurada",
    "renda_passiva_cobertura": "limiar suprimido pelo produtor quando a base não é medível",
}


def _num(valor: Any) -> Optional[float]:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    return float(valor)


def _safe(cfg: Mapping[str, Any], chave: str, default: float) -> float:
    return _num(cfg.get(chave)) if _num(cfg.get(chave)) is not None else default


def _reserva(cfg: Mapping[str, Any]) -> RiskTrigger:
    return RiskTrigger(
        kpi_key="reserva_cobertura_meses",
        code="reserva_insuficiente",
        operador=">=",
        ref="scoring.json::thresholds_alertas.reserva_minima_meses",
        limiar=_safe(cfg, "reserva_minima_meses", 6.0),
    )


def _endividamento(cfg: Mapping[str, Any]) -> RiskTrigger:
    return RiskTrigger(
        kpi_key="taxa_endividamento",
        code="endividamento_alto",
        operador="<=",
        ref="scoring.json::thresholds_alertas.endividamento_maximo_pct",
        limiar=_safe(cfg, "endividamento_maximo_pct", 20.0),
    )


def _concentracao() -> RiskTrigger:
    return RiskTrigger(
        kpi_key="concentracao_imobiliaria",
        code="concentracao_imobiliaria_alta",
        operador="<=",  # ver §Fronteira acima
        ref="parecer_red_lines._severidade_exigida_concentracao ([[ADR-340]])",
        limiar=CONCENTRACAO_ALERTA_PCT,
        limiar_severo=CONCENTRACAO_SEVERA_PCT,
    )


def build_risk_triggers(scoring: Mapping[str, Any] | None = None) -> dict[str, RiskTrigger]:
    """Resolve os gatilhos de doutrina a partir do ``scoring.json``."""
    cfg = (scoring or {}).get("thresholds_alertas") or {}
    gatilhos = (_reserva(cfg), _concentracao(), _endividamento(cfg))
    return {g.kpi_key: g for g in gatilhos}


def chaves_sob_o_gate() -> frozenset[str]:
    """Chaves que precisam de regra ou dispensa — órfã por decisão já se declarou no catálogo."""
    return frozenset(METRICA_KEYS) - frozenset(ORFAOS_DOMINIO_KEYS)


__all__ = [
    "DISPENSADAS",
    "RiskTrigger",
    "build_risk_triggers",
    "chaves_sob_o_gate",
]
