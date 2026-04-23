"""Testes de `compute_if_derived` + CRUD (ADR-073).

Testes unitários da função pura (sem DB) e testes de integração do
versionamento (com DB async).

A paridade com o valor histórico de Ferreira Campos (R$ 7.200.000) é
validada em `test_ferreira_campos_parity`.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.app.schemas.goal import IFGoalInputs
from backend.app.services.goal_service import (
    compute_if_derived,
    create_if_goal_version,
    get_current_goal,
    get_goal_history,
)
from backend.tests import factories

# ════════════════════════════════════════════════════════════════════
# Testes da função pura compute_if_derived
# ════════════════════════════════════════════════════════════════════


def _inputs(
    renda: float = 30000,
    trs: float = 5.0,
    retorno: float = 6.0,
    horizonte: int = 15,
    conservadora: float = 4.0,
) -> IFGoalInputs:
    return IFGoalInputs(
        renda_passiva_mensal_brl=renda,
        trs_pct=trs,
        retorno_real_anual_pct=retorno,
        horizonte_anos=horizonte,
        taxa_retirada_conservadora_pct=conservadora,
    )


def test_ferreira_campos_parity():
    """Paridade bit-a-bit com valor histórico do goals.json legado:
    renda 30k, TRS 5% → if_meta 7.200.000.
    """
    out = compute_if_derived(_inputs(renda=30000, trs=5.0))
    assert out.if_meta_brl == 7_200_000.0


def test_if_meta_formula_basic():
    """if_meta = renda × 12 / (trs/100). 20k × 12 / 0.05 = 4.8M."""
    out = compute_if_derived(_inputs(renda=20000, trs=5.0))
    assert out.if_meta_brl == 4_800_000.0


def test_if_meta_conservadora_is_higher():
    """Conservadora usa 4% (vs 5% operacional) → meta maior."""
    out = compute_if_derived(_inputs(renda=30000, trs=5.0, conservadora=4.0))
    assert out.if_meta_conservadora_brl > out.if_meta_brl
    # 30k × 12 / 0.04 = 9.000.000
    assert out.if_meta_conservadora_brl == 9_000_000.0


def test_aporte_necessario_with_positive_return():
    """Com 6% a.a. real em 15 anos, aporte para 7.2M deve ser finito e
    menor que (7.2M / 180 meses) — porque juros ajudam."""
    out = compute_if_derived(_inputs(renda=30000, trs=5.0, retorno=6.0, horizonte=15))
    sem_juros = 7_200_000 / (15 * 12)  # ≈ 40.000
    assert 0 < out.aporte_necessario_mensal_brl < sem_juros


def test_aporte_com_patrimonio_reduz_vs_partindo_de_zero():
    """Com patrimônio inicial, PMT para fechar o gap é menor que o baseline."""
    inp = _inputs(renda=30000, trs=5.0, retorno=6.5, horizonte=10)
    baseline = compute_if_derived(inp)
    ajustado = compute_if_derived(inp, 2_800_000.0)
    assert ajustado.aporte_mensal_com_patrimonio_atual_brl is not None
    assert ajustado.aporte_mensal_com_patrimonio_atual_brl < baseline.aporte_necessario_mensal_brl
    assert ajustado.patrimonio_atual_utilizado_brl == 2_800_000.0


def test_aporte_sem_patrimonio_nao_preenche_campos_opcionais():
    out = compute_if_derived(_inputs())
    assert out.aporte_mensal_com_patrimonio_atual_brl is None
    assert out.patrimonio_atual_utilizado_brl is None


def test_aporte_com_patrimonio_zero_igual_ao_baseline():
    inp = _inputs()
    z = compute_if_derived(inp, 0.0)
    assert z.aporte_mensal_com_patrimonio_atual_brl == z.aporte_necessario_mensal_brl


def test_aporte_zero_quando_patrimonio_ja_projeta_acima_da_meta():
    inp = _inputs(renda=30000, trs=5.0, retorno=6.0, horizonte=15)
    meta = float(compute_if_derived(inp).if_meta_brl)
    n_meses = 15 * 12
    r_m = (1 + 6.0 / 100.0) ** (1 / 12) - 1
    # PV tal que FV = PV * (1+r)^n >= meta
    pv_min = meta / ((1 + r_m) ** n_meses) * 1.02
    out = compute_if_derived(inp, pv_min)
    assert out.aporte_mensal_com_patrimonio_atual_brl == 0.0


def test_aporte_necessario_zero_return():
    """retorno_real = 0 → aporte = meta / n_meses."""
    out = compute_if_derived(_inputs(renda=10000, trs=5.0, retorno=0.0, horizonte=10))
    # meta = 10000 × 12 / 0.05 = 2.400.000
    # aporte = 2.400.000 / 120 = 20.000
    assert out.if_meta_brl == 2_400_000.0
    assert out.aporte_necessario_mensal_brl == pytest.approx(20_000.0, rel=1e-6)


def test_aporte_necessario_short_horizon():
    """Horizonte de 1 ano força aporte alto (pouca composição)."""
    out = compute_if_derived(_inputs(renda=5000, trs=5.0, retorno=6.0, horizonte=1))
    # meta = 5000 × 12 / 0.05 = 1.200.000
    # com 1 ano e 6% a.a., aporte mensal ≈ 97k
    assert out.if_meta_brl == 1_200_000.0
    assert 90_000 < out.aporte_necessario_mensal_brl < 110_000


def test_aporte_necessario_long_horizon_small_contribution():
    """Horizonte longo (30 anos) + retorno alto → aporte pequeno."""
    out = compute_if_derived(_inputs(renda=30000, trs=5.0, retorno=6.0, horizonte=30))
    assert out.if_meta_brl == 7_200_000.0
    # Com 30 anos e 6% a.a. real, aporte ~R$ 7.000-7.500
    assert 6_000 < out.aporte_necessario_mensal_brl < 9_000


def test_trs_higher_yields_lower_meta():
    """Quanto maior a TRS, menor o patrimônio necessário."""
    out_low = compute_if_derived(_inputs(renda=10000, trs=3.0))
    out_med = compute_if_derived(_inputs(renda=10000, trs=5.0))
    out_high = compute_if_derived(_inputs(renda=10000, trs=10.0))
    assert out_low.if_meta_brl > out_med.if_meta_brl > out_high.if_meta_brl


def test_derived_values_are_rounded_to_cents():
    """Outputs arredondados para 2 casas decimais (BRL cents)."""
    out = compute_if_derived(_inputs(renda=7777, trs=5.0, retorno=6.5, horizonte=12))
    # Verifica que todos os derivados são múltiplos de 0.01.
    # Usamos round(val, 2) == val em vez de val*100 para evitar problemas
    # de precisão float (8697.97 * 100 = 869796.9999... em IEEE-754).
    for val in (
        out.if_meta_brl,
        out.aporte_necessario_mensal_brl,
        out.if_meta_conservadora_brl,
    ):
        assert round(val, 2) == val, f"{val} não está arredondado para 2 casas"


def test_edge_case_very_small_return():
    """Retorno quase-zero (0.01%) cai no ramo 'sem juros' graficamente."""
    out = compute_if_derived(_inputs(renda=10000, trs=5.0, retorno=0.01, horizonte=10))
    # Aporte deve ser próximo ao caso sem juros (20.000 sem juros)
    assert 19_000 < out.aporte_necessario_mensal_brl < 20_500


def test_pydantic_rejects_zero_renda():
    """Pydantic não aceita renda_passiva = 0 (>0 constraint)."""
    with pytest.raises(Exception):  # ValidationError
        IFGoalInputs(
            renda_passiva_mensal_brl=0,
            trs_pct=5.0,
            retorno_real_anual_pct=6.0,
            horizonte_anos=10,
        )


def test_pydantic_rejects_negative_horizon():
    with pytest.raises(Exception):
        IFGoalInputs(
            renda_passiva_mensal_brl=10000,
            trs_pct=5.0,
            retorno_real_anual_pct=6.0,
            horizonte_anos=-1,
        )


def test_pydantic_accepts_zero_retorno_real():
    """retorno_real = 0 é válido (cenário pessimista)."""
    inp = IFGoalInputs(
        renda_passiva_mensal_brl=10000,
        trs_pct=5.0,
        retorno_real_anual_pct=0.0,
        horizonte_anos=10,
    )
    out = compute_if_derived(inp)
    assert out.if_meta_brl == 2_400_000.0


# ════════════════════════════════════════════════════════════════════
# Testes de CRUD versionado (precisam de DB)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_first_version(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)

    goal = await create_if_goal_version(
        ws.id,
        _inputs(renda=20000, trs=5.0),
        db=db,
        created_by=user.id,
    )
    await db.commit()

    assert goal.type == "INDEPENDENCIA_FINANCEIRA"
    assert goal.workspace_id == ws.id
    assert goal.effective_to is None
    assert goal.derived_json["if_meta_brl"] == 4_800_000.0


@pytest.mark.asyncio
async def test_editing_creates_new_version_and_closes_old(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)

    g1 = await create_if_goal_version(ws.id, _inputs(renda=20000), db=db, created_by=user.id)
    await db.commit()

    # Segunda edição um dia depois
    eff2 = date.today() + timedelta(days=1)
    g2 = await create_if_goal_version(
        ws.id,
        _inputs(renda=30000),
        db=db,
        created_by=user.id,
        effective_from=eff2,
    )
    await db.commit()

    # Re-lê estado
    await db.refresh(g1)
    await db.refresh(g2)

    # g1 foi fechada com effective_to = eff2 - 1
    assert g1.effective_to == eff2 - timedelta(days=1)
    # g2 é a vigente
    assert g2.effective_to is None
    assert g2.derived_json["if_meta_brl"] == 7_200_000.0


@pytest.mark.asyncio
async def test_get_current_goal_returns_only_active(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)

    await create_if_goal_version(ws.id, _inputs(renda=10000), db=db)
    await db.commit()

    eff2 = date.today() + timedelta(days=1)
    await create_if_goal_version(ws.id, _inputs(renda=20000), db=db, effective_from=eff2)
    await db.commit()

    current = await get_current_goal(ws.id, "INDEPENDENCIA_FINANCEIRA", db=db)
    assert current is not None
    assert current.derived_json["if_meta_brl"] == 4_800_000.0


@pytest.mark.asyncio
async def test_history_ordered_newest_first(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)

    await create_if_goal_version(
        ws.id,
        _inputs(renda=10000),
        db=db,
        effective_from=date(2025, 1, 1),
    )
    await db.commit()
    await create_if_goal_version(
        ws.id,
        _inputs(renda=20000),
        db=db,
        effective_from=date(2026, 1, 1),
    )
    await db.commit()

    hist = await get_goal_history(ws.id, "INDEPENDENCIA_FINANCEIRA", db=db)
    assert len(hist) == 2
    # Mais recente primeiro
    assert hist[0].effective_from == date(2026, 1, 1)
    assert hist[1].effective_from == date(2025, 1, 1)


@pytest.mark.asyncio
async def test_invalid_goal_type_raises(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    with pytest.raises(ValueError, match="inválido"):
        await get_current_goal(ws.id, "INVALID_TYPE", db=db)


@pytest.mark.asyncio
async def test_tenant_isolation_of_goals(db):
    """Multi-tenant isolation — ws_a e ws_b têm goals independentes."""
    user_a = await factories.make_user(db)
    ws_a = await factories.make_workspace(db, owner=user_a)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)

    await create_if_goal_version(ws_a.id, _inputs(renda=10000), db=db)
    await create_if_goal_version(ws_b.id, _inputs(renda=50000), db=db)
    await db.commit()

    current_a = await get_current_goal(ws_a.id, "INDEPENDENCIA_FINANCEIRA", db=db)
    current_b = await get_current_goal(ws_b.id, "INDEPENDENCIA_FINANCEIRA", db=db)

    assert current_a.derived_json["if_meta_brl"] == 2_400_000.0
    assert current_b.derived_json["if_meta_brl"] == 12_000_000.0

    # History não vaza
    hist_a = await get_goal_history(ws_a.id, "INDEPENDENCIA_FINANCEIRA", db=db)
    hist_b = await get_goal_history(ws_b.id, "INDEPENDENCIA_FINANCEIRA", db=db)
    assert len(hist_a) == 1
    assert len(hist_b) == 1
    assert hist_a[0].workspace_id == ws_a.id
    assert hist_b[0].workspace_id == ws_b.id
