#!/usr/bin/env python3
"""Golden do bloco SOMBRA — não-regressão da D1 da [[ADR-421]] (A42.l14).

A l14 troca o sujeito da rubrica para o artefato entregue; a D1 exige que a
re-derivação não suma, virando bloco diagnóstico normativo. Nenhum teste de
sujeito olha a sombra, então apagá-la passaria verde em todos eles — este golden
é o único gate que reprova. Capturado contra ``origin/main`` ANTES do primeiro
commit de código da lane: capturado depois, congelaria a saída já mudada.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dev.ledger_conservation import cross_group_summary, fmt_cross_group

_GOLDEN = Path(__file__).parent / "goldens" / "ledger_certify_sombra_block.txt"


def _pernas(descricao: str, magnitude: float) -> list[dict]:
    """Duas pernas do MESMO evento com o shape do carrier ADR-354."""
    row = {"data": "2026-03-10", "descricao": descricao, "valor": magnitude, "moeda": "BRL"}
    return [
        {**row, "tipo_conta": "extrato", "titular": ""},
        {**row, "tipo_conta": "extratoconta", "titular": "titular exemplo"},
    ]


def _despesas() -> dict:
    """Balde que fecha em cents com 2 pares do carrier em 2 categorias."""
    return {
        "total_geral": 300.0,
        "totais_por_categoria": {"moradia": 200.0, "outros": 100.0},
        "dados": {"moradia": _pernas("aluguel", 100.0), "outros": _pernas("mercado", 50.0)},
        "total_transacoes": 4,
        "_lineage": {"signals": {"tx_total": "6", "dedup_collapsed": "0"}},
    }


def _receitas() -> dict:
    """Balde que fecha em cents com o 3º par do carrier."""
    return {
        "total_geral": 300.0,
        "totais_por_categoria": {"salario": 300.0},
        "dados": {"salario": _pernas("salario", 150.0)},
        "total_transacoes": 2,
    }


def e4_com_carrier_cross_grupo() -> dict:
    """E4 com 3 pares do carrier em 2 baldes — wire JSON number ([[ADR-090]] §wire)."""
    return {"despesas": _despesas(), "receitas": _receitas(), "investimentos": {"dados": []}}


def sombra_block_text() -> str:
    """Bloco sombra renderizado com o rótulo e o título DEFAULT (os da sombra)."""
    return "\n".join(fmt_cross_group(cross_group_summary(e4_com_carrier_cross_grupo(), 9)))


def test_bloco_sombra_identico_ao_capturado_contra_origin_main() -> None:
    assert sombra_block_text() == _GOLDEN.read_text(encoding="utf-8").rstrip("\n")
