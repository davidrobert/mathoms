"""run_workspace_pipeline.py — dispara run do pipeline de um workspace via CLI (dev).

Atalho de debug/dogfood consumido por `make pipeline-run`. Chama o use case
`trigger_pipeline` direto (sem HTTP/auth), preservando as validações de
domínio (meta IF obrigatória, guard de run ativo, resolução de tier). O run
executa no worker Celery — `make dev-up` (ou ao menos redis + dev-worker-up)
precisa estar de pé.

Usage:
    .venv/bin/python -m backend.app.scripts.run_workspace_pipeline <uuid|email-do-dono>
    .venv/bin/python -m backend.app.scripts.run_workspace_pipeline <uuid|email-do-dono> \
        --from-stage reconcile_transactions --with-llm --reset --yes

Default é `skip_llm=True` (só DETERMINISTIC_ORDER) — reprocessar com stages
LLM (E5 narrativas, E6 parecer) tem custo real de API; opte com --with-llm.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import ConflictError, ValidationError
from backend.app.core.database import async_session
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.pipeline import PipelineRunRequest
from backend.app.services.internal_ops.pipeline_reset import reset_workspace_from_stage
from pipeline.stage_spec import FULL_ORDER

_ACTOR = "cli:run_workspace_pipeline"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dispara run do pipeline de um workspace (dev/debug)."
    )
    parser.add_argument(
        "workspace",
        nargs="?",
        default=None,
        metavar="UUID_OU_EMAIL",
        help="UUID do workspace ou email do dono (omita para listar)",
    )
    _add_flags(parser)
    return parser.parse_args(argv)


def _add_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--from-stage",
        default=None,
        help="Reprocessa a partir deste stage (descritivo ou legado, ex.: reconcile_transactions, E3)",
    )
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Inclui stages LLM (custo real de API; default: só determinístico)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Deleta artifacts do stage em diante (ADR-212) antes de disparar",
    )
    parser.add_argument("--yes", action="store_true", help="Não pede confirmação no --reset")


def build_request(args: argparse.Namespace) -> PipelineRunRequest:
    return PipelineRunRequest(
        from_stage=args.from_stage,
        skip_llm=not args.with_llm,
        stop_on_error=True,
        incremental=False,
    )


async def _print_available(db: AsyncSession) -> None:
    rows = (await db.execute(select(Workspace).order_by(Workspace.name))).scalars()
    for ws in rows:
        print(f"   {ws.id}  {ws.name}")


async def _owned_by_email(db: AsyncSession, email: str) -> list[Workspace]:
    result = await db.execute(
        select(Workspace)
        .join(User, User.id == Workspace.owner_id)
        .where(User.email == email)
        .order_by(Workspace.created_at)
    )
    return list(result.scalars())


async def _resolve_by_owner_email(db: AsyncSession, email: str) -> Workspace | None:
    """Email do dono → workspace. Ambiguidade NÃO escolhe em silêncio."""
    # Um dono pode ter N workspaces e este CLI dispara run — com `--reset`, que
    # deleta artifacts. Escolher um dos N caladamente é o footgun. A skill de
    # review usa `LIMIT 1` porque só LÊ; aqui a operação muta.
    rows = await _owned_by_email(db, email)
    if len(rows) == 1:
        return rows[0]
    if not rows:
        print(f"❌ Nenhum workspace com dono {email!r}. Disponíveis:")
        await _print_available(db)
        return None
    print(f"❌ {email!r} tem {len(rows)} workspaces — desambigue com WS=<uuid>:")
    for ws in rows:
        print(f"   {ws.id}  {ws.name}")
    return None


async def find_workspace_or_list(db: AsyncSession, workspace: str | None) -> Workspace | None:
    """Resolve o workspace por UUID ou email do dono; sem match, lista os disponíveis."""
    if workspace and "@" in workspace:
        return await _resolve_by_owner_email(db, workspace)
    if workspace:
        found = await db.get(Workspace, workspace)
        if found is not None:
            return found
        print(f"❌ Workspace {workspace!r} não encontrado. Disponíveis:")
    else:
        print("Workspaces disponíveis (rode com WS=<uuid|email>):")
    await _print_available(db)
    return None


def _confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer in {"y", "yes", "s", "sim"}


async def maybe_reset(
    db: AsyncSession, *, workspace_id: str, from_stage: str, assume_yes: bool
) -> bool:
    """Preview + confirmação + delete de artifacts via reset_workspace_from_stage."""
    preview = await reset_workspace_from_stage(
        db, workspace_id=workspace_id, from_stage=from_stage, actor=_ACTOR, preview=True
    )
    if not preview.ok:
        print(f"❌ Reset falhou: {preview.error} {preview.details}")
        return False
    affected = preview.details["artifacts_affected"]
    print(f"⚠️  Reset a partir de {preview.details['from_stage']}: {affected} artifacts.")
    if affected == 0:
        return True
    if not assume_yes and not _confirm("Deletar e continuar?"):
        print("Abortado — nada foi deletado.")
        return False
    return await _apply_reset(db, workspace_id=workspace_id, from_stage=from_stage)


async def _apply_reset(db: AsyncSession, *, workspace_id: str, from_stage: str) -> bool:
    result = await reset_workspace_from_stage(
        db, workspace_id=workspace_id, from_stage=from_stage, actor=_ACTOR, preview=False
    )
    if not result.ok:
        print(f"❌ Reset falhou: {result.error} {result.details}")
        return False
    await db.commit()
    print(f"   {result.details['artifacts_deleted']} artifacts deletados.")
    return True


async def trigger_run(db: AsyncSession, workspace_id: str, body: PipelineRunRequest) -> int:
    # import lazy: application.pipeline_run → pipeline_service instancia o
    # vault Fernet no load do módulo; manter fora do top-level preserva
    # --help/--list em ambiente sem MATHOMS_FERNET_KEY
    from backend.app.application.pipeline_run import trigger_pipeline

    try:
        run = await trigger_pipeline(workspace_id, body, db=db)
    except (ConflictError, ValidationError) as exc:
        print(f"❌ {exc}")
        return 1
    scope = f"from_stage={body.from_stage}" if body.from_stage else "todos os documentos"
    llm = "sem LLM (determinístico)" if body.skip_llm else "com LLM"
    print(f"✅ Run {run.id} disparado — {scope}, {llm}, tier={run.tier_at_run}.")
    print(f"   Acompanhe: make dev-logs SVC=worker · UI em /workspaces/{workspace_id}")
    return 0


async def _reset_if_requested(
    db: AsyncSession, args: argparse.Namespace, workspace_id: str
) -> bool:
    if not args.reset:
        return True
    reset_from = args.from_stage or FULL_ORDER[0]
    return await maybe_reset(
        db, workspace_id=workspace_id, from_stage=reset_from, assume_yes=args.yes
    )


async def _amain(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        body = build_request(args)
    except PydanticValidationError as exc:
        print(f"❌ Request inválido: {exc}")
        return 1
    async with async_session() as db:
        workspace = await find_workspace_or_list(db, args.workspace)
        if workspace is None:
            return 1
        if not await _reset_if_requested(db, args, workspace.id):
            return 1
        try:
            return await trigger_run(db, workspace.id, body)
        except Exception as exc:  # broker Redis fora do ar deixa o run preso em pending
            print(f"❌ Falha ao despachar para o worker: {exc}")
            print("   Redis/worker de pé? `make dev-up` (ou dev-redis-up + dev-worker-up).")
            return 1


def main() -> None:
    sys.exit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
