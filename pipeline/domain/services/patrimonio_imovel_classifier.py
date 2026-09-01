"""Splitters de imóveis por classification (ADR-215 §1 + §6 · ADR-227 §D3)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pipeline.domain.services.patrimonio_types import (
    RealEstateValuationContext,
    imovel_property_id,
    imovel_valor,
)
from pipeline.domain.services.real_estate_valuation_resolver import resolve_valor_efetivo

# ADR-215 P3: classification de override DB-first (ADR-215 §1).
CLASSIFICATION_RESIDENCIA_PRINCIPAL = "residencia_principal"
CLASSIFICATION_USO_PESSOAL = "uso_pessoal"
CLASSIFICATION_LOCADO = "locado"
CLASSIFICATION_COMERCIAL = "comercial"
CLASSIFICATION_ESPECULACAO = "especulacao"
CLASSIFICATION_NU_PROPRIETARIO = "nu_proprietario"
CLASSIFICATION_DESCONHECIDO = "desconhecido"

# ADR-142 §Decisão + ADR-215 §6: classifications que produzem fluxo de caixa
# (entram em ``investivel_efetivo`` quando ``include_real_estate_in_if=True``).
# `uso_pessoal | especulacao | nu_proprietario | desconhecido` nunca entram —
# Perini/Cerbasi tratam patrimônio improdutivo como capital de uso, fora do
# múltiplo de IF. ADR-235: nu_proprietario tem ônus civil (usufruto de
# terceiro) — ilíquido por contrato até consolidação plena.
_CLASSIFICATIONS_GERADORAS = frozenset({CLASSIFICATION_LOCADO, CLASSIFICATION_COMERCIAL})

# [[ADR-420]] §D1 — o discriminador do numerador da concentração é
# **rebalanceabilidade**, não fluxo de caixa: *o próximo aporte move este ativo?*
# `especulacao` FICA (alocação escolhida, com retorno esperado e saída possível — renda
# zero é exatamente o custo que o KPI deve doer); `uso_pessoal` SAI (estoque de consumo,
# mesma natureza da residência principal, que já está fora dos dois lados); e
# `nu_proprietario` SAI porque é instrumento sucessório — prescrever rebalanceamento
# sobre ela é alarme que a família não pode executar ([[ADR-235]] §Decisão item 4).
#
# A lista é de EXCLUSÃO, não de inclusão, e isso é decisão: imóvel sem classificação
# nenhuma cai em `alocacao` pelo `else`, que é o lado conservador ([[ADR-420]] §D2 —
# ausência de rótulo não compra verde num KPI de risco). Escrever a lista pelo lado
# positivo poria o não-classificado FORA do numerador, invertendo o sinal.
_CLASSIFICATIONS_FORA_DA_ALOCACAO = frozenset(
    {CLASSIFICATION_USO_PESSOAL, CLASSIFICATION_NU_PROPRIETARIO}
)


def split_imoveis_with_overrides(
    *,
    titular_bens: dict,
    conjuge_bens: dict,
    overrides_by_property_id: dict[str, str],
) -> tuple[float, float]:
    """Separa cat_1 (residencia_principal) de demais imóveis (ADR-215 §1)."""
    residencia = 0.0
    imoveis_outros = 0.0
    for im in (titular_bens.get("imoveis") or []) + (conjuge_bens.get("imoveis") or []):
        if (
            classificacao_do_imovel(im, overrides_by_property_id)
            == CLASSIFICATION_RESIDENCIA_PRINCIPAL
        ):
            residencia += imovel_valor(im)
        else:
            imoveis_outros += imovel_valor(im)
    return residencia, imoveis_outros


def split_imoveis_geradores_vs_nao_geradores(
    *,
    titular_bens: dict,
    conjuge_bens: dict,
    overrides_by_property_id: dict[str, str],
) -> tuple[float, float]:
    """Separa cat_2 em geradores (locado/comercial) vs não-geradores (ADR-215 §6)."""
    geradores = 0.0
    nao_geradores = 0.0
    for im in (titular_bens.get("imoveis") or []) + (conjuge_bens.get("imoveis") or []):
        cls = classificacao_do_imovel(im, overrides_by_property_id)
        if cls == CLASSIFICATION_RESIDENCIA_PRINCIPAL:
            continue  # cat_1, fora de cat_2
        if cls in _CLASSIFICATIONS_GERADORAS:
            geradores += imovel_valor(im)
        else:
            nao_geradores += imovel_valor(im)
    return geradores, nao_geradores


def split_imoveis_alocacao_vs_fora(
    *,
    titular_bens: dict,
    conjuge_bens: dict,
    overrides_by_property_id: dict[str, str],
) -> tuple[float, float]:
    """Parte cat_2 por rebalanceabilidade ([[ADR-420]] §D1); soma == cat_2, ao centavo."""
    alocacao = 0.0
    fora = 0.0
    for im in (titular_bens.get("imoveis") or []) + (conjuge_bens.get("imoveis") or []):
        cls = classificacao_do_imovel(im, overrides_by_property_id)
        if cls == CLASSIFICATION_RESIDENCIA_PRINCIPAL:
            continue  # cat_1, fora de cat_2 nos DOIS lados
        if cls in _CLASSIFICATIONS_FORA_DA_ALOCACAO:
            fora += imovel_valor(im)
        else:
            alocacao += imovel_valor(im)
    return alocacao, fora


@dataclass(frozen=True)
class CoberturaClassificacaoImovel:
    """Quanto do valor de imóvel tem classificação conhecida ([[ADR-433]] §D3)."""

    valor_total: Decimal
    valor_desconhecido: Decimal
    n_total: int
    n_desconhecido: int

    @property
    def pct_desconhecido(self) -> float:
        """Fatia do VALOR sem classificação (percentage) — decide a supressão."""
        if not self.valor_total:
            return 0.0
        return float(self.valor_desconhecido / self.valor_total * 100)

    def to_dict(self) -> dict:
        return {
            "valor_total": str(self.valor_total),
            "valor_desconhecido": str(self.valor_desconhecido),
            "n_total": self.n_total,
            "n_desconhecido": self.n_desconhecido,
            "pct_desconhecido": self.pct_desconhecido,
        }


# `pid` ausente NÃO é "não é residência" nem "não é gerador" — é `desconhecido`, e
# os splitters acima o mandam ao `else` por construção ([[ADR-433]] §D3). A fatia
# medida aqui é o que separa *"a família não tem casa própria"* de *"não sei qual
# é a casa"*; a contagem sozinha mente, porque a residência costuma ser o maior
# item isolado — por isso o eixo é VALOR. Esta função não move soma alguma: a
# partição monetária dos splitters fica byte-idêntica, e a [[ADR-420]] §D2
# (não-classificado cai no lado conservador do KPI de risco) segue de pé.
def cobertura_classificacao_imovel(
    *,
    titular_bens: dict,
    conjuge_bens: dict,
    overrides_by_property_id: dict[str, str],
) -> CoberturaClassificacaoImovel:
    """Fatia de imóvel cuja classificação é desconhecida ([[ADR-433]] §D3)."""
    total = desconhecido = Decimal("0")
    n_total = n_desconhecido = 0
    for im in (titular_bens.get("imoveis") or []) + (conjuge_bens.get("imoveis") or []):
        valor = Decimal(str(imovel_valor(im)))
        total += valor
        n_total += 1
        if classificacao_do_imovel(im, overrides_by_property_id) == CLASSIFICATION_DESCONHECIDO:
            desconhecido += valor
            n_desconhecido += 1
    return CoberturaClassificacaoImovel(total, desconhecido, n_total, n_desconhecido)


# Produtor único do estado ternário. Os três splitters liam `overrides.get(pid)`
# cada um do seu jeito e colapsavam "sem id" com "sem rótulo" dentro do `else`;
# nomear o terceiro estado é o que permite declará-lo ([[ADR-433]] §D3).
def classificacao_do_imovel(imovel: dict, overrides_by_property_id: dict[str, str]) -> str:
    """`desconhecido` quando falta id ou rótulo; senão a classification do override."""
    pid = imovel_property_id(imovel)
    if not pid:
        return CLASSIFICATION_DESCONHECIDO
    return overrides_by_property_id.get(pid) or CLASSIFICATION_DESCONHECIDO


def sum_imoveis_geradores_liquidos(
    imoveis: list[dict],
    overrides: dict[str, str],
    valuation_context: RealEstateValuationContext,
) -> Decimal:
    """Σ max(0, valor_efetivo − saldo_devedor) por imóvel gerador (ADR-227 §D3)."""
    total = Decimal("0")
    for im in imoveis:
        pid = imovel_property_id(im)
        if overrides.get(pid) not in _CLASSIFICATIONS_GERADORAS:
            continue
        valor_irpf = Decimal(str(imovel_valor(im)))
        valor_efetivo, _, _ = resolve_valor_efetivo(pid or "", valor_irpf, valuation_context)
        saldo = valuation_context.debts_by_property.get(pid or "", Decimal("0"))
        total += max(Decimal("0"), valor_efetivo - saldo)
    return total


__all__ = [
    "CLASSIFICATION_RESIDENCIA_PRINCIPAL",
    "CLASSIFICATION_USO_PESSOAL",
    "CLASSIFICATION_LOCADO",
    "CLASSIFICATION_COMERCIAL",
    "CLASSIFICATION_ESPECULACAO",
    "CLASSIFICATION_NU_PROPRIETARIO",
    "CLASSIFICATION_DESCONHECIDO",
    "CoberturaClassificacaoImovel",
    "classificacao_do_imovel",
    "cobertura_classificacao_imovel",
    "split_imoveis_with_overrides",
    "split_imoveis_geradores_vs_nao_geradores",
    "split_imoveis_alocacao_vs_fora",
    "sum_imoveis_geradores_liquidos",
]
