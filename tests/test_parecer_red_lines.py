"""Eval determinístico das red lines do parecer (ADR-300) — roda no PR gate sem
ANTHROPIC_API_KEY. Prova que cada red line dispara quando deve (envenenado) e
silencia quando não deve (borderline-limpo), + gate de completude por red line.
"""

from __future__ import annotations

import pytest

from backend.app.services.parecer_red_lines import RED_LINES, check_red_lines
from tests.fixtures.parecer_red_lines import CLEAN, POISONED


def _triggered(result) -> dict[str, str]:
    return {v.rl_id: v.severity for v in result.violations}


@pytest.mark.parametrize("fx", POISONED, ids=lambda f: f.fixture_id)
def test_red_line_fires_on_poisoned(fx):
    """Output envenenado dispara a red line CERTA na severidade esperada."""
    result = check_red_lines(fx.output, fx.e5)
    triggered = _triggered(result)
    assert fx.expected_rl_id in triggered, f"{fx.fixture_id}: {fx.expected_rl_id} não disparou"
    assert triggered[fx.expected_rl_id] == fx.expected_severity


@pytest.mark.parametrize("fx", CLEAN, ids=lambda f: f.fixture_id)
def test_red_line_silent_on_clean(fx):
    """Anti-falso-positivo: borderline-limpo NÃO dispara a red line alvo."""
    result = check_red_lines(fx.output, fx.e5)
    assert fx.rl_id not in _triggered(result), f"{fx.fixture_id}: {fx.rl_id} disparou (FP)"


def test_all_seven_red_lines_have_coverage():
    """Gate de completude: cada RLn tem ≥2 envenenadas + ≥1 limpa. Sem isso,
    adicionar red line sem fixture passa silencioso."""
    rl_ids = {rl.id for rl in RED_LINES}
    assert len(rl_ids) == 7
    for rl_id in rl_ids:
        poisoned = [f for f in POISONED if f.expected_rl_id == rl_id]
        clean = [f for f in CLEAN if f.rl_id == rl_id]
        assert len(poisoned) >= 2, f"{rl_id}: <2 fixtures envenenadas"
        assert len(clean) >= 1, f"{rl_id}: sem fixture borderline-limpa"


def test_clean_output_triggers_nothing():
    """Controle global: parecer saudável + E5 saudável → zero violações."""
    from tests.fixtures.parecer_red_lines import _e5, _output

    result = check_red_lines(_output(), _e5())
    assert result.violations == ()
    assert result.block_reason() is None
