"""Formatação da probabilidade do Monte Carlo (ADR-237 · A40.l25)."""
# Módulo-FOLHA de propósito: só `math`, nenhum import de `pipeline.*`. O gate de
# paridade (`dev/check_probabilidade_parity.py`) o carrega por caminho, sem
# executar `pipeline/domain/services/__init__.py` — que tem 34 imports e puxa
# `pipeline.llm` → `pydantic`, ausente do ambiente do job de Lint. Espelha o
# lado TS, que também vive em módulo próprio (`utils/probabilidade.ts`).

from __future__ import annotations

import math


def _meio_para_cima(pp: float) -> int:
    """Ponto percentual arredondado meio-para-cima."""
    return math.floor(pp + 0.5)


# A divergência com o TS era UNILATERAL e o lado errado era este: `round()` do
# Python é meio-para-PAR, enquanto `.toFixed(0)` do JS é meio-para-cima. Medido
# no domínio real do estimador (`k/50000`, ADR-360), os dois discordavam em 45
# dos 50 001 desfechos — o parágrafo dizia "2%" e a legenda do cone dizia "3%"
# para o MESMO campo, no mesmo relatório. Meio-para-cima é o que o leitor espera
# de porcentagem, então o narrador é que se move.
def fmt_probabilidade(prob: float) -> str:
    """Paridade com `formatProbability` do S7: guards <1% / >99%."""
    if prob <= 0:
        return "0%"
    if prob >= 1:
        return "100%"
    if prob < 0.01:
        return "<1%"
    if prob > 0.99:
        return ">99%"
    return f"{_meio_para_cima(prob * 100)}%"
