"""Narrador do chart ``alocacao_atual_vs_alvo`` — taxonomia v2 (A37.l8 · FIN-05).

Consome ``goals.alocacao_alvo.derived`` (injetado pelo E5 via
``AlocacaoAlvoDeviationCalculator``) — a MESMA base da tabela do card React.
Não recalcula desvio; apenas narra. Labels em paridade com
``frontend/src/components/report/cards/alocacaoCardParts.tsx`` (``labelFor``).
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from pipeline.domain.services.narrativas.format_helpers import (
    fmt_currency,
    fmt_num,
    fmt_percent,
)

# Frases em paridade literal com frontend/src/components/report/cards/alocacaoSupressao.ts
# (tests/test_alocacao_supressao_copy_parity.py): o card prefere este texto ao seu.
_MEMBRO_DA_COBERTURA: dict[str, str] = {"titular": "do titular", "conjuge": "do cônjuge"}
_CAUSA_POR_SLUG: dict[str, str] = {
    "balde_negativo": "há bem com valor negativo no patrimônio",
    "valor_nao_apurado": "há bem sem valor apurado no patrimônio",
}
_CAUSA_DESCONHECIDA = "parte do patrimônio está sem dado confiável"
_PCT_NAO_CLASSIFICADO = re.compile(r"^(\d+(?:\.\d+)?)%")

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


def _juntar_com_e(partes: list[str]) -> str:
    if len(partes) <= 1:
        return "".join(partes)
    return f"{', '.join(partes[:-1])} e {partes[-1]}"


def _causa_cobertura(detalhe: str) -> str:
    membros = [m.strip() for m in detalhe.split(",") if m.strip()]
    rotulos = [_MEMBRO_DA_COBERTURA.get(m, "de um membro da família") for m in membros]
    if not rotulos:
        return _CAUSA_DESCONHECIDA
    return f"os investimentos {_juntar_com_e(list(dict.fromkeys(rotulos)))} não foram apurados"


def _causa_nao_classificado(detalhe: str) -> str:
    pct = _PCT_NAO_CLASSIFICADO.match(detalhe.strip())
    if not pct:
        return "parte da carteira está sem classe definida"
    return f"{fmt_percent(float(pct.group(1)))} da carteira está sem classe definida"


def _causa_da_supressao(parte: str) -> str:
    slug, _, detalhe = (p.strip() for p in parte.partition(":"))
    if slug == "cobertura_incompleta":
        return _causa_cobertura(detalhe)
    if slug == "nao_classificado":
        return _causa_nao_classificado(detalhe)
    return _CAUSA_POR_SLUG.get(slug, _CAUSA_DESCONHECIDA)


def _frase_da_supressao(motivo: str) -> str:
    """`motivo_supressao` é de máquina (`<slug>: <detalhe>`, unidos por "; ")."""
    causas = [_causa_da_supressao(p) for p in motivo.split(";") if p.strip()]
    porque = _juntar_com_e(list(dict.fromkeys(causas))) or _CAUSA_DESCONHECIDA
    return f"Próximo aporte não indicado: {porque}."


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


def _aloc_frase_aporte(derived: Mapping[str, Any], desvio: Any) -> str | None:
    # `next_aporte_classe` vazio tem DUAS causas e elas dizem o oposto: carteira
    # alinhada, ou prescrição suprimida por ignorância ([[ADR-400]] §D6). Ler as
    # duas como "aderente" publica elogio sobre carteira desalinhada — medido em
    # [[A40.l82]]: "Maior desvio: 30,3 pp. Carteira aderente ao alvo."
    motivo = derived.get("motivo_supressao")
    if motivo:
        return _frase_da_supressao(str(motivo))
    next_classe = derived.get("next_aporte_classe")
    if next_classe:
        return f"Próximo aporte: {_aloc_classe_label(str(next_classe))}."
    return "Carteira aderente ao alvo." if desvio is not None else None


def _aloc_conclusion(partes: list[str], derived: Mapping[str, Any], M: Mapping[str, Any]) -> str:
    frases = [", ".join(partes) + "."]
    desvio = derived.get("desvio_max_pct")
    if desvio is not None:
        frases.append(f"Maior desvio: {fmt_num(desvio)} pp.")
    aporte = _aloc_frase_aporte(derived, desvio)
    if aporte:
        frases.append(aporte)
    modo = str(M.get("aloc_rebalanceamento") or "").replace("_", " ")
    if modo and not derived.get("motivo_supressao"):
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
