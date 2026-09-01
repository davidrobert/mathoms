"""Valor impossível em item de ativo físico vira `null` declarado ([[ADR-431]]).

Imóvel e veículo não valem menos que zero. Negativo aqui não é passivo — é
defeito de **medição do valor**, com o **eixo correto**: apartamento financiado é
declarado em Bens e Direitos pelo valor pago, e o saldo devedor NÃO vai em
Dívidas e Ônus Reais. O contribuinte sequer consegue digitar negativo ali (o PGD
recusa), então o sinal não veio da declaração — é nosso.

A guarda de sinal da [[ADR-394]] §Emenda D6 opera no **balde agregado** e é
estruturalmente cega a isto: o agregado continua positivo enquanto o item
negativo for menor que a soma dos irmãos. Este módulo é o grão abaixo, onde
`null` é representável e o `Decimal` pós-soma não é ([[ADR-394]] §Emenda (b) D7,
[[ADR-346]]).

Zerar em silêncio está fora: zero é afirmação sobre o patrimônio da pessoa.
`abs()` está fora: publicaria a dívida como se fosse o valor do bem.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode

# A chave que marca o item cujo valor não foi apurado. Presente ⇒ o item fica no
# inventário (o bem existe; apagá-lo esconde patrimônio da família) e sai da soma.
CHAVE_NAO_APURADO = "valor_nao_apurado"

MOTIVO_SINAL_IMPOSSIVEL = "sinal_impossivel_em_ativo_fisico"

# As duas coleções de ativo físico do baseline consolidado. Investimento fica de
# fora de propósito: negativo lá é saldo devedor legítimo (conta margem, cheque
# especial) e a D6 já o reclassifica.
COLECOES_FISICAS: tuple[str, ...] = ("imoveis_consolidados", "veiculos_consolidados")


# O montante ofensor NÃO entra: `valor_brl` seria float em campo monetário
# ([[ADR-090]]) e a razão vai para fila de operador, onde valor real de patrimônio
# é dado sensível. Coleção + ano localizam o item; o valor está no artefato.
@dataclass(frozen=True)
class ValorImpossivelEmItemFisico:
    """Warning tipado ([[ADR-097]] D1): o valor saiu, o item ficou."""

    colecao: str
    ano: str

    def format(self) -> str:
        return (
            f"{self.colecao}[{self.ano}] trazia valor negativo e ativo físico não vale "
            "menos que zero: valor removido da soma e publicado como não apurado"
        )

    def to_review_reason(self, *, stage: str, artifact_key: str) -> ReviewReason:
        return ReviewReason(
            code=ReviewReasonCode.domain_valor_nao_apurado,
            stage=stage,
            artifact_key=artifact_key,
            document_id=None,
            offending_value=f"colecao={self.colecao} ano={self.ano} sinal=negativo",
            expected=f"{self.colecao}[].valores_31_12[{self.ano}] >= 0",
            message="Valor de ativo fisico nao apurado: sinal impossivel na origem",
        )


def _anos_impossiveis(valores: Any) -> list[str]:
    """Anos cujo valor é numérico e negativo — `None` já é não apurado (idempotência)."""
    if not isinstance(valores, dict):
        return []
    return [
        str(ano)
        for ano, v in valores.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v < 0
    ]


def sanear_item_fisico(item: dict, *, colecao: str) -> list[ValorImpossivelEmItemFisico]:
    """Troca valor negativo por `null` no item, in-place, e devolve os warnings."""
    valores = item.get("valores_31_12")
    anos = _anos_impossiveis(valores)
    if not anos:
        return []
    warnings = [ValorImpossivelEmItemFisico(colecao=colecao, ano=ano) for ano in anos]
    for ano in anos:
        valores[ano] = None
    # UNIÃO, não substituição. O saneamento roda duas vezes (item e boundary) e um
    # merge de informe entre elas pode trazer um negativo de OUTRO ano: a segunda
    # passagem só enxerga o ano novo, porque o primeiro já virou `None`. Sobrescrever
    # apagaria da declaração o ano que continua sem valor no payload.
    item[CHAVE_NAO_APURADO] = {
        "anos": sorted(set(anos) | set(anos_nao_apurados(item))),
        "motivo": MOTIVO_SINAL_IMPOSSIVEL,
    }
    _anexa_review_reasons(item, warnings, colecao=colecao)
    return warnings


# A razão nasce DENTRO do item: `harvest_review_reasons` a colhe em qualquer
# posição ([[ADR-411]] D2), e uma lista de topo montada à mão perderia o ponteiro
# para qual item da coleção está sem valor.
def _anexa_review_reasons(
    item: dict, warnings: Iterable[ValorImpossivelEmItemFisico], *, colecao: str
) -> None:
    reasons = item.setdefault("review_reasons", [])
    if not isinstance(reasons, list):
        return
    for w in warnings:
        reasons.append(
            w.to_review_reason(stage="consolidate_baseline", artifact_key=colecao).to_dict()
        )


def _sanear_colecao(baseline: dict, colecao: str) -> list[ValorImpossivelEmItemFisico]:
    itens = [i for i in (baseline.get(colecao) or []) if isinstance(i, dict)]
    return [w for item in itens for w in sanear_item_fisico(item, colecao=colecao)]


def sanear_baseline(baseline: dict) -> list[ValorImpossivelEmItemFisico]:
    """Saneia `imoveis_consolidados` + `veiculos_consolidados` do baseline consolidado."""
    return [w for colecao in COLECOES_FISICAS for w in _sanear_colecao(baseline, colecao)]


def item_nao_apurado(item: Any) -> bool:
    """Predicado de leitura para o E5 — o item declarou que o valor não foi apurado."""
    return isinstance(item, dict) and bool(item.get(CHAVE_NAO_APURADO))


def anos_nao_apurados(item: Any) -> tuple[str, ...]:
    if not item_nao_apurado(item):
        return ()
    anos = (item.get(CHAVE_NAO_APURADO) or {}).get("anos") or []
    return tuple(str(a) for a in anos if isinstance(a, (str, int)))


__all__ = [
    "CHAVE_NAO_APURADO",
    "COLECOES_FISICAS",
    "MOTIVO_SINAL_IMPOSSIVEL",
    "ValorImpossivelEmItemFisico",
    "anos_nao_apurados",
    "item_nao_apurado",
    "sanear_baseline",
    "sanear_item_fisico",
]
