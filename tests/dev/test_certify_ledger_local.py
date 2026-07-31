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


def _rederive_vazio(_session, _ws, _run):
    """``_rederive`` sem DB: store vazio + E4 mínimo legível pelo núcleo puro."""
    from pipeline.artifact_store import InMemoryArtifactStore

    e3_result = SimpleNamespace(
        statements_loaded=0, statements_reconciled=0, skipped_inputs=0, artifacts_written=0
    )
    result = SimpleNamespace(classified=[], cash_flow=SimpleNamespace(transferencias_count=0))
    return InMemoryArtifactStore(), [], e3_result, result, {"investimentos": {"dados": []}}


def test_certify_degrada_o_blast_radius_sem_derrubar_a_certificacao(monkeypatch) -> None:
    # RATCHET no grão de `certify`: o CALL-SITE não tinha teste — voltar a chamar
    # `_override_blast_radius` (SQL cru sobre 5 colunas nullable, sem guarda) mantinha a
    # suíte verde e derrubava a certificação inteira num schema divergente, junto com a
    # prova de zero-write.
    from dev import certify_ledger_local as mod

    monkeypatch.setattr(mod, "_row_counts", lambda _s, _w: {"pipeline_artifacts": 7})
    monkeypatch.setattr(mod, "_rederive", _rederive_vazio)
    monkeypatch.setattr(mod, "_persisted_e3_by_key", lambda _s, _w: {})
    session = _FailingSession()
    report = mod.certify(session, "ws-uuid", "run-1")
    assert report.blast_radius == {}
    assert session.rolled_back == 1
    assert report.zero_write_ok is True
    assert "não medido" in mod.format_report(report)


class _PendingWriteSession(_FailingSession):
    """Sessão em que a re-derivação deixou escrita PENDENTE — visível a SELECT na mesma
    sessão (é assim que o zero-write se prova) — e cujo ``rollback`` a apaga."""

    def __init__(self) -> None:
        super().__init__()
        self.pending = 0

    def rollback(self) -> None:
        super().rollback()
        self.pending = 0


def _rederive_escrevendo(session, _ws, _run):
    """``_rederive`` que deixa 1 escrita pendente — o caso que a prova de zero-write tem de pegar."""
    session.pending = 1
    return _rederive_vazio(session, _ws, _run)


def test_contagem_final_vem_antes_do_blast_radius_que_faz_rollback(monkeypatch) -> None:
    # RATCHET de ORDEM: com `blast_radius` ANTES de `counts_after`, o `rollback` do ramo
    # degradado apaga a escrita pendente antes da 2ª contagem ⇒ counts_before ==
    # counts_after, `rolled_back == 1` e `zero_write_ok=True` — veredito de zero-write com
    # escrita tendo existido. A medição SECUNDÁRIA vem DEPOIS da prova, nunca antes.
    from dev import certify_ledger_local as mod

    monkeypatch.setattr(mod, "_row_counts", lambda s, _w: {"pipeline_artifacts": 7 + s.pending})
    monkeypatch.setattr(mod, "_rederive", _rederive_escrevendo)
    monkeypatch.setattr(mod, "_persisted_e3_by_key", lambda _s, _w: {})
    session = _PendingWriteSession()
    report = mod.certify(session, "ws-uuid", "run-1")
    assert session.rolled_back == 1 and session.pending == 0
    assert report.counts_before == {"pipeline_artifacts": 7}
    assert report.counts_after == {"pipeline_artifacts": 8}
    assert report.zero_write_ok is False
