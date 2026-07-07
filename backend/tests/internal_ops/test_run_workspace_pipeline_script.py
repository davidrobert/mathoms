"""Testes do CLI dev `run_workspace_pipeline` (make pipeline-run).

Vive em internal_ops/ porque o fluxo --reset consome
`reset_workspace_from_stage` (audit em tabela, ADR-309).
O caminho de trigger (Celery dispatch) é coberto pelos testes de
`application/pipeline_run` — aqui valida-se parsing, resolução de
workspace e a orquestração do reset.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.scripts.run_workspace_pipeline import (
    build_request,
    find_workspace_or_list,
    maybe_reset,
    parse_args,
)
from backend.tests.factories import make_run, make_user, make_workspace


def test_parse_args_defaults_to_deterministic_run() -> None:
    args = parse_args(["ws-uuid"])
    body = build_request(args)
    assert body.skip_llm is True
    assert body.from_stage is None
    assert body.incremental is False
    assert args.reset is False


def test_parse_args_with_llm_and_from_stage() -> None:
    args = parse_args(["ws-uuid", "--with-llm", "--from-stage", "reconcile_transactions"])
    body = build_request(args)
    assert body.skip_llm is False
    assert body.from_stage == "reconcile_transactions"


def test_build_request_rejects_unknown_stage() -> None:
    args = parse_args(["ws-uuid", "--from-stage", "stage_inexistente"])
    with pytest.raises(PydanticValidationError):
        build_request(args)


@pytest.mark.asyncio
async def test_find_workspace_resolves_existing(db) -> None:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    await db.commit()

    found = await find_workspace_or_list(db, ws.id)
    assert found is not None
    assert found.id == ws.id


@pytest.mark.asyncio
async def test_find_workspace_missing_lists_available(db, capsys) -> None:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    await db.commit()

    found = await find_workspace_or_list(db, "nao-existe")
    assert found is None
    out = capsys.readouterr().out
    assert "não encontrado" in out
    assert ws.id in out


async def _seed_artifacts(db, ws) -> None:
    run = await make_run(db, workspace=ws)
    for stage in ["extract_statements", "reconcile_transactions", "analyze_finances"]:
        db.add(
            PipelineArtifact(
                workspace_id=ws.id,
                pipeline_run_id=run.id,
                stage=stage,
                artifact_key=f"key_{stage}",
                content_json={"foo": "bar"},
            )
        )
    await db.flush()


async def _remaining_stages(db, ws) -> set[str]:
    stmt = select(PipelineArtifact.stage).where(PipelineArtifact.workspace_id == ws.id)
    return set((await db.execute(stmt)).scalars())


@pytest.mark.asyncio
async def test_maybe_reset_assume_yes_deletes_cascade(db) -> None:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    await _seed_artifacts(db, ws)
    await db.commit()

    ok = await maybe_reset(
        db, workspace_id=ws.id, from_stage="reconcile_transactions", assume_yes=True
    )
    assert ok is True
    assert await _remaining_stages(db, ws) == {"extract_statements"}


@pytest.mark.asyncio
async def test_maybe_reset_declined_preserves_artifacts(db, monkeypatch) -> None:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    await _seed_artifacts(db, ws)
    await db.commit()

    monkeypatch.setattr("builtins.input", lambda _: "n")
    ok = await maybe_reset(
        db, workspace_id=ws.id, from_stage="reconcile_transactions", assume_yes=False
    )
    assert ok is False
    assert await _remaining_stages(db, ws) == {
        "extract_statements",
        "reconcile_transactions",
        "analyze_finances",
    }
