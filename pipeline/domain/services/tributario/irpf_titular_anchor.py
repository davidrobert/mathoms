"""Âncora de declarante para a base da S8 (A40.l65 §Escopo 2).

O artefato do IRPF é **por declarante** e não sabe quem é o titular da família:
`natureza` só distingue `titular` de `dependente_titular`, e **cada cônjuge é
`titular` na própria declaração**. A resolução vem de `family_members`.

A unidade da dedução é a **declaração**, não o CPF — declaração conjunta inclui os
rendimentos dos dependentes, e cônjuge-como-dependente é o caso brasileiro comum.
Por isso o titular é procurado nos dois lugares (decisão do `financial-planner`,
co-design 2026-08-24).
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class AncoraTitular(str, Enum):
    resolvida = "resolvida"
    # Sem CPF de titular cadastrado E mais de uma declaração: escolher seria
    # cara-ou-coroa sobre de quem é a renda.
    ambigua = "ambigua"
    # Titular identificável, sem declaração no ano ELEITO. Causa diferente de
    # cadastro faltando — e a ação do usuário também é diferente (nenhuma).
    sem_declaracao_no_ano = "sem_declaracao_no_ano"


def sufixo_cpf(cpf: str | None) -> str | None:
    """A máscara do artefato preserva 2 dígitos; é tudo que dá para casar."""
    digitos = "".join(c for c in (cpf or "") if c.isdigit())
    return digitos[-2:] if len(digitos) >= 2 else None


def _pessoa_casa(pessoa: Any, sufixo: str) -> bool:
    if not isinstance(pessoa, dict):
        return False
    return sufixo_cpf(pessoa.get("cpf_masked")) == sufixo


def declaracao_e_do_titular(payload: dict, sufixo: str) -> bool:
    """Titular como contribuinte OU como dependente da declaração conjunta."""
    if _pessoa_casa(payload.get("contribuinte"), sufixo):
        return True
    dependentes = payload.get("dependentes") or []
    return any(_pessoa_casa(d, sufixo) for d in dependentes)


def escolher_declaracao_do_titular(
    declaracoes: list[dict], cpf_titular: str | None
) -> tuple[dict | None, AncoraTitular]:
    """Declaração do titular entre as do ano eleito, mais recente primeiro."""
    sufixo = sufixo_cpf(cpf_titular)
    if sufixo is None:
        # Sem cadastro NÃO é sempre ambiguidade. O defeito que esta âncora fecha
        # — "a base vira a declaração de quem foi processado por último" — exige
        # DUAS. Com uma só não há quem confundir, e suprimir aqui tiraria a base
        # de todo workspace de declarante único para prevenir um erro impossível.
        if len(declaracoes) == 1:
            return declaracoes[0], AncoraTitular.resolvida
        return None, AncoraTitular.ambigua
    do_titular = [d for d in declaracoes if declaracao_e_do_titular(d, sufixo)]
    if not do_titular:
        return None, AncoraTitular.sem_declaracao_no_ano
    return do_titular[0], AncoraTitular.resolvida
