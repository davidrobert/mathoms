"""Construtores de payload E3/E4 sintético compartilhados pelos testes da ledger-certify.

Vivem fora dos dois arquivos de teste desde a A42.l3, quando a rubrica ganhou arquivo
próprio (`test_ledger_unit_verdicts.py`): duplicar os builders punha duas cópias dos
mesmos literais monetários no repo, e a segunda cópia diverge no primeiro campo novo.
"""

from __future__ import annotations


def e3_payload(
    n_tx: int, *, dups: int = 0, total: int | None = None, valores=None, remocoes=None
) -> dict:
    """Artefato E3 de um grupo. `total` divergente de `n_tx` simula produtor incoerente."""
    txs = [{"valor": v} for v in (valores or [1.0] * n_tx)]
    payload: dict = {
        "transacoes": txs,
        "transacoes_total": n_tx if total is None else total,
        "transacoes_duplicadas_removidas": dups,
    }
    if remocoes is not None:
        payload["remocoes"] = remocoes
    return payload


def bucket_payload(total: float, cats: dict, dados: dict | None = None, n_tx: int = 0) -> dict:
    """Balde transacional E4 (`despesas`/`receitas`)."""
    return {
        "total_geral": total,
        "totais_por_categoria": cats,
        "dados": dados if dados is not None else {},
        "total_transacoes": n_tx,
    }
