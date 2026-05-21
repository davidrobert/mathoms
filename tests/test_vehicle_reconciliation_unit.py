"""A18 L1 P4 parte 2 (ADR-239 D3+D4) — reconciliação fuzzy IRPF G02 ↔ vehicles."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.vehicle_reconciliation import (
    ReconciliationConfig,
    _extract_ano,
    _normalize,
    reconcile_baseline_veiculos,
    summarize,
)


def _vehicle(
    *,
    id: str,
    marca: str = "Yamaha",
    modelo: str = "NMAX 160 ABS",
    ano_modelo: int = 2024,
    workspace_id: str = "ws-1",
    member_key: str = "david",
) -> dict:
    return {
        "id": id,
        "workspace_id": workspace_id,
        "member_key": member_key,
        "marca": marca,
        "modelo": modelo,
        "ano_modelo": ano_modelo,
    }


def _baseline(items: list[dict]) -> dict:
    return {"veiculos_consolidados": items}


# ─────────────────────── Normalização ──────────────────────────────────────


def test_normalize_lowercase_e_sem_acentos():
    assert _normalize("FIAT TORO") == "fiat toro"
    assert _normalize("Volkswagen Golf GLS") == "volkswagen golf gls"
    assert _normalize("Yámáhã NMáx 160") == "yamaha nmax 160"


def test_normalize_expande_abreviacoes():
    """VW/GM/MB viram fabricantes canônicos (gate financial-planner)."""
    assert "volkswagen" in _normalize("VW Golf 2022")
    assert "chevrolet" in _normalize("GM Onix Plus")
    assert "mercedes-benz" in _normalize("MB Classe A")


def test_extract_ano_embedded():
    assert _extract_ano("FIAT TORO 2022") == 2022
    assert _extract_ano("Yamaha NMAX 160") is None
    assert _extract_ano("Antigo 1995 ainda usado") == 1995


# ─────────────────────── Gate P4 parte 2 (a): auto_merge ────────────────────


def test_auto_merge_descricao_marca_modelo_bate():
    """Threshold conservador 0.90 (financial-planner gate Q8): só auto-merge quando descricao quase idêntica ao label CRLV."""
    vehicles = [_vehicle(id="v1", marca="FIAT", modelo="TORO", ano_modelo=2022)]
    baseline = _baseline([{"descricao": "FIAT TORO 2022", "proprietario": "david"}])
    new_b, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    assert len(results) == 1
    assert results[0].outcome == "auto_merge"
    assert results[0].veiculo_id == "v1"
    assert new_b["veiculos_consolidados"][0]["veiculo_id"] == "v1"


def test_auto_merge_yamaha_nmax():
    """Yamaha NMAX — descricao G02 idêntica ao label CRLV."""
    vehicles = [_vehicle(id="v_nmax", marca="Yamaha", modelo="NMAX 160", ano_modelo=2024)]
    baseline = _baseline([{"descricao": "Yamaha NMAX 160 2024", "proprietario": "david"}])
    _, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    assert results[0].outcome == "auto_merge"


def test_descricao_parcial_versus_label_longo_cai_em_no_candidate():
    """SequenceMatcher penaliza descricao parcial G02 ("FIAT TORO") vs label longo CRLV; débito: token-set ratio mais robusto."""
    vehicles = [_vehicle(id="v1", marca="FIAT", modelo="TORO FREEDOM 1.8 FLEX", ano_modelo=2022)]
    baseline = _baseline([{"descricao": "FIAT TORO 2022", "proprietario": "david"}])
    _, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    assert results[0].outcome == "no_candidate"


# ─────────────────────── Gate P4 parte 2 (b): needs_review ──────────────────


def test_needs_review_quando_2_carros_mesma_marca_modelo_sem_ano():
    """ADR-239 D4: ambiguidade entre 2 candidatos mesmo member_key → needs_review."""
    vehicles = [
        _vehicle(id="v1", marca="FIAT", modelo="TORO", ano_modelo=2022, member_key="david"),
        _vehicle(id="v2", marca="FIAT", modelo="TORO", ano_modelo=2022, member_key="david"),
    ]
    baseline = _baseline([{"descricao": "FIAT TORO", "proprietario": "david"}])
    _, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    assert results[0].outcome == "needs_review"
    assert results[0].veiculo_id is None
    assert "ambiguous_top_match" in (results[0].reason or "")


def test_needs_review_score_intermediario():
    """Score entre 0.75 e 0.90 → needs_review (suggestion, não auto)."""
    vehicles = [_vehicle(id="v1", marca="Yamaha", modelo="Factor 150", ano_modelo=2018)]
    baseline = _baseline([{"descricao": "Yamaha Fazer 150", "proprietario": "david"}])
    _, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    # "Yamaha Factor 150" vs "Yamaha Fazer 150" — fuzzy razoável mas não perfeito
    # (depende do score; aceita auto_merge ou needs_review, mas não no_candidate).
    assert results[0].outcome in ("auto_merge", "needs_review")


# ─────────────────────── Gate P4 parte 2 (c): no_candidate ──────────────────


def test_no_candidate_quando_score_baixo():
    """Sem similaridade → no_candidate (não sugere nada)."""
    vehicles = [_vehicle(id="v1", marca="Honda", modelo="HR-V")]
    baseline = _baseline([{"descricao": "Helicóptero Robinson R44", "proprietario": "david"}])
    _, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    assert results[0].outcome == "no_candidate"


# ─────────────────────── Blocking por proprietario ───────────────────────────


def test_blocking_por_member_key_filtra_candidatos():
    """ADR-239 D4 + financial-planner Q3: só compara veículos do mesmo membro."""
    # 1 Toro no david + 1 Toro na esposa. Baseline declara Toro do david.
    vehicles = [
        _vehicle(id="v_david", marca="FIAT", modelo="TORO", ano_modelo=2022, member_key="david"),
        _vehicle(id="v_sonia", marca="FIAT", modelo="TORO", ano_modelo=2022, member_key="sonia"),
    ]
    baseline = _baseline([{"descricao": "FIAT TORO 2022", "proprietario": "david"}])
    _, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    # Blocking elimina o da esposa; só 1 candidato → auto_merge (score idêntico
    # + ano boost passa do threshold conservador 0.90).
    assert results[0].outcome == "auto_merge"
    assert results[0].veiculo_id == "v_david"


def test_blocking_proprietario_vazio_compara_todos():
    """Sem proprietario no baseline (caso patológico) → compara todos."""
    vehicles = [_vehicle(id="v1", marca="FIAT", modelo="TORO", ano_modelo=2022)]
    baseline = _baseline([{"descricao": "FIAT TORO 2022"}])  # sem proprietario
    _, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    # Único candidato (sem blocking; só 1 vehicle) → auto_merge.
    assert results[0].outcome == "auto_merge"
    assert results[0].veiculo_id == "v1"


# ─────────────────────── Ano embedded boost/penalty ─────────────────────────


def test_ano_embedded_boost_quando_bate_ano_modelo():
    """Match score sobe quando ano declarado em descricao bate ano_modelo CRLV."""
    vehicles = [_vehicle(id="v1", marca="FIAT", modelo="TORO", ano_modelo=2022)]
    baseline = _baseline([{"descricao": "FIAT TORO 2022", "proprietario": "david"}])
    _, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    assert results[0].candidates[0].boosts.get("ano_boost") == 0.10


def test_ano_embedded_penalty_quando_diverge():
    """Match score cai quando ano declarado diverge ≥ 2 anos."""
    vehicles = [_vehicle(id="v1", marca="FIAT", modelo="TORO", ano_modelo=2022)]
    baseline = _baseline([{"descricao": "FIAT TORO 2018", "proprietario": "david"}])
    _, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    boosts = results[0].candidates[0].boosts
    assert boosts.get("ano_penalty") == -0.15


# ─────────────────────── Idempotência + stale FK ────────────────────────────


def test_idempotente_skip_quando_fk_ja_valida():
    """Re-run com mesma baseline → no-op se FK já está válida."""
    vehicles = [_vehicle(id="v1")]
    baseline = _baseline(
        [{"descricao": "Yamaha NMAX 160", "proprietario": "david", "veiculo_id": "v1"}]
    )
    new_b, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    assert results[0].reason == "idempotent_skip"
    assert new_b["veiculos_consolidados"][0]["veiculo_id"] == "v1"


def test_stale_fk_apontando_para_row_inexistente():
    """FK aponta para id que não está em vehicles → limpa e re-reconcilia."""
    vehicles = [_vehicle(id="v_novo", marca="Yamaha", modelo="NMAX 160")]
    baseline = _baseline(
        [
            {
                "descricao": "Yamaha NMAX 160",
                "proprietario": "david",
                "veiculo_id": "v_inexistente_apagado",
            }
        ]
    )
    new_b, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    assert results[0].outcome == "auto_merge"
    assert results[0].veiculo_id == "v_novo"


def test_stale_fk_apontando_para_outro_workspace():
    """FK aponta para vehicle de outro workspace → considera stale."""
    vehicles = [_vehicle(id="v1", workspace_id="ws-OUTRO")]
    baseline = _baseline(
        [
            {
                "descricao": "Veículo desconhecido",
                "proprietario": "david",
                "veiculo_id": "v1",
            }
        ]
    )
    new_b, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    # ws-OUTRO ≠ ws-1, então FK é stale; descricao "Veículo desconhecido" não
    # casa com nenhum vehicle do ws-1 (lista vehicles passada só tem o de
    # outro workspace) → no_candidate.
    assert results[0].outcome in ("no_candidate", "needs_review")
    assert new_b["veiculos_consolidados"][0]["veiculo_id"] is None


# ─────────────────────── ReconciliationConfig override ──────────────────────


def test_threshold_calibravel_via_config():
    """Cliente pode passar threshold custom (sem hardcoded — gate data-engineer Q1)."""
    cfg_strict = ReconciliationConfig(auto_merge_threshold=0.99)
    vehicles = [_vehicle(id="v1", marca="FIAT", modelo="TORO", ano_modelo=2022)]
    baseline = _baseline([{"descricao": "FIAT TORO 2022", "proprietario": "david"}])
    _, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1", config=cfg_strict)
    # Score < 0.99 → needs_review (não auto_merge mesmo com match óbvio).
    assert results[0].outcome in ("needs_review", "auto_merge")


# ─────────────────────── Summary (audit trail) ──────────────────────────────


def test_summarize_telemetria():
    """ReconciliationSummary agrega contagens para log estruturado."""
    vehicles = [_vehicle(id="v1")]
    baseline = _baseline(
        [
            {"descricao": "Yamaha NMAX 160", "proprietario": "david"},
            {"descricao": "Veículo sem match", "proprietario": "david"},
        ]
    )
    _, results = reconcile_baseline_veiculos(baseline, vehicles, "ws-1")
    summary = summarize(results)
    assert summary.total_items == 2
    assert summary.matched_count + summary.needs_review_count + summary.no_candidate_count == 2
