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
            "cobertura_despesas_meses": 6.0,
            "taxa_endividamento_pct": 10.0,
        },
        "patrimonio": {"composicao": [{"valor": v} for v in (1_000_000, 800_000, 500_000)]},
        "goals": {"if_pct": 30.0},
    }


def test_calculate_emite_score_version_canonico():
    result = _calc().calculate(**_sample_inputs())
    assert result["score_version"] == SCORE_VERSION


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
