"""População do numerador de ``total_pontuais*`` ([[A40.l101]] §Escapes).

O denominador roda sobre a janela FECHADA e sobre o REALIZADO; o numerador não
tinha nenhum dos dois limites. Populações diferentes do mesmo par publicam 6,0
ou 12,0 para o mesmo gasto pontual.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.consumo_consciente_calculator import (  # noqa: E402
    ConsumoConscienteCalculator,
)


def _despesas(**categorias_to_txns) -> dict:
    return {"dados": categorias_to_txns}


def _txn(data: str, descricao: str, quantia: Decimal) -> dict:
    """``Decimal`` no call-site e ``float`` no dict: o payload E4 é JSON, mas o
    teste não escreve dinheiro como literal float ([[ADR-090]])."""
    return {"data": data, "descricao": descricao, "valor": float(quantia), "banco": "Itaú"}


def _fluxo_com_janela(*, periodo: str, data_corte: str | None = None) -> dict:
    fluxo = {
        "janela_12m": {
            "receita_recorrente_mensal": 20_000.0,
            "despesa_mensal_media": 15_000.0,
            "despesa_consumo": 15_000.0 * 12,
            "n_meses": 12,
            "periodo": periodo,
        }
    }
    if data_corte:
        fluxo["data_corte"] = data_corte
    return fluxo


class TestPopulacaoDoNumerador:
    """O denominador roda sobre a janela FECHADA e sobre o REALIZADO; o numerador
    ia de `mes_inicio` a +∞ e sobre realizado+provisionado. Populações diferentes
    do mesmo par publicam 6,0 ou 12,0 para o mesmo gasto pontual."""

    _JANELA = "2025-04 a 2026-03"

    def test_posterior_ao_fim_da_janela_nao_entra_no_numerador(self):
        r = ConsumoConscienteCalculator().calculate(
            _fluxo_com_janela(periodo=self._JANELA),
            _despesas(
                lazer=[
                    _txn("2025-12-10", "DENTRO", Decimal("30000")),
                    _txn("2026-06-10", "DEPOIS DO FIM", Decimal("60000")),
                ]
            ),
        )
        assert r.pontuais_janela == 30_000.0
        assert r.equivalente_meses_poupanca == 6.0

    def test_o_fim_da_janela_e_inclusivo(self):
        """Limite superior errado por um mês esvazia o último mês da janela."""
        r = ConsumoConscienteCalculator().calculate(
            _fluxo_com_janela(periodo=self._JANELA),
            _despesas(lazer=[_txn("2026-03-31", "ULTIMO DIA DA JANELA", Decimal("30000"))]),
        )
        assert r.pontuais_janela == 30_000.0

    def test_provisionado_sai_tambem_do_total_full(self):
        """`split_provisionado` já tira o posterior ao corte do denominador; sem
        o mesmo corte aqui, `total_pontuais` conta o que o fluxo não conta."""
        despesas = _despesas(
            lazer=[
                _txn("2025-12-10", "REALIZADO", Decimal("30000")),
                _txn("2026-06-10", "PROVISIONADO", Decimal("60000")),
            ]
        )
        com_corte = ConsumoConscienteCalculator().calculate(
            _fluxo_com_janela(periodo=self._JANELA, data_corte="2026-03-31"), despesas
        )
        sem_corte = ConsumoConscienteCalculator().calculate(
            _fluxo_com_janela(periodo=self._JANELA), despesas
        )
        assert com_corte.total_pontuais == 30_000.0
        assert com_corte.base.to_dict()["bruto"]["contagem"] == 1
        # Sem `data_corte` declarado o corte não é inventado — o payload de
        # payload antigo (pré-provisionado) segue com a base full.
        assert sem_corte.total_pontuais == 90_000.0
