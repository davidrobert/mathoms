"""ledger-certify núcleo puro — vereditos + drift + sum-preserving (ADR-302/343)."""

from __future__ import annotations

from types import SimpleNamespace

from dev.ledger_certify_core import (
    _drift,
    build_report,
    e3_group_verdict,
    e4_bucket_verdict,
    format_report,
)
from dev.ledger_conservation import (
    COBERTO_SEM_VALOR,
    CONSERVADO,
    NAO_VERIFICAVEL,
    PERDA_SILENCIOSA,
    investment_double_count,
)


def _e3(n_tx: int, *, dups: int = 0, total: int | None = None, valores=None) -> dict:
    txns = [{"valor": v} for v in (valores if valores is not None else [1.0] * n_tx)]
    return {
        "transacoes": txns,
        "transacoes_total": n_tx if total is None else total,
        "transacoes_duplicadas_removidas": dups,
    }


def _bucket(total: float, cats: dict, dados: dict | None = None, n_tx: int = 0) -> dict:
    return {
        "total_geral": total,
        "totais_por_categoria": cats,
        "dados": dados or {},
        "total_transacoes": n_tx,
    }


# ─────────────────────────── e3_group_verdict ───────────────────────────


def test_e3_group_conservado() -> None:
    assert e3_group_verdict(_e3(5))[0] == CONSERVADO


def test_e3_group_dups_coberto() -> None:
    assert e3_group_verdict(_e3(5, dups=2))[0] == COBERTO_SEM_VALOR


def test_e3_group_zero_tx_nao_sobe_a_conservado() -> None:
    assert e3_group_verdict(_e3(0))[0] == COBERTO_SEM_VALOR


def test_e3_group_inconsistente_nao_verificavel() -> None:
    assert (
        e3_group_verdict({"transacoes": [{"valor": 1}], "transacoes_total": 9})[0]
        == NAO_VERIFICAVEL
    )


def test_e3_group_sem_payload_nao_verificavel() -> None:
    assert e3_group_verdict(None)[0] == NAO_VERIFICAVEL
    assert e3_group_verdict({})[0] == NAO_VERIFICAVEL


def _with_ledger(g: dict, *, tx_carregadas: int, **remocoes: int) -> dict:
    g = dict(g)
    g["tx_carregadas"] = tx_carregadas
    g["remocoes"] = {k: {"count": v, "valor_cents": 0} for k, v in remocoes.items()}
    return g


def test_e3_group_ledger_fecha_upgrada_para_conservado() -> None:
    # ADR-347 — sem ledger, dups>0 seria COBERTO; com o ledger de contagem que
    # FECHA (7 == 5 survivors + 2 removidas), sobe a CONSERVADO (conservação provada).
    g = _with_ledger(_e3(5, dups=2), tx_carregadas=7, intra_statement_dedup=2)
    assert e3_group_verdict(g)[0] == CONSERVADO


def test_e3_group_ledger_com_residuo_e_perda_silenciosa() -> None:
    # ADR-347 — o ledger é o detector de P0: resíduo não-declarado ⇒ perda.
    g = _with_ledger(_e3(5), tx_carregadas=10, intra_statement_dedup=1)
    assert e3_group_verdict(g)[0] == PERDA_SILENCIOSA


# ─────────────────────────── e4_bucket_verdict ───────────────────────────


def test_e4_tx_bucket_conservado() -> None:
    b = _bucket(3.0, {"a": 1.0, "b": 2.0}, {"a": [{"valor": 1.0}], "b": [{"valor": 2.0}]})
    assert e4_bucket_verdict("despesas", b, [])[0] == CONSERVADO


def test_e4_tx_bucket_sum_mismatch_perda() -> None:
    b = _bucket(5.0, {"a": 1.0, "b": 2.0}, {"a": [{"valor": 1.0}], "b": [{"valor": 2.0}]})
    assert e4_bucket_verdict("despesas", b, [])[0] == PERDA_SILENCIOSA


def test_e4_tx_bucket_dados_mismatch_perda() -> None:
    b = _bucket(3.0, {"a": 1.0, "b": 2.0}, {"a": [{"valor": 1.0}], "b": [{"valor": 99.0}]})
    assert e4_bucket_verdict("despesas", b, [])[0] == PERDA_SILENCIOSA


def test_e4_investimentos_empty_coberto() -> None:
    assert e4_bucket_verdict("investimentos", {"dados": []}, [])[0] == COBERTO_SEM_VALOR


def test_e4_investimentos_ok() -> None:
    assert e4_bucket_verdict("investimentos", {"dados": [{"tipo": "x"}]}, [])[0] == CONSERVADO


def test_e4_non_ledger_bucket_coberto() -> None:
    assert e4_bucket_verdict("patrimonio", {"composicao": [1, 2]}, [])[0] == COBERTO_SEM_VALOR


def test_e4_bucket_ausente_nao_verificavel() -> None:
    assert e4_bucket_verdict("despesas", None, [])[0] == NAO_VERIFICAVEL


# ─────────── sum-preserving: o check que a conservação não vê (ADR-271) ───────────


def test_investment_double_count_falha_em_cenario_sum_preserving() -> None:
    """Total intacto, posição duplicada 2× — a soma fecha, o dedup não. É o modo
    de falha que a skill existe para caçar; a conservação agregada é cega a ele."""
    pos = {"tipo": "cdb", "instituicao": "itau", "descricao": "cdb pos"}
    investimentos = {"dados": [pos, dict(pos)], "total_geral": 100.0}
    collisions = investment_double_count(investimentos)
    assert collisions, "duplicata não detectada"
    assert e4_bucket_verdict("investimentos", investimentos, collisions)[0] == PERDA_SILENCIOSA


# ─────────────────────────── drift ───────────────────────────


def test_drift_particiona_matched_diff_only() -> None:
    fresh = {"a": _e3(5), "b": _e3(3), "c": _e3(2)}
    persisted = {"a": _e3(5), "b": _e3(4), "d": _e3(1)}
    d = _drift(fresh, persisted)
    assert d.matched == 1
    assert len(d.count_diff) == 1 and "b:" in d.count_diff[0]
    assert d.fresh_only == ["c"]
    assert d.persisted_only == ["d"]


# ─────────────────────────── build_report (síntese) ───────────────────────────


def _fake_result(
    n: int, with_key: int, transf: int = 0, valores: list[float] | None = None
) -> SimpleNamespace:
    vals = valores or [0.0] * n
    classified = [
        SimpleNamespace(natural_key=({"x": 1} if i < with_key else None), valor=vals[i])
        for i in range(n)
    ]
    return SimpleNamespace(
        classified=classified, cash_flow=SimpleNamespace(transferencias_count=transf)
    )


def _fake_e3_result() -> SimpleNamespace:
    return SimpleNamespace(
        statements_loaded=1, statements_reconciled=1, skipped_inputs=0, artifacts_written=1
    )


def _conserving_e4(n_tx: int) -> dict:
    despesas = _bucket(3.0, {"a": 3.0}, {"a": [{"valor": 1.0}, {"valor": 2.0}]}, n_tx=n_tx)
    despesas["_lineage"] = {"signals": {"tx_total": str(n_tx), "dedup_collapsed": "0"}}
    return {
        "despesas": despesas,
        "receitas": _bucket(0.0, {}, {}, n_tx=0),
        "investimentos": {"dados": []},
    }


def test_build_report_synthetic_conserva() -> None:
    seeds = [{"transacoes": [{"valor": 1.0}, {"valor": 2.0}]}]
    fresh_e3 = {"g1": _e3(2, valores=[1.0, 2.0])}
    report = build_report(
        "ws-uuid",
        "run-1",
        seeds,
        _fake_e3_result(),
        _fake_result(2, 1, valores=[1.0, 2.0]),
        _conserving_e4(2),
        fresh_e3,
        persisted_e3=fresh_e3,
    )
    assert [c.verdict for c in report.conservation] == [CONSERVADO, CONSERVADO]
    assert report.e3_groups[0].verdict == CONSERVADO
    assert report.natural_key["present"] == 1 and report.natural_key["total"] == 2
    assert report.drift.matched == 1
    assert "ledger-certify" in format_report(report)


def test_build_report_synthetic_detecta_drop_e3_para_e4() -> None:
    seeds = [{"transacoes": [{"valor": 1.0}, {"valor": 2.0}]}]
    fresh_e3 = {"g1": _e3(2, valores=[1.0, 2.0])}
    e4 = _conserving_e4(1)  # tx_total=1 mas E3 tem 2 survivors → dropou 1
    report = build_report(
        "ws-uuid", "run-1", seeds, _fake_e3_result(), _fake_result(1, 0), e4, fresh_e3, fresh_e3
    )
    assert report.conservation[1].verdict == PERDA_SILENCIOSA


def test_zero_write_ok_property() -> None:
    report = build_report(
        "ws",
        "r",
        [],
        _fake_e3_result(),
        _fake_result(0, 0),
        {"investimentos": {"dados": []}},
        {},
        {},
    )
    report.counts_before = {"pipeline_artifacts": 5}
    report.counts_after = {"pipeline_artifacts": 5}
    assert report.zero_write_ok
    report.counts_after = {"pipeline_artifacts": 6}
    assert not report.zero_write_ok
