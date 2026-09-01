"""Imobilização patrimonial ([[ADR-420]] §D3 · financia a [[ADR-235]] §Decisão item 4): quanto do patrimônio líquido está preso em imóvel — residência (cat_1) + imóveis de investimento (cat_2) sobre `patrimonio_liquido`. SEM alvo, limiar, operador, componente de score, gatilho ou card: é órfã de domínio declarada, e existe porque estreitar o numerador da concentração sozinho apagaria a nu-propriedade de toda superfície de risco — trocaria falso alarme por silêncio, e numa família com sucessão ativa o silêncio é o erro mais caro dos dois."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from pipeline.domain.services.bases_financeiras import BaseFinanceira

# O nome recusa "concentração" de propósito ([[ADR-420]] §D3): a [[ADR-235]] chamava
# este número de "concentração imobiliária total", e dois `concentracao_*` com bases
# distintas é o RV8-02 recriado um nível acima — o defeito que a [[A40.l80]] gastou 11
# PRs matando. Honra-se a intenção, recusa-se o rótulo.
CHAVE_DA_RAZAO = "imobilizacao_patrimonial_pct"

#: Termos de `patrimonio` que o numerador soma, DECLARADOS ([[ADR-420]] §D5): razão nova
#: que nasce sem numerador nomeável repete no dia um o C14 da [[A40.l80]] que esta mesma
#: lane acabou de fechar na concentração. São dois, por isso a declaração é lista.
TERMOS_DO_NUMERADOR: tuple[str, ...] = ("residencia", "imoveis_investimento")

BASE = BaseFinanceira.patrimonio_liquido


# `Decimal`, não `float`: o identificador nomeia dinheiro (ADR-090), e é a mesma
# convenção do vizinho `bases_financeiras._valor_da_base`. O `float` só aparece no
# retorno da razão, que é percentual — não é dinheiro.
def _valor_monetario(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except (TypeError, ValueError, ArithmeticError):
        return Decimal("0")


def _valor_da_base(patrimonio: Mapping[str, Any]) -> Decimal:
    """Lê a base que DECLARA, nunca o `liquido` top-level — é o padrão do #1782."""
    declarada = (patrimonio.get("bases") or {}).get(BASE.value) or {}
    return _valor_monetario(declarada.get("valor_brl"))


def compute_imobilizacao_patrimonial_pct(patrimonio: Mapping[str, Any]) -> float | None:
    """``(residencia + cat_2) / patrimonio_liquido × 100``; ``None`` com PL ≤ 0."""
    base = _valor_da_base(patrimonio)
    if base <= 0:
        return None
    imobilizado = sum(
        (_valor_monetario(patrimonio.get(termo)) for termo in TERMOS_DO_NUMERADOR),
        Decimal("0"),
    )
    return round(float(imobilizado / base * 100), 2)
