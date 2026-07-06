"""Numerador da reserva de emergência — ``reserva_liquida_disponivel`` (A28.l1).

Filtro estrito de liquidez/risco sobre os itens de investimento por membro
(FORMULAS.md §Reserva): só buckets ``Caixa`` + ``Renda Fixa`` (ADR-193)
com liquidez diária entram; ações/FII/exterior/cripto/fundos/previdência
ficam fora. Caixa E3 é split por tipo (BRL vs moeda estrangeira); residual
IRPF não-verificável fica fora e é exposto como ``caixa_nao_classificado``.

Interno em ``Decimal`` (ADR-090).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from pipeline.domain.services.asset_classifier import classify_asset
from pipeline.domain.services.patrimonio_types import (
    MemberIdentity,
    get_bens,
    investimento_valor,
    safe_float,
)

_ZERO = Decimal("0")
_CENT = Decimal("0.01")

# Buckets ADR-193 elegíveis como reserva (liquidez D+0/D+1, baixo risco).
_LIQUID_BUCKETS = frozenset({"Caixa", "Renda Fixa"})
# Renda fixa SEM liquidez diária (crédito securitizado / mercado secundário).
_ILLIQUID_RF_RE = re.compile(r"debentur|\bcra\b|\bcri\b")


def _dec(value: object) -> Decimal:
    return Decimal(str(safe_float(value)))


@dataclass(frozen=True)
class LiquidezMembro:
    """Parcela líquida vs excluída dos investimentos de um membro."""

    valor_liquido: Decimal
    valor_excluido: Decimal
    fonte: str  # "posicoes" | "irpf" | "agregado_sem_itens"


@dataclass(frozen=True)
class ReservaLiquida:
    """Numerador decomposto: membros + caixa E3 por tipo + residual excluído."""

    por_membro: dict[str, LiquidezMembro]
    caixa_brl: Decimal
    caixa_me: Decimal
    caixa_nao_classificado: Decimal

    def componentes(self, *, incluir_caixa_me: bool, solo: bool) -> dict[str, Decimal]:
        """Componentes quantizados a cents — ``total_liquido == Σ componentes``
        exato por construção (invariante check_lineage_sum, ADR-279)."""
        out = {
            f"investimentos_{key}": m.valor_liquido.quantize(_CENT)
            for key, m in self.por_membro.items()
        }
        if solo:
            out.setdefault("investimentos_", _ZERO)
        out["caixa"] = self.caixa_brl.quantize(_CENT)
        out["caixa_moeda_estrangeira"] = (
            self.caixa_me.quantize(_CENT) if incluir_caixa_me else _ZERO
        )
        return out

    def investimentos_nao_liquidos(self) -> Decimal:
        return sum((m.valor_excluido for m in self.por_membro.values()), _ZERO)


def build_reserva_liquida(
    patrimonio: dict,
    investimentos_atuais: dict | None,
    bens_por_membro: Mapping[str, dict] | None,
    *,
    identity: MemberIdentity,
    keywords: Mapping[str, tuple[str, ...]] | None = None,
) -> ReservaLiquida:
    """Aplica o filtro de liquidez por membro e decompõe o caixa E3 por tipo."""
    por_membro = _liquidez_por_membro(
        patrimonio, investimentos_atuais, bens_por_membro, identity, keywords
    )
    return _com_caixa_por_tipo(patrimonio, por_membro)


def _liquidez_por_membro(
    patrimonio: dict,
    investimentos_atuais: dict | None,
    bens_por_membro: Mapping[str, dict] | None,
    identity: MemberIdentity,
    keywords: Mapping[str, tuple[str, ...]] | None,
) -> dict[str, LiquidezMembro]:
    return {
        member_key: _liquidez_membro(
            member_key,
            identity=identity,
            keywords=keywords,
            aggregate=_dec(patrimonio.get(f"investimentos_{member_key}", 0)),
            investimentos_atuais=investimentos_atuais,
            bens=(bens_por_membro or {}).get(member_key),
        )
        for member_key in _member_keys(identity)
    }


def _com_caixa_por_tipo(patrimonio: dict, por_membro: dict[str, LiquidezMembro]) -> ReservaLiquida:
    caixa_brl, caixa_me = _split_caixa_detalhes(patrimonio.get("caixa_detalhes") or [])
    nao_classificado = _dec(patrimonio.get("caixa_moeda_estrangeira", 0)) - caixa_brl - caixa_me
    return ReservaLiquida(
        por_membro=por_membro,
        caixa_brl=caixa_brl,
        caixa_me=caixa_me,
        caixa_nao_classificado=max(_ZERO, nao_classificado),
    )


def _member_keys(identity: MemberIdentity) -> list[str]:
    keys = [identity.titular_key]
    if identity.conjuge_key:
        keys.append(identity.conjuge_key)
    return keys


def _liquidez_membro(
    member_key: str,
    *,
    identity: MemberIdentity,
    keywords: Mapping[str, tuple[str, ...]] | None,
    aggregate: Decimal,
    investimentos_atuais: dict | None,
    bens: dict | None,
) -> LiquidezMembro:
    items = _positions_for_member(member_key, identity, investimentos_atuais)
    fonte = "posicoes"
    if not items and bens is not None:
        items, fonte = _irpf_items(get_bens(bens)), "irpf"
    if not items:
        # Sem item-level data (fixtures antigas/aggregate puro): mantém o
        # agregado com flag — melhor superestimar rotulado que zerar cego.
        return LiquidezMembro(aggregate, _ZERO, "agregado_sem_itens")
    liquido, excluido = _filter_liquid(items, keywords)
    return LiquidezMembro(liquido, excluido, fonte)


def _filter_liquid(
    items: list[dict], keywords: Mapping[str, tuple[str, ...]] | None
) -> tuple[Decimal, Decimal]:
    liquido = _ZERO
    excluido = _ZERO
    kw = dict(keywords) if keywords else None
    for item in items:
        valor = _item_valor(item)
        if valor <= _ZERO:
            continue
        if _is_liquid_item(item, kw):
            liquido += valor
        else:
            excluido += valor
    return liquido, excluido


def _positions_for_member(
    member_key: str, identity: MemberIdentity, investimentos_atuais: dict | None
) -> list[dict]:
    """Posições atuais do membro; sem membro atribuído → titular (convenção legado)."""
    dados = (investimentos_atuais or {}).get("dados") or []
    out: list[dict] = []
    for pos in dados:
        if not isinstance(pos, dict):
            continue
        membro = str(pos.get("membro") or "").lower()
        if member_key and member_key in membro:
            out.append(pos)
        elif not membro and member_key == identity.titular_key:
            out.append(pos)
    return out


def _irpf_items(bens: dict) -> list[dict]:
    """Itens IRPF do membro: investimentos + contas bancárias (lista)."""
    items = [inv for inv in (bens.get("investimentos") or []) if isinstance(inv, dict)]
    contas = bens.get("contas_bancarias")
    if isinstance(contas, list):
        items.extend(c for c in contas if isinstance(c, dict))
    elif contas is not None and safe_float(contas) > 0:
        # Escalar consolidado (formato v1.5) — semanticamente Caixa.
        items.append({"tipo": "conta corrente", "descricao": "contas bancárias", "valor": contas})
    return items


def _item_valor(item: dict) -> Decimal:
    for key in ("valor_atual", "valor_total", "valor_brl"):
        v = item.get(key)
        if v is not None:
            return _dec(v)
    return _dec(investimento_valor(item))


def _is_liquid_item(item: dict, keywords: dict[str, tuple[str, ...]] | None) -> bool:
    tipo = str(item.get("tipo") or "")
    descricao = str(item.get("descricao") or item.get("nome") or item.get("description") or "")
    instituicao = str(item.get("instituicao") or "")
    bucket = classify_asset(tipo, descricao, instituicao, keywords=keywords)
    if bucket not in _LIQUID_BUCKETS:
        return False
    haystack = f"{tipo} {descricao} {instituicao}".lower()
    return not _ILLIQUID_RF_RE.search(haystack)


def _split_caixa_detalhes(detalhes: list) -> tuple[Decimal, Decimal]:
    """Separa saldos E3 por tipo: ``caixa`` (BRL) vs ``moeda_estrangeira``."""
    caixa = _ZERO
    moeda_estrangeira = _ZERO
    for det in detalhes:
        if not isinstance(det, dict):
            continue
        valor = _dec(det.get("valor_brl", 0))
        if det.get("tipo") == "moeda_estrangeira":
            moeda_estrangeira += valor
        else:
            caixa += valor
    return caixa, moeda_estrangeira


__all__ = ["LiquidezMembro", "ReservaLiquida", "build_reserva_liquida"]
