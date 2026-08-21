"""Faixa marginal da tabela progressiva do IRPF (ADR-375 D6).

Fonte única das faixas: ``FiscalParameters.ir_brackets`` (ADR-135). O segundo
produtor vivo da mesma regra — ``cascata_triggers._ir_marginal_anual``, sobre
tabela mensal hardcoded — migra na [[A40.l37]].
"""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.types.config import IRPFBracket


class TabelaProgressivaInvalida(ValueError):
    """Tabela sobre a qual não há faixa a resolver — defeito de config, não de negócio."""


# Recusar é decisão, não rigor gratuito. A implementação anterior devolvia a
# alíquota da última faixa *excedida* quando não achava faixa aplicável, e foi
# esse "chutar algo plausível" que produziu dois testes asseverando o defeito
# como se fosse a regra (ADR-375 D7). Tabela sem faixa terminal é malformada:
# a tabela do IRPF sempre tem topo aberto.
def resolve_faixa_marginal(
    base_calculo_anual_brl_cents: int,
    faixas: tuple[IRPFBracket, ...],
) -> Decimal:
    """Alíquota da faixa que CONTÉM a base; ``upper_brl_cents`` é teto inclusivo."""
    if not faixas:
        raise TabelaProgressivaInvalida(
            "tabela progressiva vazia; esperado >=1 IRPFBracket, o último com upper_brl_cents=None"
        )
    for faixa in faixas:
        if faixa.upper_brl_cents is None:
            return faixa.aliquota_pct
        if base_calculo_anual_brl_cents <= faixa.upper_brl_cents:
            return faixa.aliquota_pct
    raise TabelaProgressivaInvalida(
        f"base {base_calculo_anual_brl_cents} cents excede o último teto "
        f"({faixas[-1].upper_brl_cents}) e a tabela não tem faixa terminal; "
        f"{len(faixas)} faixas recebidas"
    )
