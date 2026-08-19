"""CTO-3 (§r7) — o teste de LOOP: quem retém o run é `validation.valid`."""

# O teste que guardava a promessa da ADR-393 D4 afirmava pertinência em conjunto
# (`code not in BLOCKING_CODES`) e nunca exercitava o loop. Aqui o
# `_execute_stages_loop` roda de verdade e devolve `paused_for_review` — o
# observável. Os quatro casos cruzam `valid` × `code` e mostram que o eixo que
# decide é `valid`, não o vocabulário. Baseline do RV7-03/DE-3: quando o
# predicado virar `any(code ∈ BLOCKING_CODES)`, os dois casos marcados INVERTE
# mudam de valor, e mudá-los é ato deliberado.

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pytest

from backend.app.tasks.pipeline_task import _execute_stages_loop

_ADVISORY = "domain.balance_gap"
_BLOCKING = "extract.missing_required_field"
_STAGE = "reconcile_transactions"


@dataclass
class _StageResult:
    success: bool = True
    error: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


def _detail(*, valid: bool, code: str) -> dict:
    return {
        "validation": {
            "valid": valid,
            "errors": [] if valid else ["boom"],
            "review_reasons": [{"code": code, "message": "m", "occurrence_count": 1}],
        }
    }


class _Ctx:
    artifact_store = None


_M = "backend.app.tasks.pipeline_task."
# Colaboradores de I/O do loop: o alvo do teste é o RAMO, não a persistência.
_SILENCED = (
    "_record_stage_running",
    "_commit_and_close_artifact_session",
    "_rollback_and_close_artifact_session",
)


@contextmanager
def _loop_harness():
    with ExitStack() as stack:
        stack.enter_context(patch(_M + "_is_cancelled", return_value=False))
        stack.enter_context(patch(_M + "_find_stage_completion_marker", return_value=None))
        stack.enter_context(patch(_M + "_open_artifact_session", return_value=(None, None)))
        stack.enter_context(patch(_M + "_record_stage_result", return_value=True))
        for name in _SILENCED:
            stack.enter_context(patch(_M + name))
        yield stack.enter_context(patch(_M + "_record_stage_needs_review"))


def _run_loop(detail: dict) -> bool:
    """Roda o loop com 1 stage e devolve `paused_for_review`."""
    with _loop_harness() as pause:
        _, paused = _execute_stages_loop(
            _Ctx(),
            [_STAGE],
            "run-1",
            "ws-1",
            skip_llm=False,
            stop_on_error=True,
            tier="premium",
            llm_stages=frozenset(),
            run_stage_fn=lambda _c, _s: _StageResult(detail=detail),
        )
        assert paused == (pause.call_count == 1), "pausa e registro têm de andar juntos"
    return paused


@pytest.mark.parametrize(
    "valid,code,esperado,nota",
    [
        (True, _ADVISORY, False, "advisory com valid=True: não pausa"),
        (False, _ADVISORY, True, "INVERTE sob RV7-03: hoje advisory PAUSA se valid=False"),
        (True, _BLOCKING, False, "INVERTE sob RV7-03: hoje blocking NÃO pausa se valid=True"),
        (False, _BLOCKING, True, "blocking com valid=False: pausa"),
    ],
)
def test_quem_retem_o_run_e_validation_valid(valid, code, esperado, nota) -> None:
    assert _run_loop(_detail(valid=valid, code=code)) is esperado, nota


def test_stage_sem_bloco_validation_nunca_pausa() -> None:
    """Default `valid=True` protege todo stage que não declara validação."""
    assert _run_loop({}) is False
