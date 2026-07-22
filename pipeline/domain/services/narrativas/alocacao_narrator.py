"""Narrador do chart ``alocacao_atual_vs_alvo`` — taxonomia v2 (A37.l8 · FIN-05).

Consome ``goals.alocacao_alvo.derived`` (injetado pelo E5 via
``AlocacaoAlvoDeviationCalculator``) — a MESMA base da tabela do card React.
Não recalcula desvio; apenas narra. Labels em paridade com
``frontend/src/components/report/cards/alocacaoCardParts.tsx`` (``labelFor``).
"""

from __future__ import annotations

from typing import Any, Mapping

from pipeline.domain.services.narrativas.format_helpers import (
    fmt_currency,
    fmt_num,
    fmt_percent,
)

_ALOC_CLASSE_LABELS: dict[str, str] = {
    "renda_fixa": "Renda Fixa",
    "acoes_br": "Ações BR",
    "acoes_int": "Ações Int.",
    "fiis": "FIIs",
    "fora_alvo": "Fora do alvo",
}
_ALOCACAO_SEM_ALVO = {
    "context": (
        "Alocação-alvo ainda não definida para este workspace — a comparação da "
        "carteira atual com o alvo por classe fica disponível quando o alvo for cadastrado."
    ),
    "conclusion": (
        "Defina a alocação-alvo na tela /plano para comparar a carteira atual com o "
        "alvo e orientar o próximo aporte."
    ),
}


def _aloc_classe_label(classe: str) -> str:
    return _ALOC_CLASSE_LABELS.get(classe, classe)


def _aloc_partes_comparaveis(comparaveis: list[dict[str, Any]]) -> list[str]:
    """Uma parte "Classe atual%→alvo%" por linha da tabela (mesma ordem do card)."""
    partes: list[str] = []
    for row in comparaveis:
        atual, alvo = row.get("atual_pct") or 0, row.get("alvo_pct")
        if not atual and not alvo:
            continue
        alvo_txt = fmt_percent(alvo) if alvo is not None else "sem alvo"
        partes.append(
            f"{_aloc_classe_label(str(row.get('classe') or ''))} {fmt_percent(atual)}→{alvo_txt}"
        )
    return partes


def _aloc_conclusion(partes: list[str], derived: Mapping[str, Any], M: Mapping[str, Any]) -> str:
    frases = [", ".join(partes) + "."]
    desvio = derived.get("desvio_max_pct")
    if desvio is not None:
        frases.append(f"Maior desvio: {fmt_num(desvio)} pp.")
    next_classe = derived.get("next_aporte_classe")
    if next_classe:
        frases.append(f"Próximo aporte: {_aloc_classe_label(str(next_classe))}.")
    elif desvio is not None:
        frases.append("Carteira aderente ao alvo.")
    modo = str(M.get("aloc_rebalanceamento") or "").replace("_", " ")
    if modo:
        frases.append(f"Rebalanceamento {modo}.")
    return " ".join(frases)


def narrate_alocacao_atual_vs_alvo(M: Mapping[str, Any]) -> dict[str, str]:
    """FIN-05: lê `goals.alocacao_alvo.derived` (v2, mesma base do card) — não recalcula desvio."""
    derived = M.get("aloc_derived") or {}
    comparaveis = [r for r in derived.get("comparaveis") or [] if isinstance(r, dict)]
    partes = _aloc_partes_comparaveis(comparaveis)
    if not derived.get("has_alvo") or not partes:
        return dict(_ALOCACAO_SEM_ALVO)
    caixa_brl = (derived.get("caixa") or {}).get("valor_brl") or 0
    context = (
        f"Comparação da carteira líquida de {fmt_currency(derived.get('carteira_liquida_brl'))} "
        "com a alocação-alvo (taxonomia de 7 classes, renormalizada — mesma base da tabela). "
        f"Caixa ({fmt_currency(caixa_brl)}) e imóveis físicos "
        f"({fmt_currency(derived.get('imoveis_fisicos_brl') or 0)}) ficam fora da comparação."
    )
    return {"context": context, "conclusion": _aloc_conclusion(partes, derived, M)}
