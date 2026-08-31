"""Modo entregue da KR-B — fail-closed + fiação sem DB."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from dev.ledger_certify_entregue import (
    EntregueRecusado,
    evidence_from_retention,
    require_pinned_run,
)


def test_require_pinned_run_recusa_workspace_latest() -> None:
    with pytest.raises(EntregueRecusado, match="workspace-latest"):
        require_pinned_run(None)
    with pytest.raises(EntregueRecusado, match="workspace-latest"):
        require_pinned_run("")
    assert require_pinned_run("run-1") == "run-1"


def test_evidence_recusa_sem_collapse_retention() -> None:
    with pytest.raises(EntregueRecusado, match="collapse_retention"):
        evidence_from_retention("run-1", None, None)
    with pytest.raises(EntregueRecusado, match="collapse_retention"):
        evidence_from_retention("run-1", {"skipped": True}, "rev")


def test_evidence_recusa_sombra_sem_corte() -> None:
    summary = {"collapse_retention": {"removals_publicadas": 0, "retido_por_override": 0}}
    with pytest.raises(EntregueRecusado, match="sem rows cortadas"):
        evidence_from_retention("run-1", summary, "rev")


def test_evidence_aceita_enforce_com_cortadas() -> None:
    summary = {"collapse_retention": {"removals_publicadas": 453, "retido_por_override": 0}}
    got = evidence_from_retention("run-abc", summary, "deadbeef")
    assert got == {
        "run_id": "run-abc",
        "executor_revision": "deadbeef",
        "cortadas": 453,
        "retido_por_override": 0,
    }


def test_seed_e3_nao_chama_reconcile() -> None:
    from dev.certify_ledger_local import _E3_STAGE, _fresh_e3, _seed_e3
    from pipeline.artifact_store import InMemoryArtifactStore

    store = InMemoryArtifactStore()
    _seed_e3(store, {"g1": {"transacoes_total": 2, "transacoes": []}})
    assert _fresh_e3(store) == {"g1": {"transacoes_total": 2, "transacoes": []}}
    assert store.list_keys(_E3_STAGE) == ["g1"]


def _rederive_vazio(_session, _ws, _run):
    from pipeline.artifact_store import InMemoryArtifactStore

    e3_result = SimpleNamespace(
        statements_loaded=0, statements_reconciled=0, skipped_inputs=0, artifacts_written=0
    )
    result = SimpleNamespace(classified=[], cash_flow=SimpleNamespace(transferencias_count=0))
    return InMemoryArtifactStore(), [], e3_result, result, {"investimentos": {"dados": []}}


def _rederive_entregue_vazio(_session, _ws, _run, _e3):
    result = SimpleNamespace(classified=[], cash_flow=SimpleNamespace(transferencias_count=3))
    return result, {"despesas": {"dados": {}}, "receitas": {"dados": {}}}


def _patch_entregue(monkeypatch, mod) -> None:
    monkeypatch.setattr(mod, "_row_counts", lambda _s, _w: {"pipeline_artifacts": 7})
    monkeypatch.setattr(mod, "_rederive", _rederive_vazio)
    monkeypatch.setattr(mod, "_persisted_e3_subject", lambda _s, _w, _r: {})
    monkeypatch.setattr(mod, "_e3_of_run", lambda _s, _w, _r: {"g1": {"transacoes": []}})
    monkeypatch.setattr(mod, "_entregue_evidence", lambda _s, _w, _r: _EVIDENCE)
    monkeypatch.setattr(mod, "_rederive_entregue", _rederive_entregue_vazio)
    monkeypatch.setattr(mod, "_blast_radius_or_empty", lambda _s, _w: {})


_EVIDENCE = {
    "run_id": "run-1",
    "executor_revision": "abc",
    "cortadas": 2,
    "retido_por_override": 0,
}


def test_certify_entregue_anexa_bloco_e_prova_zero_write(monkeypatch) -> None:
    from dev import certify_ledger_local as mod

    _patch_entregue(monkeypatch, mod)
    report = mod.certify_entregue(object(), "ws-uuid", "run-1")
    assert report.zero_write_ok is True
    assert report.entregue["cortadas"] == 2
    assert report.cross_group_entregue is not None
    assert report.cross_group_entregue.nao_varrido == {"transferencias": 3}
    texto = mod.format_report(report)
    assert texto.count("[numerador KR-B]") == 1
    assert "[sombra · enforce omitido]" in texto
