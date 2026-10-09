"""Situação da métrica do parecer: veredito do comparador ou nível do produtor (A40.l92).

A tabela "Métricas a observar" desenhava a trilha como ``clamp(atual / alvo)``, re-derivada
por regex sobre a string renderizada: o glifo do operador sumia, e a barra ENCHIA conforme a
métrica de teto piorava (``taxa_endividamento`` 45% contra ``≤ 20%`` ⇒ trilha cheia). O
veredito sai daqui como dado, e o front só desenha.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping, Optional, get_args

from pipeline.domain.services.comparador_de_limiar import (
    conforme_ao_limiar,
    numero_finito,
    veredito_do_comparador,
)
from pipeline.domain.services.kpi_orfaos_dominio import MOTIVO_DA_ORFA, NIVEL_DO_PRODUTOR_PATH
from pipeline.domain.services.kpi_target_catalog import OBSERVADO_CONSERVADOR_PATH
from pipeline.llm.schemas.parecer_comparador import (
    Comparador,
    NivelConfianca,
    OperadorComparador,
)
from pipeline.llm.tools.planner_drill_down import PlannerDrillDown

_OPERADORES = frozenset(get_args(OperadorComparador))
_NIVEIS = frozenset(get_args(NivelConfianca))


def comparador_da_metrica(
    alvo: Mapping, observado: Any, *, alvo_publicado: bool
) -> Optional[Comparador]:
    """Veredito sobre o bruto — só quando a linha publica alvo E observado."""
    if not alvo_publicado:
        return None
    veredito = veredito_do_comparador(observado, alvo.get("operador"), alvo.get("limiar"))
    if veredito is None or veredito.operador not in _OPERADORES:
        return None
    return Comparador(
        operador=veredito.operador,
        conforme=veredito.conforme,
        progresso_pct=veredito.progresso_pct,
    )


# Chave cuja situação é o nível do produtor nunca tem comparador, em NENHUMA era. E5
# anterior à A40.l92 publica alvo `< 10` para despesas; regenerado sobre ele (ADR-291), o
# parecer devolveria o veredito que a decisão de domínio removeu — ao lado do nível, duas
# respostas na mesma linha. Subtrai o alvo; nunca acrescenta número.
def alvo_sem_comparador(metrica_key: str, alvo: Mapping) -> Mapping:
    """O alvo lido, sem limiar quando a situação da chave é o nível do produtor."""
    if metrica_key not in NIVEL_DO_PRODUTOR_PATH or alvo.get("limiar") is None:
        return alvo
    sem = {"limiar": None, "operador": None, "procedencia": None, "ref": None}
    return {**alvo, **sem, "motivo": alvo.get("motivo") or MOTIVO_DA_ORFA.get(metrica_key)}


def nivel_do_produtor(metrica_key: str, drill: PlannerDrillDown) -> Optional[str]:
    """Nível publicado pelo produtor para métrica que fala do relatório, não da família."""
    path = NIVEL_DO_PRODUTOR_PATH.get(metrica_key)
    if path is None:
        return None
    lido = drill.valor_bruto(path)
    nivel = lido.value if lido.found else None
    return nivel if isinstance(nivel, str) and nivel in _NIVEIS else None


# Número e status não se contradizem na mesma linha. Se 1 casa põe o observado do lado
# errado do limiar — bruto 20,04 renderizado "20,0%" sob "≤ 20,0%" com "Acima do limite" —,
# mostra-se a 2ª. Arredondar NA DIREÇÃO do veredito fabricaria número; aqui só se ganha
# casa. O resíduo (|Δ| < 0,005) é limite conhecido: o produtor publica até 2 casas.
_CASAS_ADAPTATIVAS = (1, 2)
_SUFIXO = {"meses": " meses", "pct": "%", "pct_aa": "%", "ratio_0_1": "%"}


def medidas_da_linha(metrica_key: str, drill: PlannerDrillDown, path: str) -> tuple[Any, Any]:
    """(medida crua, extremo conservador cru quando o catálogo o declara)."""
    conservador_path = OBSERVADO_CONSERVADOR_PATH.get(metrica_key)
    conservador = drill.valor_bruto(conservador_path).value if conservador_path else None
    return drill.valor_bruto(path).value, conservador


def extremo_conservador(alvo: Mapping, medida: Any, conservador: Any) -> Any:
    """O lado da medida que menos favorece a conformidade — [[ADR-412]] §E3."""
    m, c = numero_finito(medida), numero_finito(conservador)
    if m is None or c is None:
        return medida
    return min(m, c) if alvo.get("operador") == ">=" else max(m, c)


def exibir_sem_contradicao(
    julgado: Any, medida: Any, fator: float, unidade: str, limiar: Any, comparador: Comparador
) -> Optional[str]:
    """Observado (intervalo, se o extremo julgado difere) sem contradizer o veredito."""
    sufixo, lim = _SUFIXO.get(unidade), numero_finito(limiar)
    j, m = numero_finito(julgado), numero_finito(medida)
    if sufixo is None or lim is None or j is None:
        return None
    limiar_exibido, escala = lim * Decimal(str(fator)), Decimal(str(fator))
    casas = next(
        (
            c
            for c in _CASAS_ADAPTATIVAS
            if _concorda(float(j * escala), c, limiar_exibido, comparador)
        ),
        _CASAS_ADAPTATIVAS[-1],
    )
    pontas = sorted({_numero_exibido(v * escala, casas) for v in (j, m if m is not None else j)})
    texto = " a ".join(f"{v:.{casas}f}".replace(".", ",") for v in pontas)
    return texto + sufixo


def _numero_exibido(valor: Decimal, casas: int) -> Decimal:
    return Decimal(f"{float(valor):.{casas}f}")


# Compara o que a família LÊ: a string formatada, não o float — `f"{20.05:.1f}"` e o
# arredondamento de um Decimal discordam no meio-passo.
def _concorda(escalado: float, casas: int, limiar: Decimal, comparador: Comparador) -> bool:
    exibido = Decimal(f"{escalado:.{casas}f}")
    return conforme_ao_limiar(exibido, comparador.operador, limiar) == comparador.conforme


__all__ = [
    "alvo_sem_comparador",
    "comparador_da_metrica",
    "exibir_sem_contradicao",
    "extremo_conservador",
    "medidas_da_linha",
    "nivel_do_produtor",
]
