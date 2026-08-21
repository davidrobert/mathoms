"""Alvo de KPI tem procedência declarada — o LLM seleciona, não autora (§r7 PE-2/FP-6).

O parecer publicava ``metricas[].target`` como string livre do LLM. Medido em dois
runs sobre payload byte-idêntico (``ratios.concentracao_imobiliaria = 34.86`` nos
dois), o alvo migrou de ``< 30%`` para ``< 35%`` — **atravessando o valor
observado**: violação virou conformidade sem nada ter mudado no patrimônio. E o
limiar canônico do repo para esse conceito é 50% ([[ADR-340]]), então os dois
números do LLM estavam errados, em direções opostas.

Este módulo é o leitor único do limiar **na rota do `target` publicado** — não do
repo. Os leitores pré-existentes de ``endividamento_maximo_pct``
(``pontos_fortes_analyzer``, ``pontos_urgentes_analyzer``, com default inline
duplicado) permanecem; unificá-los é trabalho à parte. O que esta rota evita é uma
**quarta** cópia, nascendo no backend.

Duas procedências, com precedência declarada — **alvo da família vence doutrina do
produto** (co-design financial-planner: na metodologia dona da métrica o desvio só
existe contra o alvo declarado, e publicar número mais frouxo que o compromisso da
família é o produto absolvendo-a da própria meta):

- ``goal_declarado`` — a família escolheu (``goals.*``, ``reserva_emergencia.meses_alvo``).
- ``limiar_canonico`` — doutrina do produto em config/código, vale para toda família.

Alvo sem fonte única é **órfão**: publica ``limiar=None`` + ``motivo`` legível, nunca
um número inventado. Órfão é fato esperado, não anomalia — não vira ``needs_review``
(usar o canal de retenção para o caso comum queima o canal), e a métrica continua
publicada como observacional para não perder o sinal.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional

from pipeline.domain.services.diagnostico_comportamental_analyzer import (
    NAO_IDENTIFICADO_PARCIAL_PCT,
)
from pipeline.domain.services.exposicao_cambial_analyzer import THRESHOLD_VERDE_PCT
from pipeline.domain.services.real_estate_metrics import RealEstateConfig

#: Vocabulário fechado de KPI. O LLM escolhe uma destas chaves; não inventa alvo.
#: Chave nova aqui exige fonte determinística OU motivo de órfão — nunca um número
#: escolhido na hora.
METRICA_KEYS = (
    "taxa_poupanca_recorrente",
    "reserva_cobertura_meses",
    "alocacao_renda_fixa",
    "concentracao_imobiliaria",
    "exposicao_cambial",
    "carteira_trs",
    "taxa_endividamento",
    "if_progresso",
    "despesas_nao_categorizadas",
    "protecao_cobertura",
)

PROCEDENCIA_GOAL = "goal_declarado"
PROCEDENCIA_CANONICO = "limiar_canonico"


@dataclass(frozen=True)
class KpiTarget:
    """Alvo de um KPI com procedência auditável — ``limiar is None`` ⇒ órfão."""

    # `motivo` diz por que é órfão e é o texto que a UI mostra no lugar do alvo.
    observado_path: str
    base: str
    unidade: str
    limiar: Optional[float] = None
    operador: Optional[str] = None
    procedencia: Optional[str] = None
    ref: Optional[str] = None
    motivo: Optional[str] = None


# Limiar que vive em constante de código/config; `ref` aponta o leitor único.
# Tupla: (chave, observado_path, base, unidade, limiar, operador, ref)
_CANONICOS = (
    (
        "exposicao_cambial",
        "$.exposicao_cambial.pct_investivel_financeiro",
        "investivel_financeiro",
        "pct",
        THRESHOLD_VERDE_PCT,
        ">=",
        "exposicao_cambial_analyzer.THRESHOLD_VERDE_PCT",
    ),
    (
        "despesas_nao_categorizadas",
        "$.diagnostico_confianca.share_nao_identificado_pct",
        "despesa_total",
        "pct",
        NAO_IDENTIFICADO_PARCIAL_PCT,
        "<",
        "diagnostico_comportamental_analyzer.NAO_IDENTIFICADO_PARCIAL_PCT",
    ),
)

# Órfãos por DECISÃO de domínio, não por lacuna de implementação — publicar número
# aqui seria regressão, não melhoria:
#
# - `carteira_trs` — [[ADR-191]] §D5: TRS efetiva é yield observado e não tem
#   comparador. O parecer publicou "≥ IPCA+4%" e depois "≥ 6% real": 4% vs 6% real,
#   e ambos comparam yield de fluxo com retorno TOTAL (yield + ganho de capital),
#   induzindo "vender growth para perseguir dividend yield" — o erro de iniciante
#   que a métrica existe para evitar.
# - `protecao_cobertura` — [[ADR-387]] proíbe afirmar capital ideal sem segurado,
#   dependência econômica e inventário confirmados. O publicado ("≥ 60 meses de
#   renda") era 2 a 4× mais frouxo que o canon (10× renda anual × fator + dívidas),
#   na única métrica cujo erro é irreversível para terceiros (os dependentes).
# - `taxa_poupanca_recorrente` — RV2-24: `poupanca_referencia_pct` (25) e
#   `pontos_fortes_taxa_poupanca_min_pct` (30) descrevem o mesmo conceito sem
#   precedência declarada. O resolver NÃO escolhe: escolher seria inventar regra de
#   domínio com carimbo de procedência — pior que o alvo do LLM por parecer autoritativo.
# - `if_progresso` — o alvo é o par (ano declarado, 100%); o ano sozinho promete
#   estado futuro sem a probabilidade do cone, que a persona proíbe (R20).
#
# Tupla: (chave, observado_path, base, unidade, motivo)
_ORFAOS_DOMINIO = (
    (
        "carteira_trs",
        "$.ratios.rentabilidade.trs_pct",
        "patrimonio_gerador",
        "pct_aa",
        "rentabilidade observada não tem alvo canônico (ADR-191 §D5)",
    ),
    (
        "protecao_cobertura",
        "$.protecao_patrimonial.pct_renda_anual",
        "renda_anual_ativa",
        "pct",
        "capital ideal exige inventário de proteção confirmado (ADR-387)",
    ),
    (
        "taxa_poupanca_recorrente",
        "$.ratios.taxa_poupanca_recorrente_pct",
        "receita_recorrente",
        "pct",
        "duas fontes divergentes para o mesmo limiar (RV2-24)",
    ),
    (
        "if_progresso",
        "$.goals.if_pct",
        "patrimonio_alvo",
        "pct",
        "progresso rumo à IF é acompanhado pelo cone, não por alvo pontual",
    ),
)


def _leaf(payload: Mapping[str, Any], *caminho: str) -> Any:
    no: Any = payload
    for chave in caminho:
        if not isinstance(no, Mapping):
            return None
        no = no.get(chave)
    return no


def _num(valor: Any) -> Optional[float]:
    return float(valor) if isinstance(valor, (int, float)) and not isinstance(valor, bool) else None


def _comparavel(e5: Mapping[str, Any], classe: str) -> Optional[Mapping[str, Any]]:
    """Join por ``classe``, nunca por índice — a lista é ordenada por desvio."""
    derived = _leaf(e5, "goals", "alocacao_alvo", "derived")
    if not isinstance(derived, Mapping):
        return None
    for item in derived.get("comparaveis") or ():
        if isinstance(item, Mapping) and item.get("classe") == classe:
            return item
    return None


def _orfao(observado_path: str, base: str, unidade: str, motivo: str) -> KpiTarget:
    return KpiTarget(observado_path=observado_path, base=base, unidade=unidade, motivo=motivo)


def _reserva(e5: Mapping[str, Any]) -> KpiTarget:
    meses = _num(_leaf(e5, "reserva_emergencia", "meses_alvo"))
    path, base = "$.reserva_emergencia.cobertura_meses", "despesa_essencial_mensal"
    if meses is None:
        return _orfao(path, base, "meses", "alvo de reserva não computado para este perfil")
    return KpiTarget(
        observado_path=path,
        base=base,
        unidade="meses",
        limiar=meses,
        operador=">=",
        procedencia=PROCEDENCIA_GOAL,
        ref="$.reserva_emergencia.meses_alvo",
    )


# Casar as duas pontas na mesma base é o que fecha o FP-6: o parecer publicava
# observado de `tabela_classes` (base carteira financeira) contra alvo de
# `comparaveis` (base carteira líquida), e o desvio saía ~10pp menor que o
# `desvio_pp` que o motor já havia calculado.
def _alocacao_renda_fixa(e5: Mapping[str, Any]) -> KpiTarget:
    comp = _comparavel(e5, "renda_fixa")
    alvo = _num(comp.get("alvo_pct")) if comp else None
    path = "$.goals.alocacao_alvo.derived.comparaveis[classe=renda_fixa].atual_pct"
    base = "carteira_liquida"
    if alvo is None:
        return _orfao(path, base, "pct", "alocação-alvo não declarada para renda fixa")
    return KpiTarget(
        observado_path=path,
        base=base,
        unidade="pct",
        limiar=alvo,
        operador="<=",
        procedencia=PROCEDENCIA_GOAL,
        ref="$.goals.alocacao_alvo.derived.comparaveis[classe=renda_fixa].alvo_pct",
    )


def _concentracao_imobiliaria(alerta_pct: float) -> KpiTarget:
    return KpiTarget(
        observado_path="$.ratios.concentracao_imobiliaria",
        base="carteira_produtiva",
        unidade="pct",
        limiar=alerta_pct,
        operador="<",
        procedencia=PROCEDENCIA_CANONICO,
        ref="RealEstateConfig.concentracao_alerta_pct ([[ADR-340]])",
    )


# Pareamento enforçado em pontos_urgentes_analyzer.py — mesma razão, mesmo limiar.
def _endividamento(scoring: Mapping[str, Any]) -> KpiTarget:
    alertas = scoring.get("thresholds_alertas") or {}
    maximo = _num(alertas.get("endividamento_maximo_pct"))
    path, base = "$.ratios.taxa_endividamento_pct", "patrimonio_bruto"
    if maximo is None:
        return _orfao(path, base, "pct", "limiar de endividamento ausente do scoring")
    return KpiTarget(
        observado_path=path,
        base=base,
        unidade="pct",
        limiar=maximo,
        operador="<=",
        procedencia=PROCEDENCIA_CANONICO,
        ref="scoring.json::thresholds_alertas.endividamento_maximo_pct",
    )


def _tabelados() -> dict[str, KpiTarget]:
    canonicos = {
        chave: KpiTarget(
            observado_path=path,
            base=base,
            unidade=unidade,
            limiar=limiar,
            operador=operador,
            procedencia=PROCEDENCIA_CANONICO,
            ref=ref,
        )
        for chave, path, base, unidade, limiar, operador, ref in _CANONICOS
    }
    orfaos = {
        chave: _orfao(path, base, unidade, motivo)
        for chave, path, base, unidade, motivo in _ORFAOS_DOMINIO
    }
    return {**canonicos, **orfaos}


# `concentracao_alerta_pct` entra por parâmetro (e não é lido de um global) porque é
# overridável por workspace via ConfigStore ([[ADR-134]]) — só o produtor conhece a
# config efetiva.
def build_kpi_targets(
    e5: Mapping[str, Any],
    *,
    scoring: Mapping[str, Any],
    concentracao_alerta_pct: Optional[float] = None,
) -> dict[str, dict[str, Any]]:
    """Resolve o alvo de cada KPI do vocabulário a partir do payload E5 + config."""
    alerta = (
        concentracao_alerta_pct
        if concentracao_alerta_pct is not None
        else float(RealEstateConfig().concentracao_alerta_pct)
    )
    alvos: dict[str, KpiTarget] = {
        "reserva_cobertura_meses": _reserva(e5),
        "alocacao_renda_fixa": _alocacao_renda_fixa(e5),
        "concentracao_imobiliaria": _concentracao_imobiliaria(alerta),
        "taxa_endividamento": _endividamento(scoring),
        **_tabelados(),
    }
    return {chave: asdict(alvo) for chave, alvo in alvos.items()}


__all__ = [
    "METRICA_KEYS",
    "PROCEDENCIA_CANONICO",
    "PROCEDENCIA_GOAL",
    "KpiTarget",
    "build_kpi_targets",
]
