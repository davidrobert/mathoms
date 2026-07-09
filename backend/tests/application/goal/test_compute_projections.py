"""Use cases de ``/compute`` — dry-run dos 4 goal types (sem DB)."""

from __future__ import annotations

from backend.app.application.goal import (
    compute_alocacao_projection,
    compute_aporte_projection,
    compute_dolar_projection,
    compute_if_projection,
)
from backend.app.schemas.dto.goal import (
    AlocacaoGoalComputeRequest,
    AlocacaoGoalInputsV2,
    AporteGoalComputeRequest,
    AporteGoalInputs,
    DolarGoalComputeRequest,
    DolarGoalInputs,
    IFGoalComputeRequest,
    IFGoalInputs,
)


def _if_inputs() -> IFGoalInputs:
    return IFGoalInputs(
        renda_passiva_mensal_brl=30_000,
        trs_pct=5.0,
        retorno_real_anual_pct=5.0,
        horizonte_anos=20,
    )


def test_compute_if_projection_without_patrimonio_omits_progress():
    resp = compute_if_projection(IFGoalComputeRequest(inputs=_if_inputs()))

    assert resp.derived.if_meta_brl > 0
    assert resp.percentual_conquistado is None
    assert resp.faltante_brl is None


def test_compute_if_projection_with_patrimonio_includes_progress():
    resp = compute_if_projection(
        IFGoalComputeRequest(inputs=_if_inputs(), patrimonio_atual_brl=720_000)
    )

    # 720_000 / 7_200_000 × 100 = 10%
    assert resp.percentual_conquistado == 10.0
    assert resp.faltante_brl == 6_480_000.0


def test_compute_aporte_projection_computes_anual_and_pct():
    resp = compute_aporte_projection(
        AporteGoalComputeRequest(
            inputs=AporteGoalInputs(
                meta_aporte_mensal_brl=10_000,
                distribuicao={"acoes": 6_000, "renda_fixa": 4_000},
            )
        )
    )

    assert resp.derived.aporte_anual_brl == 120_000
    assert resp.derived.distribuicao_pct == {"acoes": 60.0, "renda_fixa": 40.0}


def test_compute_dolar_projection_applies_default_cambio():
    resp = compute_dolar_projection(
        DolarGoalComputeRequest(
            inputs=DolarGoalInputs(meta_usd=50_000, aporte_mensal_brl=5_000),
        )
    )

    assert resp.cambio_utilizado == 5.70
    assert resp.derived.horizonte_estimado_meses > 0


def test_compute_dolar_projection_respects_explicit_cambio():
    resp = compute_dolar_projection(
        DolarGoalComputeRequest(
            inputs=DolarGoalInputs(meta_usd=50_000, aporte_mensal_brl=5_000),
            cambio_brl_usd=6.0,
        )
    )

    assert resp.cambio_utilizado == 6.0


def test_compute_alocacao_projection_flags_sum_100_valid():
    resp = compute_alocacao_projection(
        AlocacaoGoalComputeRequest(
            inputs=AlocacaoGoalInputsV2(
                rf_pos_pct=20,
                rf_pre_pct=10,
                rf_ipca_pct=10,
                acoes_br_pct=25,
                acoes_int_pct=15,
                fiis_pct=10,
                caixa_pct=10,
            )
        )
    )

    assert resp.valido is True
    assert resp.derived.soma_percentuais == 100.0


# Nota: soma ≠ 100 é bloqueada no validador do DTO ``AlocacaoGoalInputsV2``;
# o flag ``valido`` é defensivo caso alguém construa o modelo via
# ``model_construct`` (bypass) ou evolução futura do validador — preservado
# por paridade com router legado.
