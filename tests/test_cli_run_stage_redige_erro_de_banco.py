"""ADR-441 D2 — o stderr do `run-stage` não carrega valor do banco.

O shell Go repassa o stderr do filho e devolve o `_fail(...)` no corpo do 503. Duas
portas: o `CliEnvironmentError` que embrulha a hidratação (`f"...: {exc}" from exc`) e a
exceção não tratada, cujo traceback o Python imprimiria cru.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from pipeline import cli_run_stage
from pipeline.observability.failure_text import DATABASE_VALUES_OMITTED
from tests.unit.pipeline.test_failure_text import _ENDERECO, _TITULAR, _unique_violation

_ARGV = [
    "run-stage",
    "consolidate_baseline",
    "--workspace",
    "/tmp/ws-sintetico",
    "--run-id",
    "run-1",
    "--workspace-id",
    "ws-1",
]


def _sem_valor(texto: str) -> bool:
    return _ENDERECO not in texto and _TITULAR not in texto


def _hidratacao_que_quebra_no_banco(_stage, _args):
    try:
        raise _unique_violation()
    except IntegrityError as exc:
        raise cli_run_stage.CliEnvironmentError(
            f"falha ao hidratar o WorkspaceContext (ADR-303 D4): {exc}"
        ) from exc


def test_erro_de_ambiente_que_embrulha_o_banco_sai_redigido(capsys):
    with patch.object(cli_run_stage, "_execute_run_stage", _hidratacao_que_quebra_no_banco):
        code = cli_run_stage.main(_ARGV)

    err = capsys.readouterr().err
    payload = json.loads(err.strip().splitlines()[-1])
    assert code == cli_run_stage.EXIT_USAGE
    assert payload["error"] == "environment"
    assert payload["message"].startswith("CliEnvironmentError: UniqueViolation")
    assert DATABASE_VALUES_OMITTED in payload["message"]
    assert _sem_valor(err), err


def test_excecao_de_banco_nao_tratada_sai_so_com_frames(capsys):
    with patch.object(cli_run_stage, "_execute_run_stage", side_effect=_unique_violation()):
        code = cli_run_stage.main(_ARGV)

    err = capsys.readouterr().err
    assert code == cli_run_stage.EXIT_STAGE_FAILED
    assert "Traceback (most recent call last)" in err
    assert _sem_valor(err), err


def test_excecao_sem_banco_mantem_o_traceback_completo(capsys):
    """Controle: a semântica do traceback não tratado segue igual fora do banco."""
    with patch.object(cli_run_stage, "_execute_run_stage", side_effect=RuntimeError("boom")):
        code = cli_run_stage.main(_ARGV)

    err = capsys.readouterr().err
    assert code == cli_run_stage.EXIT_STAGE_FAILED
    assert "RuntimeError: boom" in err
