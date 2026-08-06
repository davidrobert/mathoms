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


# ───── resolução por email do dono (make pipeline-run WS=<email>) ─────


@pytest.mark.asyncio
async def test_resolve_por_email_do_dono(db) -> None:
    """`WS=<email>` dispensa consultar o uuid antes de cada run."""
    owner = await make_user(db, email="dono-unico@exemplo.test")
    ws = await make_workspace(db, owner=owner)

    found = await find_workspace_or_list(db, "dono-unico@exemplo.test")

    assert found is not None and found.id == ws.id


@pytest.mark.asyncio
async def test_email_ambiguo_recusa_em_vez_de_escolher(db, capsys) -> None:
    """Ambiguidade NÃO escolhe em silêncio — este CLI aceita `--reset`."""
    # Mutação que mata: copiar o `LIMIT 1` da skill de review. Ela só LÊ; aqui
    # a operação muta (deleta artifacts), então escolher 1 de N é footgun.
    owner = await make_user(db, email="dono-com-dois@exemplo.test")
    await make_workspace(db, owner=owner, name="Primeiro")
    await make_workspace(db, owner=owner, name="Segundo")

    found = await find_workspace_or_list(db, "dono-com-dois@exemplo.test")

    assert found is None
    assert "desambigue com WS=<uuid>" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_email_inexistente_nao_confunde_com_uuid(db, capsys) -> None:
    """Email sem match reporta ausência de DONO, não de workspace."""
    found = await find_workspace_or_list(db, "ninguem@exemplo.test")

    assert found is None
    assert "Nenhum workspace com dono" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_uuid_continua_funcionando(db) -> None:
    """O caminho antigo não regride — `@` é o único discriminador."""
    owner = await make_user(db, email="por-uuid@exemplo.test")
    ws = await make_workspace(db, owner=owner)

    found = await find_workspace_or_list(db, ws.id)

    assert found is not None and found.id == ws.id
