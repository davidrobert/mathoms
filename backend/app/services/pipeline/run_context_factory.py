"""Hidratação canônica do ``WorkspaceContext`` para executores de stage.

Fonte única dos três caminhos de execução — Celery (``pipeline_task``), modo
HTTP (``pipeline-service``) e CLI ``run-stage`` (A3.cli): ``DBConfigStore`` +
overrides (ADR-134/180), resolvers DB (ADR-215/219/222), ``imoveis_no_if``
(ADR-222), budget hooks LLM (ADR-173) e materialização opcional de
``tarefas.md`` (ADR-077/180 — consumida pelo E5). Sem hidratação, o stage
roda com config de disco — a degradação semântica silenciosa registrada no
§Escopo deferido da ADR-303.

Invariantes:

- **Não há snapshot-isolamento de config entre stages — nem no Celery.** A
  sessão long-lived dá read-committed com estabilização por identity map, e o
  ``DBConfigStore`` consulta sob demanda; edição de config no meio de um run
  pode ser vista por stages subsequentes em qualquer executor. Não "corrigir".
- **A sessão de config é read-only durante o stage** (nunca commitar) e
  coexiste com a sessão de escrita do ``DBArtifactStore``
  (``artifact_session_factory``) — só o artifact store escreve enquanto o
  stage roda (ADR-256). Fechamento: artifact store primeiro (commit/rollback
  libera o write-lock), ``HydratedContext.close()`` depois — ele grava o
  ``LLMCallLog`` adiado, que precisa do lock livre (ADR-173 §Emenda 2026-10-08).
- Este módulo **não importa celery**.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.services.db_economic_assumptions_resolver import (
    DBEconomicAssumptionsResolver,
)
from backend.app.services.db_property_identity_resolver import (
    DBPropertyIdentityResolver,
)
from backend.app.services.db_property_overrides_resolver import (
    DBPropertyOverridesResolver,
)
from backend.app.services.db_property_supersession_writer import (
    DBPropertySupersessionWriter,
)
from backend.app.services.db_tributario_section_resolver import (
    DBTributarioSectionResolver,
)
from backend.app.services.institution_catalog_provider import (
    DBInstitutionCatalogProvider,
)
from backend.app.services.pipeline.pipeline_adapter import (
    build_config_overrides_from_db,
    build_config_store,
)

if TYPE_CHECKING:
    from pipeline.run_deadline import RunDeadline

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HydratedContext:
    """Contexto hidratado + a sessão read-only que respalda config/resolvers."""

    ctx: Any
    config_store_session: Session

    def close(self) -> None:
        """Grava o ``LLMCallLog`` adiado e fecha a sessão de config — SEMPRE após o artifact store fechar."""
        flush_deferred_llm_call_log(self.ctx)
        try:
            self.config_store_session.close()
        except Exception as exc:
            logger.warning("config_store_session close failed: %s", exc)


def flush_deferred_llm_call_log(ctx) -> None:
    """Grava o ``LLMCallLog`` adiado do run — chamar só com a sessão do stage FECHADA."""
    # getattr: ctx de teste/executor sem hooks, ou hooks fake sem buffer.
    flush = getattr(getattr(ctx, "llm_call_hooks", None), "flush_call_log", None)
    if flush is not None:
        flush()


def _default_session_factory() -> Session:
    from backend.app.core.database import SyncSessionLocal

    return SyncSessionLocal()


def _read_imoveis_no_if(ws_id: str, session: Session) -> bool:
    """ADR-222: `imoveis_no_if` per-workspace; default True quando ausente."""
    from backend.app.models.workspace import Workspace

    row = session.execute(
        select(Workspace.imoveis_no_if).where(Workspace.id == ws_id)
    ).scalar_one_or_none()
    return True if row is None else bool(row)


def _read_residencia_status(ws_id: str, session: Session) -> Optional[str]:
    """[[ADR-215]] `residencia_status`; ``None`` quando o workspace não existe."""
    from backend.app.models.workspace import Workspace

    return session.execute(
        select(Workspace.residencia_status).where(Workspace.id == ws_id)
    ).scalar_one_or_none()


def _workspace_flags(ws_id: str, session: Session) -> dict:
    """Escolhas do workspace que o E5 lê ([[ADR-222]] · [[ADR-215]] · [[ADR-439]])."""
    return {
        "imoveis_no_if": _read_imoveis_no_if(ws_id, session),
        "residencia_status": _read_residencia_status(ws_id, session),
    }


def _db_resolvers(session: Session) -> dict:
    return {
        "property_identity_resolver": DBPropertyIdentityResolver(session=session),
        "property_supersession_writer": DBPropertySupersessionWriter(session=session),
        "economic_assumptions_resolver": DBEconomicAssumptionsResolver(session=session),
        "property_overrides_resolver": DBPropertyOverridesResolver(session=session),
        # A33.l8 (ADR-137): catálogo de instituições p/ injection nos prompts LLM.
        "institution_catalog_provider": DBInstitutionCatalogProvider(session=session),
        # RV3-11 (A40.l9): seção tributária resolvida em stage-time (E5.N), do
        # último run COM E4 — o goals.json de t=0 fica só como fallback.
        "tributario_section_resolver": DBTributarioSectionResolver(session=session),
    }


def _build_ctx(
    ws_id: str,
    tenant_root: Path,
    run_id: str,
    config_dir: Optional[Path] = None,
    *,
    session: Session,
):
    from pipeline.context import WorkspaceContext

    return WorkspaceContext.for_tenant(
        tenant_root,
        config=build_config_overrides_from_db(ws_id, db=session),
        config_dir=config_dir,
        pipeline_run_id=run_id,
        workspace_id=ws_id,
        config_store=build_config_store(db=session),
        **_workspace_flags(ws_id, session),
        **_db_resolvers(session),
    )


def _attach_llm_budget_hooks(
    ctx, ws_id: str, run_id: str, run_deadline: Optional[RunDeadline] = None
) -> None:
    # ADR-173: hard-stop de budget + LLMCallLog em toda chamada LLM. Budget e
    # gasto vêm do DB + cache Redis, mas em SQLite o service CARREGA as calls
    # adiadas da instância até o flush (§Emenda 2026-10-08) — por isso todo
    # executor grava ao fechar a sessão do stage e no ``close()`` do contexto:
    # instância por-stage (HTTP/CLI) só não perde o pendente porque o close flusha.
    from backend.app.services.llm_budget_service import LLMBudgetService

    ctx.llm_call_hooks = LLMBudgetService.for_pipeline_run(ws_id, run_id, run_deadline=run_deadline)


def _attach_llm_response_cache(ctx) -> None:
    # ADR-307: cache de resposta opt-in no choke-point. Redis se disponível,
    # NoOp caso contrário (miss em tudo — degrada gracioso, ADR-111).
    from backend.app.services.storage.llm_cache import get_default_llm_cache

    ctx.llm_response_cache = get_default_llm_cache()


def _attach_llm_metrics_emitter(ctx) -> None:
    # A33.l7 (ADR-110): métricas OTLP no choke-point. ``None`` sem
    # OTEL_EXPORTER_OTLP_ENDPOINT — opt-in preservado, zero overhead.
    from backend.app.core.llm_metrics import get_llm_metrics_emitter

    ctx.llm_metrics_emitter = get_llm_metrics_emitter()


def materialize_tarefas_md(ws_id: str, ctx) -> None:
    """ADR-077/180: materializa ``tarefas.md`` (consumido pelo E5). Best-effort."""
    from backend.app.core.database import SyncSessionLocal
    from backend.app.services.pipeline.pipeline_adapter import build_tarefas_md_sync

    try:
        with SyncSessionLocal() as db:
            md = build_tarefas_md_sync(ws_id, db=db)
        if not md.strip():
            logger.info("No tasks in DB — keeping original tarefas.md")
            return
        ctx.config_dir.mkdir(parents=True, exist_ok=True)
        (ctx.config_dir / "tarefas.md").write_text(md, encoding="utf-8")
        logger.info("Materialized tarefas.md → %s", ctx.config_dir / "tarefas.md")
    except Exception as exc:  # noqa: BLE001 — best-effort por contrato (ADR-077)
        logger.warning(
            "Failed to materialize tarefas.md for ws=%s: %s. Pipeline uses original (fallback).",
            ws_id,
            exc,
        )


def build_hydrated_context(
    *,
    ws_id: str,
    tenant_root: Path,
    run_id: str,
    config_dir: Optional[Path] = None,
    incremental: bool = False,
    incremental_doc_paths: Optional[List[str]] = None,
    skip_llm: bool = False,
    materialize_tarefas: bool = False,
    session_factory: Optional[Callable[[], Session]] = None,
    run_deadline: Optional[RunDeadline] = None,
) -> HydratedContext:
    """Cria o ``WorkspaceContext`` hidratado. ``config_dir`` explícito vence; ausente → ``<root>/config``."""
    session = (session_factory or _default_session_factory)()
    ctx = _build_ctx(ws_id, tenant_root, run_id, config_dir, session=session)
    ctx.incremental, ctx.incremental_doc_paths = incremental, list(incremental_doc_paths or [])
    # ADR-355: ÚNICO ponto de negação entre o vocabulário do wire (``skip_llm``,
    # negativo, filtra stages) e o do contexto (``llm_calls_allowed``, positivo,
    # governa chamada dentro de stage). Espalhar o ``not`` por executor seria
    # três lugares para inverter a polaridade.
    ctx.llm_calls_allowed = not skip_llm
    _attach_llm_budget_hooks(ctx, ws_id, run_id, run_deadline)
    _attach_llm_response_cache(ctx)
    _attach_llm_metrics_emitter(ctx)
    ctx.ensure_dirs()
    if materialize_tarefas:
        materialize_tarefas_md(ws_id, ctx)
    return HydratedContext(ctx=ctx, config_store_session=session)
