"""Cobertura de `dev/measure_conservation_gate.py` (guarda pré-execução A36.l3).

Prova, com E5 sintéticos zero-PII, que a medição classifica corretamente cada
cenário sob os gates de severidade — em especial que a re-tag core captura os
checks de conservação numérica (CV2/CV3/CV6) que o gate de hoje deixa passar, e
que os checks de render (CV9/CV10) saem do gate de pausa.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "measure_conservation_gate", _REPO / "dev" / "measure_conservation_gate.py"
)
assert _spec and _spec.loader
mcg = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = mcg  # @dataclass precisa do módulo em sys.modules ao processar
_spec.loader.exec_module(mcg)

_REQUIRED_CHARTS = (
    "score_gauge",
    "patrimonio_doughnut",
    "alocacao_atual_vs_alvo",
    "fluxo_mensal",
    "receita_bar",
    "receita_despesa_mensal",
    "despesas_doughnut",
)


def _clean_e5() -> dict:
    """E5 sintético consistente — passa todos os checks relevantes de gate."""
    return {
        "score": {"valor": 7.0, "classificacao": "x", "componentes": [{"nota": 7.0, "peso": 1.0}]},
        "patrimonio": {
            "bruto": 1000.0,
            "investivel_efetivo": 500.0,
            "composicao": [{"valor": 1000.0}],
        },
        "fluxo_caixa": {
            "receita_total": 1000.0,
            "despesa_total": 600.0,
            "fluxo_liquido": 400.0,
            "receita_recorrente": 1000.0,
        },
        "ratios": {"taxa_poupanca_recorrente_pct": 40.0},
        "goals": {
            "if_meta": 1000.0,
            "if_trs": 4.0,
            "if_trs_monthly_value": (1000 * 4 / 100) / 12,
            "if_pct": 50.0,
        },
        "endividamento": {"total_dividas": 0.0, "percentual_patrimonio": 0.0},
        "reserva_emergencia": {
            "total_liquida": 6000.0,
            "despesas_mensais": 1000.0,
            "cobertura_meses": 6.0,
        },
        "narrativas": {
            "summaries": {f"s{i}": "texto" for i in range(1, 11)},
            "charts": {c: {"context": "c", "conclusion": "f"} for c in _REQUIRED_CHARTS},
        },
        "tarefas": [{"t": "x", "p": "alta"}],
        "diagnostico_comportamental": [{"padrao": "x"}],
    }


def _failed(e5: dict) -> frozenset[str]:
    return frozenset(r.check_id for r in mcg.run_cross_validation(e5) if not r.passed)


def test_clean_run_pauses_nowhere() -> None:
    c = mcg.classify("clean", _failed(_clean_e5()))
    assert not c.pauses_today and not c.pauses_core and not c.pauses_core_borderline


def test_cv2_violation_is_a_new_pause_under_core() -> None:
    """Composição ≠ bruto (>5%): não pausa hoje (CV2 é warning), pausa sob core."""
    e5 = _clean_e5()
    e5["patrimonio"]["composicao"] = [{"valor": 1200.0}]  # 20% vs bruto 1000
    c = mcg.classify("cv2", _failed(e5))
    assert "CV2" in c.failed
    assert not c.pauses_today
    assert c.pauses_core


def test_cv1_violation_pauses_today_and_core() -> None:
    """Score inconsistente (CV1 é error hoje): pausa em ambos."""
    e5 = _clean_e5()
    e5["score"] = {"valor": 5.0, "classificacao": "x", "componentes": [{"nota": 9.0, "peso": 1.0}]}
    c = mcg.classify("cv1", _failed(e5))
    assert "CV1" in c.failed
    assert c.pauses_today and c.pauses_core


def _render_regression_e5() -> dict:
    """Narrativas ENTREGUES mas incompletas — regressão de render de verdade."""
    # A40.l18 mudou a forma deste caso. Antes era `narrativas: {}` (ausentes),
    # mas ausência agora SKIPA a classe de render (CV9/CV10/CV14): sem narrativa
    # o stage a montante degradou, e reportar render vermelho conflacionaria
    # "não veio" com "regressou". O caso que este teste quer medir é o segundo.
    e5 = _clean_e5()
    e5["narrativas"]["charts"].pop(_REQUIRED_CHARTS[0])
    return e5


def test_render_only_leaves_pause_gate_under_core() -> None:
    """Narrativas incompletas (CV9/CV10 error): pausa hoje, sai do gate sob core."""
    c = mcg.classify("render", _failed(_render_regression_e5()))
    assert {"CV9", "CV10"} & c.failed
    assert c.pauses_today
    assert not c.pauses_core


def test_measure_aggregates_deltas() -> None:
    """O agregado separa novos-a-pausar (conservação) de deixam-de-pausar (render)."""
    clean = _clean_e5()
    cv2 = _clean_e5()
    cv2["patrimonio"]["composicao"] = [{"valor": 1200.0}]
    render = _render_regression_e5()

    report = mcg.measure([("clean", clean), ("cv2", cv2), ("render", render)])
    assert report.total == 3
    assert report.pauses_today == 1  # só render
    assert report.pauses_core == 1  # só cv2
    assert report.newly_pausing == ["cv2"]
    assert report.no_longer_pausing == ["render"]


def test_unparseable_e5_is_counted_not_raised() -> None:
    """E5 de shape inválido é registrado como não-validável, não aborta o lote."""
    report = mcg.measure([("bad", {"score": {"componentes": [{"nota": "abc", "peso": 1}]}})])
    assert report.classifications == []
    assert len(report.unparseable) == 1
    assert report.unparseable[0][0] == "bad"
