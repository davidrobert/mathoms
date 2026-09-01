"""O ano-base de um item afirma foto em **31/12 fechado** ([[A40.l114]]).

`valores_31_12[ano]` e `saldo_31_12[ano]` não são um rótulo qualquer: eles afirmam
a posição no dia 31/12 daquele ano. Um ano ainda em curso não tem 31/12, logo a
chave não pode alcançá-lo — em 2026-09-01 o teto é 2025.

Nada enforçava isso. Uma tela de posição do Itaú capturada em **29/03/2026** entrou
como `valores_31_12["2026"]`, e o `max()` sobre os itens levou o eixo do domicílio
inteiro para um 31/12 que não ocorreu. A regra já existia como default espalhado
(`consolidate_baseline.py` usa `date.today().year - 1` em dois pontos); o que
faltava era alguém enforçá-la.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger("mathoms.pipeline.patrimonio")


def ultimo_ano_31_12_fechado(hoje: date | None = None) -> int:
    """Ano do último 31/12 que efetivamente ocorreu."""
    ref = hoje or date.today()
    return ref.year if (ref.month, ref.day) == (12, 31) else ref.year - 1


@dataclass(frozen=True)
class AnoNaoFechadoWarning:
    """Ano-base afirma um 31/12 que ainda não ocorreu."""

    anos_recusados: tuple[int, ...]
    teto: int

    def format(self) -> str:
        recusados = ", ".join(str(a) for a in self.anos_recusados)
        return (
            f"ano-base recusado: {recusados} afirma(m) 31/12 não fechado "
            f"(último fechado: {self.teto}); fora do eixo de resolução"
        )


# Message literal + `extra=` ([[ADR-273]]): o texto do warning tipado carrega ano,
# que não é PII, mas a denylist redige por CHAVE — interpolar aqui abriria o
# precedente que o gate fecha.
def anos_fechados(anos: set[int], teto: int) -> set[int]:
    """Descarta anos que afirmam um 31/12 ainda não ocorrido; loga o que recusou."""
    recusados = tuple(sorted(a for a in anos if a > teto))
    if recusados:
        logger.warning(
            "patrimonio_ano_nao_fechado",
            extra={
                "anos_recusados": list(recusados),
                "teto": teto,
                "detalhe": AnoNaoFechadoWarning(recusados, teto).format(),
            },
        )
    return {a for a in anos if a <= teto}
