"""Frase de supressão da indicação de aporte ([[ADR-394]] §Emenda · [[ADR-400]]).

``derived.motivo_supressao`` é de máquina: ``<slug>: <detalhe>``, causas unidas por
``"; "`` (``_compor_motivo`` em ``alocacao_alvo_deviation``). A frase é a mesma do
card React (``frontend/src/components/report/cards/alocacaoSupressao.ts``): as duas
pontas leem ``tests/fixtures/narrativas/alocacao_supressao_frases.json``.
"""

from __future__ import annotations

import re

# "Próximo aporte não indicado" lia como contraindicação — a família pausaria o
# aporte, e o que o produtor retira é só a CLASSE dele.
_SEM_INDICACAO = "Não indicamos a classe do próximo aporte"
_MEMBRO_DA_COBERTURA: dict[str, str] = {"titular": "do titular", "conjuge": "do cônjuge"}
_MEMBRO_SEM_PAPEL = "de um membro da família"
# Sem número no `nao_classificado`: o percentual do produtor é sobre a carteira
# financeira COM caixa, e o da tabela do card é sem caixa.
_CAUSA_FIXA: dict[str, str] = {
    "nao_classificado": "parte da carteira está sem classe definida",
    "balde_negativo": "há bem com valor negativo registrado no patrimônio",
}
_CAUSA_DESCONHECIDA = "parte do patrimônio está sem valor confiável"
_ITENS = re.compile(r"^(\d+)")


def _juntar_com_e(partes: list[str]) -> str:
    if len(partes) <= 1:
        return "".join(partes)
    return f"{', '.join(partes[:-1])} e {partes[-1]}"


def _causa_cobertura(detalhe: str) -> str:
    membros = [m.strip() for m in detalhe.split(",") if m.strip()]
    rotulos = [_MEMBRO_DA_COBERTURA.get(m, _MEMBRO_SEM_PAPEL) for m in membros]
    unicos = list(dict.fromkeys(rotulos or [_MEMBRO_SEM_PAPEL]))
    return f"os investimentos {_juntar_com_e(unicos)} não foram apurados"


def _causa_valor_nao_apurado(detalhe: str) -> str:
    itens = _ITENS.match(detalhe)
    n = int(itens.group(1)) if itens else 0
    if n == 1:
        return "há um bem sem valor apurado"
    return f"há {n} bens sem valor apurado" if n else "há bem sem valor apurado"


def _causa(parte: str) -> str:
    slug, _, detalhe = (p.strip() for p in parte.partition(":"))
    if slug == "cobertura_incompleta":
        return _causa_cobertura(detalhe)
    if slug == "valor_nao_apurado":
        return _causa_valor_nao_apurado(detalhe)
    return _CAUSA_FIXA.get(slug, _CAUSA_DESCONHECIDA)


def frase_da_supressao(motivo: str) -> str:
    """Uma causa vira "…: causa."; duas ou mais, uma frase por causa."""
    causas = [_causa(p) for p in motivo.split(";") if p.strip()]
    frases = list(dict.fromkeys(causas or [_CAUSA_DESCONHECIDA]))
    if len(frases) == 1:
        return f"{_SEM_INDICACAO}: {frases[0]}."
    return " ".join([f"{_SEM_INDICACAO}.", *(f"{f[0].upper()}{f[1:]}." for f in frases)])
