"""ledger-certify harness — colapso workspace-latest + seed/read InMemory (ADR-302/343).

Cobre a lógica de leitura que NÃO depende do DB (fixtures sintéticas). A validação
ponta-a-ponta é o run real sobre um workspace (skill Passo 2), não um teste.
"""

from __future__ import annotations

from types import SimpleNamespace

from dev.certify_ledger_local import _fresh_e3, _latest_by_canonical, _seed_store


def _row(stage: str, key: str, created_at: int, rid: int, payload: dict) -> SimpleNamespace:
    return SimpleNamespace(
        stage=stage, artifact_key=key, created_at=created_at, id=rid, content_json=payload
    )


def test_latest_by_canonical_picks_newest_created_at() -> None:
    rows = [
        _row("extract_statements", "k1", 100, 1, {"v": "old"}),
        _row("extract_statements", "k1", 200, 2, {"v": "new"}),
    ]
    latest = _latest_by_canonical(rows)
    assert latest[("extract_statements", "k1")].content_json == {"v": "new"}


def test_latest_by_canonical_collapses_legacy_and_descriptive() -> None:
    rows = [
        _row("E2-extratos", "k1", 300, 1, {"v": "legacy-older-created"}),
        _row("extract_statements", "k1", 400, 2, {"v": "descritivo-newer"}),
    ]
    latest = _latest_by_canonical(rows)
    assert len(latest) == 1
    assert latest[("extract_statements", "k1")].content_json["v"] == "descritivo-newer"


def test_latest_by_canonical_tiebreak_by_id() -> None:
    rows = [
        _row("extract_statements", "k1", 100, 1, {"v": "a"}),
        _row("extract_statements", "k1", 100, 5, {"v": "b"}),
    ]
    latest = _latest_by_canonical(rows)
    assert latest[("extract_statements", "k1")].content_json["v"] == "b"


def test_seed_store_returns_only_e2_payloads() -> None:
    from pipeline.artifact_store import InMemoryArtifactStore

    store = InMemoryArtifactStore()
    latest_e2 = {
        ("extract_statements", "acc1"): {"transacoes": [{"valor": 1.0}]},
        ("extract_invoices", "card1"): {"transacoes": []},
    }
    latest_base = {("consolidate_baseline", "baseline_patrimonial"): {"data": {}}}
    seeds = _seed_store(store, latest_e2, latest_base)
    assert len(seeds) == 2
    assert store.read("extract_statements", "acc1") == {"transacoes": [{"valor": 1.0}]}
    assert store.read("consolidate_baseline", "baseline_patrimonial") == {"data": {}}


def test_fresh_e3_reads_reconcile_keys() -> None:
    from pipeline.artifact_store import InMemoryArtifactStore

    store = InMemoryArtifactStore()
    store.seed("reconcile_transactions", "g1", {"transacoes_total": 3, "transacoes": []})
    store.seed("reconcile_transactions", "g2", {"transacoes_total": 1, "transacoes": []})
    fresh = _fresh_e3(store)
    assert set(fresh) == {"g1", "g2"}
    assert fresh["g1"]["transacoes_total"] == 3


class _FailingSession:
    """Sessão cujo ``execute`` sempre falha — grava se o ``rollback`` foi chamado."""

    def __init__(self) -> None:
        self.rolled_back = 0

    def execute(self, *_args, **_kwargs):
        from sqlalchemy.exc import OperationalError

        raise OperationalError("SELECT ...", {}, Exception("no such column: orphaned_at"))

    def rollback(self) -> None:
        self.rolled_back += 1


def test_blast_radius_faz_rollback_antes_de_degradar() -> None:
    # Em PostgreSQL o statement falho aborta a transação (25P02) e o `_row_counts`
    # seguinte — a PROVA de zero-write — falharia junto. O rollback é o que mantém a
    # sessão utilizável depois de a medição SECUNDÁRIA degradar.
    from dev.certify_ledger_local import _blast_radius_or_empty

    session = _FailingSession()
    assert _blast_radius_or_empty(session, "ws-uuid") == {}
    assert session.rolled_back == 1
