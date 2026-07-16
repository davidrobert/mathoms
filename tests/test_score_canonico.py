"""ADR-217 wave 0 — score_version + componentes[].status + ScoreReader recompute on-read."""

from __future__ import annotations

from pipeline.domain.services.financial_score_calculator import (
    SCORE_VERSION,
    FinancialScoreCalculator,
    FinancialScoreConfig,
)


def _calc() -> FinancialScoreCalculator:
    return FinancialScoreCalculator(FinancialScoreConfig.default())


def _sample_inputs() -> dict:
    return {
        "ratios": {
            "taxa_poupanca_recorrente_pct": 25.0,
            "autonomia_financeira_meses": 6.0,
            "taxa_endividamento_pct": 10.0,
        },
        "patrimonio": {"composicao": [{"valor": v} for v in (1_000_000, 800_000, 500_000)]},
        "goals": {"if_pct": 30.0},
    }


def test_calculate_emite_score_version_canonico():
    result = _calc().calculate(**_sample_inputs())
    assert result["score_version"] == SCORE_VERSION


def _cobertura_nota(*, cobertura: float, meses_alvo: int | None) -> float:
    reserva = {"cobertura_meses": cobertura}
    if meses_alvo is not None:
        reserva["meses_alvo"] = meses_alvo
    inputs = {**_sample_inputs(), "reserva": reserva}
    result = _calc().calculate(**inputs)
    return next(c for c in result["componentes"] if c["code"] == "cobertura_despesas")["nota"]


def test_cobertura_plateau_satura_no_meses_alvo():
    """score_version 2.0 (ADR-328/FP-02): nota satura em 10 no alvo do perfil e
    não sobe acima dele — não premia over-provisioning."""
    for alvo in (6, 12, 18):
        assert _cobertura_nota(cobertura=alvo, meses_alvo=alvo) == 10.0
        assert _cobertura_nota(cobertura=alvo * 2, meses_alvo=alvo) == 10.0
        assert _cobertura_nota(cobertura=alvo * 3, meses_alvo=alvo) == 10.0


def test_cobertura_no_alvo_nao_e_penalizada():
    """CLT no alvo de 6m tira nota alta (era ~1,4/10 no teto fixo 24 do 1.0-legacy)."""
    assert _cobertura_nota(cobertura=6, meses_alvo=6) == 10.0


def test_cobertura_interpola_entre_piso_e_alvo():
    """Piso 3m mantido; interpola linear [3, meses_alvo] → [0, 10]."""
    # meio do caminho entre 3 e 12 (=7,5) → 5,0
    assert _cobertura_nota(cobertura=7.5, meses_alvo=12) == 5.0
    # abaixo do piso → 0
    assert _cobertura_nota(cobertura=3, meses_alvo=12) == 0.0


def test_cobertura_fallback_sem_meses_alvo_usa_config():
    """Sem ``reserva.meses_alvo`` (perfil não resolve) → plateau no fallback do
    config (12); satura em 12."""
    assert _cobertura_nota(cobertura=12, meses_alvo=None) == 10.0
    assert _cobertura_nota(cobertura=24, meses_alvo=None) == 10.0


def test_cobertura_nota_2_0_nunca_abaixo_do_1_0_legacy():
    """Prova do financial-planner: para range_min=3 fixo e meses_alvo ≤ 24, a nota
    da cobertura só sobe ou fica flat vs teto fixo 24 — nenhuma família perde ponto."""
    from pipeline.domain.services.financial_score_calculator import linear_interpolate

    for meses_alvo in (6, 12, 18):
        for cobertura in (3, 5, 8, 12, 20, 30):
            nova = _cobertura_nota(cobertura=cobertura, meses_alvo=meses_alvo)
            antiga = linear_interpolate(cobertura, 3, 24)
            assert nova >= antiga - 1e-9, (meses_alvo, cobertura, nova, antiga)


def test_calculate_componentes_carregam_status_emitted():
    result = _calc().calculate(**_sample_inputs())
    assert all(c["status"] == "emitted" for c in result["componentes"])


def test_calculate_componentes_carregam_code_canonico():
    result = _calc().calculate(**_sample_inputs())
    codes = {c["code"] for c in result["componentes"]}
    assert codes == {
        "taxa_poupanca_recorrente",
        "cobertura_despesas",
        "taxa_endividamento",
        "progresso_if",
        "diversificacao",
    }


def test_score_reader_recompute_on_read_legacy_artifact():
    """ADR-217 D6: artifact legado sem score_version recebe recompute em service-layer."""
    from backend.app.services.score_reader import (
        ensure_score_present,
        has_canonical_score,
    )

    legacy_payload = {
        "score": {"valor": 6.5, "classificacao": "Bom", "componentes": []},
        **_sample_inputs(),
    }
    assert not has_canonical_score(legacy_payload["score"])
    enriched = ensure_score_present(legacy_payload)
    assert has_canonical_score(enriched["score"])
    assert enriched["score"]["score_version"] == SCORE_VERSION


def test_score_reader_idempotente_para_artifact_ja_canonico():
    from backend.app.services.score_reader import ensure_score_present

    canonical = {
        "score": {
            "valor": 7.5,
            "classificacao": "Bom",
            "score_version": SCORE_VERSION,
            "componentes": [{"code": "x", "status": "emitted"}],
        },
        "ratios": {},
    }
    out = ensure_score_present(canonical)
    assert out is canonical  # no-op idempotent


def test_score_reader_devolve_payload_intacto_se_inputs_ausentes():
    from backend.app.services.score_reader import ensure_score_present

    payload = {"score": {"valor": 0, "classificacao": "N/D"}}
    out = ensure_score_present(payload)
    assert out is payload


def test_score_reader_recompute_produz_score_canonico_completo():
    """Recompute via ScoreReader bate com `FinancialScoreCalculator.calculate()` direto."""
    from backend.app.services.score_reader import ensure_score_present

    inputs = _sample_inputs()
    direct = _calc().calculate(**inputs)
    payload = {"score": {"valor": 0, "classificacao": "stale"}, **inputs}
    enriched = ensure_score_present(payload)
    assert enriched["score"]["valor"] == direct["valor"]
    assert enriched["score"]["score_version"] == direct["score_version"]
