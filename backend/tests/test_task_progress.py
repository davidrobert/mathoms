"""Testes de `task_progress_service` (ADR-074 §F8.3).

Cobre:
- Detecção de task trackable (heurística aporte mensal)
- Parsing de valor BRL do title (R$ 20k, R$ 20.000, 20k/mês)
- Cálculo de % executado quando temos transactions
- Is_trackable=False para task não-aporte
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from backend.app.services.task_progress_service import (
    _current_month_period,
    _parse_brl_target,
    compute_progress,
)
from backend.tests import factories

# ─── Parsing de target BRL ──────────────────────────────────────────────


def test_parse_brl_target_with_k_suffix():
    assert _parse_brl_target("Configurar aporte R$20k/mês") == 20000.0


def test_parse_brl_target_with_full_number():
    assert _parse_brl_target("Aporte R$ 20.000/mês") == 20000.0


def test_parse_brl_target_with_decimal_brl():
    assert _parse_brl_target("Aporte R$ 1.234,56") == 1234.56


def test_parse_brl_target_with_short_k_no_dollar():
    assert _parse_brl_target("aportar 50k no mês") == 50000.0


def test_parse_brl_target_returns_none_without_value():
    assert _parse_brl_target("Consultar AccountTech") is None


def test_parse_brl_target_treats_dot_thousand_correctly():
    """Bug guard: 'R$ 1.800' é formato BRL (ponto=milhar), deve ser 1800 e
    não 1.8. Descoberto na validação contra tarefas reais da Ferreira Campos."""
    assert _parse_brl_target("Iniciar aportes PGBL R$1.800/mês") == 1800.0
    assert _parse_brl_target("PGBL R$ 1.800,00 mensal") == 1800.0


def test_parse_brl_target_preserves_decimal_with_non_3_digit_suffix():
    """'R$ 1.5' tem só 1 dígito após o ponto → decimal genuíno."""
    assert _parse_brl_target("Compra R$ 1.5 milhão") == 1.5


def test_parse_brl_target_picks_first_value():
    """Task com múltiplos valores — pega o primeiro (geralmente o alvo)."""
    title = "Configurar aporte R$ 20.000/mês (R$10k Cofrinhos + R$5k IPCA)"
    assert _parse_brl_target(title) == 20000.0


# ─── Period helpers ─────────────────────────────────────────────────────


def test_current_month_period_returns_first_and_last_day():
    start, end = _current_month_period()
    assert start.day == 1
    assert end.month == start.month
    assert end.year == start.year
    # Último dia do mês (28-31)
    assert 28 <= end.day <= 31


# ─── compute_progress ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_progress_not_trackable_for_non_aporte_task(db):
    ws = await factories.make_workspace(db)
    task = await factories.make_task(
        db, workspace=ws, title="Entregar IRPF 2026", category="Tributario"
    )
    progress = compute_progress(task)
    assert progress.is_trackable is False


@pytest.mark.asyncio
async def test_progress_trackable_for_aporte_task(db):
    ws = await factories.make_workspace(db)
    task = await factories.make_task(
        db,
        workspace=ws,
        title="Configurar aporte R$ 20.000/mês",
        category="Invest",
    )
    # Sem tenant_root → executed=0 (best-effort). Target detectado via title.
    progress = compute_progress(task)
    assert progress.is_trackable is True
    assert progress.target_brl == 20000.0
    assert progress.executed_brl == 0.0
    assert progress.matched_transactions_count == 0
    assert progress.percent_executed == 0.0


@pytest.mark.asyncio
async def test_progress_trackable_without_extractable_target(db):
    ws = await factories.make_workspace(db)
    task = await factories.make_task(
        db,
        workspace=ws,
        title="Configurar aporte mensal automatizado",
        category="Orcamento",
    )
    progress = compute_progress(task)
    assert progress.is_trackable is True
    # Sem valor no título → target None; percent também None
    assert progress.target_brl is None
    assert progress.percent_executed is None


@pytest.mark.asyncio
async def test_progress_ignores_category_outside_invest_orcamento(db):
    ws = await factories.make_workspace(db)
    task = await factories.make_task(
        db,
        workspace=ws,
        title="Aporte mensal para seguro",
        category="Seguros",
    )
    progress = compute_progress(task)
    assert progress.is_trackable is False


@pytest.mark.asyncio
async def test_progress_with_fake_tenant_root_does_not_crash(db, tmp_path: Path):
    """Se tenant_root não tem arquivos E4, `load_transactions` retorna []
    e o service degrada graciosamente."""
    ws = await factories.make_workspace(db)
    task = await factories.make_task(
        db,
        workspace=ws,
        title="Configurar aporte R$ 10.000/mês",
        category="Invest",
    )
    progress = compute_progress(task, tenant_root=str(tmp_path))
    assert progress.is_trackable is True
    assert progress.executed_brl == 0.0
    assert progress.percent_executed == 0.0


# ─── compute_progress com transactions sintéticas ──────────────────────


@pytest.mark.asyncio
async def test_progress_matches_transactions_with_keywords(db, tmp_path: Path):
    """Cria fixtures E4 no tmp_path e verifica que transactions com
    descricao match kwayword são somadas."""
    import json

    ws = await factories.make_workspace(db)
    task = await factories.make_task(
        db,
        workspace=ws,
        title="Configurar aporte R$ 20.000/mês",
        category="Invest",
    )

    # Monta estrutura mínima de tenant_root
    e4_dir = tmp_path / "processed" / "E4_unified"
    e4_dir.mkdir(parents=True)

    start, end = _current_month_period()
    in_month_iso = start.replace(day=5).isoformat()
    out_month_iso = date(start.year - 1, 6, 15).isoformat()

    despesas = {
        "dados": {
            "investimentos": [
                {
                    "data": in_month_iso,
                    "descricao": "Aporte Cofrinho Itaú",
                    "valor": -10000.0,
                    "banco": "itau",
                    "categoria": "investimentos",
                },
                {
                    "data": in_month_iso,
                    "descricao": "Tesouro IPCA+ compra",
                    "valor": -5000.0,
                    "banco": "itau",
                    "categoria": "investimentos",
                },
                {
                    "data": out_month_iso,
                    "descricao": "Cofrinho antigo",
                    "valor": -10000.0,
                    "banco": "itau",
                    "categoria": "investimentos",
                },
                {
                    "data": in_month_iso,
                    "descricao": "Supermercado Pão de Açúcar",
                    "valor": -500.0,
                    "banco": "itau",
                    "categoria": "alimentacao",
                },
            ]
        }
    }
    (e4_dir / "despesas-4_unified.json").write_text(json.dumps(despesas), encoding="utf-8")
    # Arquivo de receitas vazio (esperado pelo loader)
    (e4_dir / "receitas-4_unified.json").write_text(json.dumps({"dados": {}}), encoding="utf-8")

    progress = compute_progress(task, tenant_root=str(tmp_path))
    assert progress.is_trackable is True
    assert progress.target_brl == 20000.0
    # Somou os 2 aportes do mês (10k + 5k), ignorou o de mês anterior e o
    # supermercado.
    assert progress.executed_brl == 15000.0
    assert progress.matched_transactions_count == 2
    assert progress.percent_executed == 75.0
    assert "tesouro" in progress.matched_keywords or "cofrinho" in progress.matched_keywords
