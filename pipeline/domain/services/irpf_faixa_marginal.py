"""Tabela progressiva do IRPF aplicada: faixa marginal (D6) e imposto devido (D5).

Fonte única das faixas: ``FiscalParameters.ir_brackets`` (ADR-135). O segundo
produtor vivo da mesma regra — ``cascata_triggers._ir_marginal_anual``, sobre
tabela mensal hardcoded — migra na [[A40.l37]].
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pipeline.domain.types.config import IRPFBracket


class TabelaProgressivaInvalida(ValueError):
    """Tabela sobre a qual não há faixa a resolver — defeito de config, não de negócio."""


# Recusar é decisão, não rigor gratuito. A implementação anterior devolvia a
# alíquota da última faixa *excedida* quando não achava faixa aplicável, e foi
# esse "chutar algo plausível" que produziu dois testes asseverando o defeito
# como se fosse a regra (ADR-375 D7). Tabela sem faixa terminal é malformada:
# a tabela do IRPF sempre tem topo aberto.
def _faixa_que_contem(
    base_calculo_anual_brl_cents: int,
    faixas: tuple[IRPFBracket, ...],
) -> IRPFBracket:
    """Faixa que CONTÉM a base; ``upper_brl_cents`` é teto inclusivo."""
    if not faixas:
        raise TabelaProgressivaInvalida(
            "tabela progressiva vazia; esperado >=1 IRPFBracket, o último com upper_brl_cents=None"
        )
    for faixa in faixas:
        if faixa.upper_brl_cents is None:
            return faixa
        if base_calculo_anual_brl_cents <= faixa.upper_brl_cents:
            return faixa
    raise TabelaProgressivaInvalida(
        f"base {base_calculo_anual_brl_cents} cents excede o último teto "
        f"({faixas[-1].upper_brl_cents}) e a tabela não tem faixa terminal; "
        f"{len(faixas)} faixas recebidas"
    )


def resolve_faixa_marginal(
    base_calculo_anual_brl_cents: int,
    faixas: tuple[IRPFBracket, ...],
) -> Decimal:
    """Alíquota da faixa que CONTÉM a base; ``upper_brl_cents`` é teto inclusivo."""
    return _faixa_que_contem(base_calculo_anual_brl_cents, faixas).aliquota_pct


# O D5 pede `IR(base) − IR(base − aporte)`, e diferença exige a função inteira —
# alíquota sozinha só reproduz o `limite × marginal` que o D5 encerra. A parcela a
# deduzir já vive em `IRPFBracket.deducao_brl_cents`: o contrato nunca faltou.
def ir_devido_anual(
    base_calculo_anual_brl_cents: int,
    faixas: tuple[IRPFBracket, ...],
) -> int:
    """Imposto anual devido em cents: ``base × alíquota − parcela``, piso em zero."""
    faixa = _faixa_que_contem(base_calculo_anual_brl_cents, faixas)
    bruto = Decimal(base_calculo_anual_brl_cents) * faixa.aliquota_pct / Decimal("100")
    devido = int(bruto.quantize(Decimal("1"), rounding=ROUND_HALF_UP)) - faixa.deducao_brl_cents
    # Piso zero é regra da RFB, não defensividade: a parcela a deduzir excede o
    # imposto bruto no piso de cada faixa.
    return max(0, devido)
