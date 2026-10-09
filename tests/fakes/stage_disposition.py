"""Runners fake da disposição da transação do stage (ADR-357 §6 · ADR-256).

Cada runner grava, pela sessão do stage, um artefato-sonda e uma row de domínio
— o padrão de ``extract_comprovantes_bens``, que faz upsert em ``vehicles`` pelo
``store.session`` — e então entrega, devolve ``{"success": False}``, levanta, ou
deixa o próprio store recusar um payload em ``strict``. São as formas de
não-entrega que ``orchestrator._run_stage`` achata em ``success=False``.

A sonda vive num stage de artefato sem schema: quem decide commit ou rollback é
o stage EXECUTADO, nunca o do artefato. Chave da sonda e modelo do veículo são o
``run_id`` do caso, para cada caso ter o próprio grupo de supersessão.
"""

from __future__ import annotations

import contextlib
import io
import json

PROBE_STAGE = "disposition_probe"
# Stage com schema real (`e2_extract`): em strict, o `write()` recusa sozinho.
STRICT_STAGE = "extract_statements"


def _write_probe(ctx) -> None:
    from backend.app.models.vehicle import Vehicle

    store = ctx.artifact_store
    store.write(PROBE_STAGE, ctx.pipeline_run_id, {"origem": "runner fake"})
    store.session.add(
        Vehicle(
            workspace_id=store.workspace_id,
            placa=ctx.pipeline_run_id[-7:],
            renavam="12345678900",
            marca="X",
            modelo=ctx.pipeline_run_id,
            ano_modelo=2024,
            ano_fabricacao=2024,
        )
    )


def deliver(ctx) -> dict:
    _write_probe(ctx)
    return {"success": True}


def report_failure(ctx) -> dict:
    _write_probe(ctx)
    return {"success": False}


def raise_after_write(ctx) -> None:
    _write_probe(ctx)
    raise RuntimeError("fixture: o stage falha depois de escrever")


def store_rejects_second_write(ctx) -> dict:
    _write_probe(ctx)
    ctx.artifact_store.write(STRICT_STAGE, ctx.pipeline_run_id, {})
    return {"success": True}


def run_cli_cases(cases_json: str) -> list[dict]:
    """Roda ``cli_run_stage.main`` uma vez por caso, com o runner fake no lugar do real."""
    import pipeline.orchestrator as orchestrator
    from pipeline.cli_run_stage import main

    outcomes = []
    for stage, runner, argv in json.loads(cases_json):
        orchestrator._STAGE_RUNNERS[stage] = (__name__, runner)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(argv)
        outcomes.append({"exit_code": code, "stdout": stdout.getvalue()})
    return outcomes
