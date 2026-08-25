"""Produtor único do eixo de posições atuais ([[ADR-412]] §D3).

[[ADR-410]] resolveu o eixo A (baseline consolidado, `bens[]`). Este módulo é o
eixo B — `investimentos_atuais["dados"]` + `["total_por_membro"]` — cujo resolver
estava duplicado em `reserva_liquidez._positions_for_member` com convenção
INVERTIDA: lá, posição sem membro ia para o titular. A regra canônica sempre foi
a de `_papel_da_chave`; o que faltava era grão e injeção.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable, Mapping

from pipeline.domain.services.bases_financeiras import PapelMembro, chave_de_componente
from pipeline.domain.services.member_key_matcher import matches_member_key

_ZERO = Decimal("0")


def papel_da_chave(chave: str, *, titular_key: str, conjuge_key: str) -> PapelMembro:
    """Papel de uma chave de membro; o vazio é órfão, **nunca** titular."""
    if not chave:
        return PapelMembro.sem_dono
    if titular_key and matches_member_key(titular_key, chave):
        return PapelMembro.titular
    if conjuge_key and matches_member_key(conjuge_key, chave):
        return PapelMembro.conjuge
    return PapelMembro.sem_dono


@dataclass(frozen=True)
class BaldeDoPapel:
    """O que o eixo B viu para um papel, nos dois grãos."""

    papel: PapelMembro
    total_brl: Decimal
    posicoes: tuple[dict, ...]
    chaves: frozenset[str]

    @property
    def soma_itens_brl(self) -> Decimal:
        return sum((_valor_da_posicao(p) for p in self.posicoes), _ZERO)

    # O agregado NÃO é derivável dos itens: `investments_consolidator` usa
    # `total_fonte` quando existe e só cai para a soma das posições na ausência.
    # Derivar `total_brl` de `sum(posicoes)` descartaria em silêncio o resíduo
    # não-detalhado — este campo o NOMEIA em vez de escondê-lo.
    @property
    def divergencia_item_vs_agregado(self) -> Decimal:
        return self.total_brl - self.soma_itens_brl

    @property
    def atribuido(self) -> bool:
        return bool(self.chaves)

    @property
    def chave_publicada(self) -> str:
        return chave_de_componente(self.papel)


@dataclass(frozen=True)
class CarteiraPorPapel:
    """Eixo B particionado; **sempre** com os três papéis, mesmo vazios."""

    baldes: Mapping[PapelMembro, BaldeDoPapel]

    def __getitem__(self, papel: PapelMembro) -> BaldeDoPapel:
        return self.baldes[papel]

    @property
    def divergencia_total(self) -> Decimal:
        return sum((b.divergencia_item_vs_agregado for b in self.baldes.values()), _ZERO)

    @property
    def total_brl(self) -> Decimal:
        return sum((b.total_brl for b in self.baldes.values()), _ZERO)

    @classmethod
    def vazia(cls) -> "CarteiraPorPapel":
        """Sem eixo B — o chamador cai para o fallback IRPF, papel a papel."""
        return cls(baldes={p: BaldeDoPapel(p, _ZERO, (), frozenset()) for p in PapelMembro})


def build_carteira_por_papel(
    investimentos_atuais: dict | None, *, titular_key: str, conjuge_key: str
) -> CarteiraPorPapel:
    """Particiona `dados` + `total_por_membro` nos três papéis, uma vez por run."""
    dados = (investimentos_atuais or {}).get("dados") or []
    totais = (investimentos_atuais or {}).get("total_por_membro") or {}
    if not dados and not totais:
        return CarteiraPorPapel.vazia()

    posicoes: dict[PapelMembro, list[dict]] = {p: [] for p in PapelMembro}
    for pos in dados:
        if isinstance(pos, dict):
            papel = papel_da_chave(
                str(pos.get("membro") or "").lower(),
                titular_key=titular_key,
                conjuge_key=conjuge_key,
            )
            posicoes[papel].append(pos)

    somas, chaves = _agregado_por_papel(totais, titular_key=titular_key, conjuge_key=conjuge_key)
    return CarteiraPorPapel(
        baldes={
            papel: BaldeDoPapel(
                papel=papel,
                total_brl=somas[papel],
                posicoes=tuple(posicoes[papel]),
                chaves=frozenset(chaves[papel]),
            )
            for papel in PapelMembro
        }
    )


def _agregado_por_papel(
    totais: Mapping[str, Any], *, titular_key: str, conjuge_key: str
) -> tuple[dict[PapelMembro, Decimal], dict[PapelMembro, set[str]]]:
    somas = {p: _ZERO for p in PapelMembro}
    chaves: dict[PapelMembro, set[str]] = {p: set() for p in PapelMembro}
    for chave, valor in (totais or {}).items():
        papel = papel_da_chave(str(chave).lower(), titular_key=titular_key, conjuge_key=conjuge_key)
        somas[papel] += _to_decimal(valor)
        chaves[papel].add(str(chave))
    return somas, chaves


def _valor_da_posicao(pos: Mapping[str, Any]) -> Decimal:
    for campo in ("valor", "valor_brl", "saldo_brl", "valor_atual"):
        if pos.get(campo) is not None:
            return _to_decimal(pos[campo])
    return _ZERO


def _to_decimal(valor: Any) -> Decimal:
    if isinstance(valor, Mapping):
        return _to_decimal(valor.get("valor") or valor.get("valor_brl") or 0)
    if isinstance(valor, Decimal):
        return valor
    try:
        return Decimal(str(valor))
    except (ValueError, TypeError, ArithmeticError):
        return _ZERO


__all__: Iterable[str] = (
    "BaldeDoPapel",
    "CarteiraPorPapel",
    "build_carteira_por_papel",
    "papel_da_chave",
)
