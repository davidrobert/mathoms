"""Duas sugestões P1 que se cancelam na mesma classe (§r7 FP-6, braço 2).

Medido no r7: o parecer emitiu "reduzir a concentração em renda fixa" e
"desenvolver estratégia de previdência privada", ambas P1 — e o próprio payload
declara ``comparaveis[renda_fixa].componentes = ["Renda Fixa", "Previdência"]``.
Previdência **é componente** da comparável que a outra sugestão manda reduzir, e o
mapeamento canônico confirma (``_BUCKET_TO_COMPARABLE["Previdência"]`` resolve
para ``renda_fixa`` em ``alocacao_alvo_deviation``). A família lê duas ordens opostas sobre o mesmo balde.

**Rebaixa, nunca bloqueia** — segue a doutrina do guardrail pós-LLM ([[ADR-294]]
"dropar > promover"; este módulo nem dropa). Bloquear proibiria a recomendação mais
defensável do conjunto: previdência para alta renda com horizonte longo é ganho
fiscal/sucessório que existe **independente** da classe do subjacente, e
``Previdência → renda_fixa`` é heurística de keyword, não verdade econômica (um
PGBL pode ter subjacente 100% renda variável).

Por isso o gate exige a **condição de reconciliação explícita**, não a ausência do
par: com condição declarada as duas convivem; sem nenhuma, o item que **aumenta**
cai para P2 com ``confianca=media``.

Direção é lida por proximidade verbo↔classe, não por presença: a sugestão medida
diz "reduzir ... renda fixa e ampliar ... (renda variável brasileira, FIIs,
internacional)" — tem os dois verbos e quatro classes numa frase só, e um matcher
por presença marcaria renda fixa como aumento.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable, Optional

from pipeline.domain.services.alocacao_alvo_deviation import COMPARABLE_KEYS
from pipeline.llm.schemas.parecer_planejador import Sugestao

logger = logging.getLogger("mathoms.llm.parecer_planejador")

REASON_ANTAGONISMO = "parecer_sugestoes_antagonicas_mesma_classe"

#: Sinônimos → chave comparável. Deriva de `_BUCKET_TO_COMPARABLE` (fonte única do
#: bucket→classe) e acrescenta como a prosa do parecer nomeia cada classe.
_SINONIMOS: dict[str, tuple[str, ...]] = {
    "renda_fixa": ("renda fixa", "previdencia", "previdência", "pgbl", "vgbl"),
    "acoes_br": ("acoes br", "ações br", "renda variavel brasileira", "renda variável brasileira"),
    "acoes_int": ("internacional", "exterior", "offshore"),
    "fiis": ("fiis", "fundos imobiliarios", "fundos imobiliários"),
    "fora_alvo": ("cripto",),
}

_REDUZ = ("reduzir", "reduza", "diminuir", "desconcentrar", "desinvestir", "sair de")
_AUMENTA = ("ampliar", "aumentar", "elevar", "desenvolver", "expandir", "reforcar", "reforçar")

#: Condições que reconciliam o par (financial-planner, §r7). Qualquer uma basta —
#: o objetivo é obrigar a explicitar, não proibir.
_RECONCILIA = (
    "subjacente",
    "multimercado",
    "substitui",
    "sem aporte novo",
    "dentro da classe",
    "migrar o estoque",
    "temporariamente",
    "compensavel",
    "compensável",
)


def _normaliza(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).lower()


def _marcas_de_direcao(baixo: str) -> list[tuple[int, int]]:
    marcas = [(baixo.find(v), -1) for v in _REDUZ if v in baixo]
    marcas += [(baixo.find(v), +1) for v in _AUMENTA if v in baixo]
    return sorted(marcas)


def _sinal_para(marcas: list[tuple[int, int]], pos: int) -> int:
    anteriores = [sinal for idx, sinal in marcas if idx < pos]
    return anteriores[-1] if anteriores else marcas[0][1]


def _classes_com_direcao(texto: str) -> dict[str, int]:
    """Classe → sinal (-1 reduz, +1 aumenta) pelo verbo mais próximo à esquerda."""
    baixo = _normaliza(texto)
    marcas = _marcas_de_direcao(baixo)
    if not marcas:
        return {}
    posicoes = {
        classe: min(baixo.find(t) for t in termos if t in baixo)
        for classe, termos in _SINONIMOS.items()
        if any(t in baixo for t in termos)
    }
    return {classe: _sinal_para(marcas, pos) for classe, pos in posicoes.items()}


def _tem_condicao(sug: Sugestao) -> bool:
    blob = _normaliza(f"{sug.acao} {sug.impacto_qualitativo}")
    return any(marcador in blob for marcador in _RECONCILIA)


def _alguem_reduz(itens: list[tuple[Sugestao, dict[str, int]]], classe: str, exceto: int) -> bool:
    return any(m.get(classe, 0) < 0 for j, (_, m) in enumerate(itens) if j != exceto)


def _par_antagonico(itens: list[tuple[Sugestao, dict[str, int]]]) -> Optional[tuple[int, str]]:
    """Índice do item que AUMENTA e a classe em conflito — ou None."""
    for i, (_, mapa) in enumerate(itens):
        aumentadas = [c for c, sinal in mapa.items() if sinal > 0]
        conflito = next((c for c in aumentadas if _alguem_reduz(itens, c, i)), None)
        if conflito is not None:
            return i, conflito
    return None


def _rebaixa(sug: Sugestao) -> Sugestao:
    return sug.model_copy(update={"prioridade": "P2", "confianca": "media"})


# `COMPARABLE_KEYS` vem do módulo que define o mapa bucket→classe, para que classe
# nova nasça conhecida aqui em vez de ser silenciosamente ignorada pelo filtro.
def _classes_conhecidas() -> frozenset[str]:
    return frozenset(COMPARABLE_KEYS)


def _mapas_p1(itens: list[Sugestao]) -> list[tuple[Sugestao, dict[str, int]]]:
    conhecidas = _classes_conhecidas()
    return [
        (
            s,
            {
                c: v
                for c, v in _classes_com_direcao(f"{s.acao} {s.impacto_qualitativo}").items()
                if c in conhecidas
            },
        )
        for s in itens
        if s.prioridade == "P1"
    ]


def rebaixa_sugestoes_antagonicas(
    sugestoes: Iterable[Sugestao], *, workspace_id: str
) -> tuple[list[Sugestao], int]:
    """Rebaixa P1 que aumenta uma classe que outra P1 manda reduzir, sem condição."""
    itens = list(sugestoes)
    indices_p1 = [i for i, s in enumerate(itens) if s.prioridade == "P1"]
    mapas = _mapas_p1(itens)

    achado = _par_antagonico(mapas)
    if achado is None or any(_tem_condicao(s) for s, _ in mapas):
        return itens, 0
    pos, classe = achado
    alvo = indices_p1[pos]
    itens[alvo] = _rebaixa(itens[alvo])
    logger.warning(REASON_ANTAGONISMO, extra={"workspace_id": workspace_id, "classe": classe})
    return itens, 1


__all__ = ["REASON_ANTAGONISMO", "rebaixa_sugestoes_antagonicas"]
