"""ledger-certify — núcleo puro de conservação E2→E3→E4 (ADR-343/302)."""

from __future__ import annotations

from dev.ledger_conservation import (
    COBERTO_SEM_VALOR,
    CONSERVADO,
    PERDA_SILENCIOSA,
    _tx_cents,
    e2_to_e3,
    e3_to_e4,
    investment_double_count,
)


def _e2(*valores: float) -> dict:
    return {"transacoes": [{"valor": v} for v in valores]}


def _e3(survivors: list[float], dups: int = 0) -> dict:
    return {
        "transacoes_total": len(survivors),
        "transacoes_duplicadas_removidas": dups,
        "transacoes": [{"valor": v} for v in survivors],
    }


def _bucket(geral, cats: dict, n_tx: int, *, tx_total=None, collapsed=0) -> dict:
    b = {"total_geral": geral, "totais_por_categoria": cats, "total_transacoes": n_tx}
    if tx_total is not None:
        b["_lineage"] = {"signals": {"tx_total": str(tx_total), "dedup_collapsed": str(collapsed)}}
    return b


# ─────────────────────────── _tx_cents ───────────────────────────


def test_tx_cents_prefers_amount_over_valor() -> None:
    assert _tx_cents({"valor": 1.11, "amount": "2.22"}) == 222
    assert _tx_cents({"valor": 1.11, "amount": None}) == 111
    assert _tx_cents({"valor": 1.11}) == 111


# ─────────────────────────── E2 → E3 ───────────────────────────


def test_e2e3_conservado_sem_dups() -> None:
    r = e2_to_e3([_e2(100.0, 50.0)], [_e3([100.0, 50.0])])
    assert r.verdict == CONSERVADO
    assert r.count_in == 2 and r.count_out == 2 and r.value_in_cents == 15000


def test_e2e3_dups_vira_coberto_sem_valor() -> None:
    r = e2_to_e3([_e2(100.0, 100.0, 50.0)], [_e3([100.0, 50.0], dups=1)])
    assert r.verdict == COBERTO_SEM_VALOR  # count fecha (2+1==3), valor não-provável


def test_e2e3_tx_perdida_e_perda_silenciosa() -> None:
    # 3 entram, só 2 sobrevivem e 0 dups declaradas → 1 sumiu
    r = e2_to_e3([_e2(100.0, 50.0, 25.0)], [_e3([100.0, 50.0], dups=0)])
    assert r.verdict == PERDA_SILENCIOSA
    assert r.count_in == 3 and r.count_out == 2


def test_e2e3_valor_diverge_sem_dups_e_perda() -> None:
    r = e2_to_e3([_e2(100.0, 50.0)], [_e3([100.0, 49.0])])  # count ok, valor não
    assert r.verdict == PERDA_SILENCIOSA


# ─────────────────────────── E3 → E4 ───────────────────────────


def test_e3e4_conservado() -> None:
    despesas = _bucket(80.0, {"casa": 80.0}, 1, tx_total=2, collapsed=0)
    receitas = _bucket(100.0, {"salario": 100.0}, 1)
    r = e3_to_e4([_e3([100.0, 80.0])], despesas, receitas, transferencias_count=0)
    assert r.verdict == CONSERVADO


def test_e3e4_classifier_dropou() -> None:
    despesas = _bucket(80.0, {"casa": 80.0}, 1, tx_total=1)  # E3=2 mas tx_total=1
    receitas = _bucket(100.0, {"salario": 100.0}, 1)
    r = e3_to_e4([_e3([100.0, 80.0])], despesas, receitas, transferencias_count=0)
    assert r.verdict == PERDA_SILENCIOSA


def test_e3e4_destino_nao_fecha() -> None:
    despesas = _bucket(80.0, {"casa": 80.0}, 1, tx_total=3)  # 3 classificados, só 2 têm destino
    receitas = _bucket(100.0, {"salario": 100.0}, 1)
    r = e3_to_e4([_e3([100.0, 80.0, 10.0])], despesas, receitas, transferencias_count=0)
    assert r.verdict == PERDA_SILENCIOSA


def test_e3e4_balde_nao_fecha() -> None:
    despesas = _bucket(80.0, {"casa": 50.0}, 1, tx_total=2)  # Σ cat (50) != total (80)
    receitas = _bucket(100.0, {"salario": 100.0}, 1)
    r = e3_to_e4([_e3([100.0, 80.0])], despesas, receitas, transferencias_count=0)
    assert r.verdict == PERDA_SILENCIOSA


def test_e3e4_transferencia_conta_no_destino() -> None:
    despesas = _bucket(80.0, {"casa": 80.0}, 1, tx_total=3)
    receitas = _bucket(100.0, {"salario": 100.0}, 1)
    r = e3_to_e4([_e3([100.0, 80.0, 30.0])], despesas, receitas, transferencias_count=1)
    assert r.verdict == CONSERVADO  # 1 receita + 1 despesa + 1 transferência = 3


# ─────────────── dedup de investimento (sum-preserving fail) ───────────────


def test_investment_double_count_detecta_duplicata() -> None:
    inv = {
        "dados": [
            {
                "tipo": "CDB",
                "instituicao": "Banco X",
                "descricao": "CDB 2028",
                "valor_atual": 1000.0,
            },
            {
                "tipo": "cdb",
                "instituicao": "banco x",
                "descricao": "CDB 2028",
                "valor_atual": 1000.0,
            },
        ]
    }
    hits = investment_double_count(inv)
    assert len(hits) == 1  # normalização casa "CDB"/"cdb", "Banco X"/"banco x"


def test_investment_double_count_limpo_quando_unico() -> None:
    inv = {
        "dados": [
            {"tipo": "CDB", "instituicao": "Banco X", "descricao": "CDB 2028"},
            {"tipo": "CDB", "instituicao": "Banco Y", "descricao": "CDB 2030"},
        ]
    }
    assert investment_double_count(inv) == []
