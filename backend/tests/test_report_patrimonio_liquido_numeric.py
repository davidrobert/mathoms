"""ADR-283 — ``reports.patrimonio_liquido`` persiste Numeric(18,2) e é lido como Decimal exato (regressão do invariante ADR-090 no read-path da meta IF)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.models.report import Report
from backend.app.services.goal_service import get_latest_report_patrimonio_liquido
from backend.tests import factories


@pytest.mark.asyncio
async def test_patrimonio_liquido_persiste_decimal_exato(db):
    ws = await factories.make_workspace(db)
    report = Report(
        workspace_id=ws.id,
        title="Relatório Numeric",
        period="2026-04",
        patrimonio_liquido=Decimal("12345678.90"),
    )
    db.add(report)
    await db.flush()

    stored = (
        await db.execute(select(Report.patrimonio_liquido).where(Report.id == report.id))
    ).scalar_one()
    assert stored == Decimal("12345678.90")
    assert isinstance(stored, Decimal)


def test_denorm_from_analysis_extrai_score_e_patrimonio():
    score, pl = Report.denorm_from_analysis(
        {"score": {"valor": 6.3}, "patrimonio": {"liquido": 3395285.46}}
    )
    assert score == 6.3
    assert pl == Decimal("3395285.46")
    assert isinstance(pl, Decimal)


def test_denorm_from_analysis_campos_ausentes_ou_malformados():
    assert Report.denorm_from_analysis({}) == (None, None)
    assert Report.denorm_from_analysis({"patrimonio": {"bruto": 1.0}}) == (None, None)
    assert Report.denorm_from_analysis({"score": {"valor": "x"}}) == (None, None)
    assert Report.denorm_from_analysis(None) == (None, None)


@pytest.mark.asyncio
async def test_get_latest_patrimonio_liquido_retorna_decimal(db):
    ws = await factories.make_workspace(db)
    db.add(
        Report(
            workspace_id=ws.id,
            title="Relatório IF",
            period="2026-04",
            patrimonio_liquido=Decimal("1800000.55"),
        )
    )
    await db.flush()

    result = await get_latest_report_patrimonio_liquido(ws.id, db=db)
    assert result == Decimal("1800000.55")
    assert isinstance(result, Decimal)
