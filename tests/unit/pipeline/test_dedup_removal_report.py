"""ADR-347 PR1 — declaração de remoções de dedup por canal (anti-silêncio).

Prova que `dedup_report`/`reconcile_with_report` **declaram** o que o dedup remove
(contagem + valor cents + par de fonte distinta), sem alterar o comportamento de
`reconcile`/`_dedup` legados. Não testa política de needs_review (PR2)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import jsonschema

from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Money, Transaction
from pipeline.domain.services.e3_reconciler_adapter import E3ReconcilerAdapter
from pipeline.domain.services.reconciliation_service import (
    DedupRemoval,
    ReconciliationConfig,
    ReconciliationService,
)


def _tx(desc: str, valor: str, *, src: str, day: int = 1) -> Transaction:
    return Transaction(
        date=date(2026, 1, day),
        description=desc,
        amount=Money.of(valor, "BRL"),
        source_document=src,
    )


def _stmt(txns: list[Transaction], *, src: str = "a.csv") -> BankStatement:
    return BankStatement(
        institution="itau",
        member_key="titular",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        currency="BRL",
        transactions=txns,
        source_document=src,
    )


def _service() -> ReconciliationService:
    return ReconciliationService(ReconciliationConfig())


def test_dedup_report_declara_contagem_e_valor_intra_statement():
    # 3 tx, uma é duplicata exata (mesma fonte) → 1 removida, R$12,34, cross=0.
    svc = _service()
    txns = [
        _tx("PADARIA", "10.00", src="a.csv"),
        _tx("MERCADO", "12.34", src="a.csv"),
        _tx("MERCADO", "12.34", src="a.csv"),
    ]
    kept, count, valor_cents, cross = svc.dedup_report(txns)
    assert len(kept) == 2
    assert count == 1
    assert valor_cents == 1234
    assert cross == 0  # mesma fonte → não é sinal de re-upload cross-file


def test_dedup_report_cross_source_conta_par_de_fonte_distinta():
    # mesma tx em duas fontes distintas (re-upload sobreposto) → cross=1.
    svc = _service()
    txns = [
        _tx("SALARIO", "5000.00", src="jan.csv"),
        _tx("SALARIO", "5000.00", src="jan_dez.csv"),
    ]
    kept, count, valor_cents, cross = svc.dedup_report(txns)
    assert count == 1
    assert valor_cents == 500000
    assert cross == 1


def test_dedup_report_sem_duplicata_nao_declara_nada():
    svc = _service()
    txns = [_tx("A", "1.00", src="a.csv"), _tx("B", "2.00", src="a.csv")]
    kept, count, valor_cents, cross = svc.dedup_report(txns)
    assert len(kept) == 2 and count == 0 and valor_cents == 0 and cross == 0


def test_reconcile_with_report_emite_DedupRemoval_intra():
    svc = _service()
    stmt = _stmt(
        [
            _tx("MERCADO", "12.34", src="a.csv"),
            _tx("MERCADO", "12.34", src="a.csv"),
        ]
    )
    out, removals = svc.reconcile_with_report([stmt])
    assert sum(len(s.transactions) for s in out) == 1
    assert len(removals) == 1
    r = removals[0]
    assert isinstance(r, DedupRemoval)
    assert r.canal == "intra_statement_dedup"
    assert r.count == 1 and r.valor_cents == 1234 and r.cross_source_count == 0
    assert r.source == "a.csv"  # F6: source_document keyed p/ o ledger de VALOR por artefato


def test_reconcile_legado_inalterado_vs_report():
    # `reconcile` (back-compat) deve devolver exatamente os mesmos statements que
    # `reconcile_with_report`[0] — zero regressão de comportamento.
    svc = _service()
    stmt = _stmt([_tx("X", "1.00", src="a.csv"), _tx("X", "1.00", src="a.csv")])
    legado = svc.reconcile([stmt])
    novo, _ = svc.reconcile_with_report([stmt])
    assert [len(s.transactions) for s in legado] == [len(s.transactions) for s in novo]
    assert sum(len(s.transactions) for s in legado) == 1


def _e2_payload(*, arquivo: str, txns: list[dict]) -> dict:
    return {
        "pipeline_stage": "E2",
        "banco": "itau",
        "tipo": "extratoconta",
        "moeda": "BRL",
        "periodo_inicio": "2026-01-01",
        "periodo_fim": "2026-01-31",
        "arquivo_origem": arquivo,
        "transacoes": txns,
    }


def test_reconcile_via_store_declara_cross_file_dedup():
    # Dois re-uploads sobrepostos (fontes distintas, mesma conta/período) com uma
    # tx duplicada → o merge cross-file declara a remoção em result.removals (ADR-347).
    sal = {"data": "2026-01-05", "descricao": "SALARIO", "valor": 5000.0}
    store = InMemoryArtifactStore()
    a = _e2_payload(
        arquivo="a.csv", txns=[sal, {"data": "2026-01-06", "descricao": "X", "valor": -10.0}]
    )
    b = _e2_payload(
        arquivo="b.csv", txns=[sal, {"data": "2026-01-07", "descricao": "Y", "valor": -20.0}]
    )
    store.seed("extract_statements", "itau_a", a)
    store.seed("extract_statements", "itau_b", b)
    result = E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)
    cross = [r for r in result.removals if r.canal == "cross_file_dedup"]
    assert len(cross) == 1
    assert cross[0].count == 1 and cross[0].valor_cents == 500000
    assert cross[0].cross_source_count == 1  # a.csv ≠ b.csv → sinal de re-upload


def test_artifact_ledger_balances_count_tol_zero():
    # ADR-347 PR1b — o artefato E3 declara tx_carregadas + remocoes e fecha
    # tx_carregadas == transacoes_total + Σ remocoes[*].count (tol-zero).
    txns = [
        {"data": "2026-01-05", "descricao": "MERCADO", "valor": -12.34},
        {"data": "2026-01-05", "descricao": "MERCADO", "valor": -12.34},  # dup intra
        {"descricao": "SEM DATA", "valor": -1.0},  # undated_drop
    ]
    store = InMemoryArtifactStore()
    store.seed("extract_statements", "itau_x", _e2_payload(arquivo="x.csv", txns=txns))
    E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)
    p = store.read("reconcile_transactions", store.list_keys("reconcile_transactions")[0])
    rem = p["remocoes"]
    assert p["tx_carregadas"] == 3
    assert rem["intra_statement_dedup"]["count"] == 1 and rem["undated_drop"]["count"] == 1
    # F6 (ADR-347 §Dec-6): valor do dedup intra serializado no artefato (antes era 0 hard-coded).
    # Assinado (débito MERCADO -12,34 → -1234c), espelhando dedup_report; harness compara val_in-val_out.
    assert rem["intra_statement_dedup"]["valor_cents"] == -1234
    assert p["tx_carregadas"] == len(p["transacoes"]) + sum(r["count"] for r in rem.values())


def test_artifact_ledger_valor_cents_assinado_valida_schema():
    # F6: intra valor_cents é ASSINADO (débito → negativo). O schema e3_reconciled deve
    # aceitar inteiro assinado (remoção de minimum:0); senão o write em strict quebraria
    # (DBArtifactStore._validate_schema, ADR-212). Trava a regressão que a revisão pegou.
    txns = [
        {"data": "2026-01-05", "descricao": "MERCADO", "valor": -12.34},
        {"data": "2026-01-05", "descricao": "MERCADO", "valor": -12.34},  # dup intra (débito)
    ]
    store = InMemoryArtifactStore()
    store.seed("extract_statements", "itau_x", _e2_payload(arquivo="x.csv", txns=txns))
    E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)
    p = store.read("reconcile_transactions", store.list_keys("reconcile_transactions")[0])
    entry = p["remocoes"]["intra_statement_dedup"]
    assert entry["valor_cents"] < 0  # débito → assinado negativo
    schema_path = Path(__file__).resolve().parents[3] / "config/schemas/e3_reconciled.schema.json"
    remocao_schema = json.loads(schema_path.read_text())["$defs"]["remocao"]
    jsonschema.validate(entry, remocao_schema)  # raise se o $def rejeitar valor_cents assinado


def test_exclusions_ledger_conta_tx_de_statement_pulado():
    # ADR-347 PR2 — statement inteiro pulado (banco vazio) tem suas tx contadas no
    # ledger run-level de exclusões (conservação workspace), não somem em silêncio.
    payload = _e2_payload(
        arquivo="e.csv",
        txns=[
            {"data": "2026-01-05", "descricao": "A", "valor": -1.0},
            {"data": "2026-01-06", "descricao": "B", "valor": -2.0},
        ],
    )
    payload["banco"] = ""  # força o canal empty_institution
    store = InMemoryArtifactStore()
    store.seed("extract_statements", "sem_banco", payload)
    result = E3ReconcilerAdapter(ReconciliationConfig()).reconcile_via_store(store)
    excl = {e.canal: e.count for e in result.exclusions}
    assert excl.get("empty_institution") == 2
