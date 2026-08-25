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
from pipeline.domain.services.bases_financeiras import PapelMembro, chave_de_componente
from pipeline.domain.services.carteira_por_papel import CarteiraPorPapel
from pipeline.domain.services.patrimonio_types import (
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


# O eixo B (posições atuais) NÃO substitui o eixo IRPF: no dogfood o balde do
# cônjuge vem inteiramente do braço IRPF, e tratar a carteira como resposta
# completa o zeraria — com a identidade de conservação fechando mesmo assim,
# porque os dois lados cairiam juntos. `sem_dono` não tem campo aqui de
# propósito: não há pessoa cujo IRPF consultar.
@dataclass(frozen=True)
class FallbackIrpfPorPapel:
    """Bens IRPF por papel; `sem_dono` nunca tem fallback."""

    titular: dict | None = None
    conjuge: dict | None = None

    def para(self, papel: PapelMembro) -> dict | None:
        return {PapelMembro.titular: self.titular, PapelMembro.conjuge: self.conjuge}.get(papel)


@dataclass(frozen=True)
class ReservaLiquida:
    """Numerador decomposto: papéis + caixa E3 por tipo + residual excluído."""

    por_papel: dict[PapelMembro, LiquidezMembro]
    caixa_brl: Decimal
    caixa_me: Decimal
    caixa_nao_classificado: Decimal

    # Sempre os TRÊS papéis: shape estável dispensa `.get()` no leitor, e o
    # `solo` sumiu porque um balde ausente e um balde zero diziam a mesma coisa
    # por caminhos diferentes. `chave_de_componente`, nunca f-string ([[ADR-412]]
    # §Emenda E7): `f"investimentos_{PapelMembro.sem_dono}"` vira
    # `investimentos_PapelMembro.sem_dono` e o `$def` fechado rejeita os três.
    def componentes(self, *, incluir_caixa_me: bool) -> dict[str, Decimal]:
        """Componentes quantizados a cents — ``total_liquido == Σ componentes``
        exato por construção (invariante check_lineage_sum, ADR-279)."""
        out = {
            chave_de_componente(papel): self.por_papel[papel].valor_liquido.quantize(_CENT)
            for papel in PapelMembro
        }
        out["caixa"] = self.caixa_brl.quantize(_CENT)
        out["caixa_moeda_estrangeira"] = (
            self.caixa_me.quantize(_CENT) if incluir_caixa_me else _ZERO
        )
        return out

    def investimentos_nao_liquidos(self) -> Decimal:
        return sum((m.valor_excluido for m in self.por_papel.values()), _ZERO)


def build_reserva_liquida(
    patrimonio: dict,
    carteira: CarteiraPorPapel,
    fallback_irpf: FallbackIrpfPorPapel,
    *,
    keywords: Mapping[str, tuple[str, ...]] | None = None,
) -> ReservaLiquida:
    """Aplica o filtro de liquidez por papel e decompõe o caixa E3 por tipo."""
    por_papel = _liquidez_por_papel(patrimonio, carteira, fallback_irpf, keywords)
    return _com_caixa_por_tipo(patrimonio, por_papel)


# Balde `None` = membro não apurado ([[ADR-394]] §Emenda (b) D7). A reserva não
# conta dinheiro que ninguém mediu, então ele entra como zero — `_dec` já o faz, e
# um ramo explícito seria cerimônia que nenhuma mutação mata. O contrato "None
# conta zero" é travado por teste; a ressalva no KPI é follow-up da [[A40.l69]].
def _com_caixa_por_tipo(
    patrimonio: dict, por_papel: dict[PapelMembro, LiquidezMembro]
) -> ReservaLiquida:
    caixa_brl, caixa_me = _split_caixa_detalhes(patrimonio.get("caixa_detalhes") or [])
    # CTO-02: caixa TOTAL menos as parcelas classificadas (BRL + ME) = resíduo
    # não classificado. Lê `caixa_total_brl` com fallback ao alias legado.
    caixa_total = _dec(
        patrimonio.get("caixa_total_brl", patrimonio.get("caixa_moeda_estrangeira", 0))
    )
    nao_classificado = caixa_total - caixa_brl - caixa_me
    return ReservaLiquida(
        por_papel=por_papel,
        caixa_brl=caixa_brl,
        caixa_me=caixa_me,
        caixa_nao_classificado=max(_ZERO, nao_classificado),
    )


def _liquidez_por_papel(
    patrimonio: dict,
    carteira: CarteiraPorPapel,
    fallback_irpf: FallbackIrpfPorPapel,
    keywords: Mapping[str, tuple[str, ...]] | None,
) -> dict[PapelMembro, LiquidezMembro]:
    return {
        papel: _liquidez_do_papel(
            papel,
            keywords=keywords,
            posicoes=list(carteira[papel].posicoes),
            bens=fallback_irpf.para(papel),
            aggregate=_dec(patrimonio.get(chave_de_componente(papel), 0)),
        )
        for papel in PapelMembro
    }


def _liquidez_do_papel(
    papel: PapelMembro,
    *,
    keywords: Mapping[str, tuple[str, ...]] | None,
    posicoes: list[dict],
    bens: dict | None,
    aggregate: Decimal,
) -> LiquidezMembro:
    items, fonte = posicoes, "posicoes"
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
    bucket = classify_asset(tipo, descricao, keywords=keywords)
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


__all__ = [
    "FallbackIrpfPorPapel",
    "LiquidezMembro",
    "ReservaLiquida",
    "build_reserva_liquida",
]
