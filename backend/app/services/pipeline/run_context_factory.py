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
  libera o write-lock), ``HydratedContext.close()`` depois.
- Este módulo **não importa celery**.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional

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
from backend.app.services.institution_catalog_provider import (
    DBInstitutionCatalogProvider,
)
from backend.app.services.pipeline.pipeline_adapter import (
    build_config_overrides_from_db,
    build_config_store,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HydratedContext:
    """Contexto hidratado + a sessão read-only que respalda config/resolvers."""

    ctx: Any
    config_store_session: Session

    def close(self) -> None:
        """Fecha a sessão de config — chamar SEMPRE após o artifact store fechar."""
        try:
            self.config_store_session.close()
        except Exception as exc:
            logger.warning("config_store_session close failed: %s", exc)


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


def _db_resolvers(session: Session) -> dict:
    return {
        "property_identity_resolver": DBPropertyIdentityResolver(session=session),
        "economic_assumptions_resolver": DBEconomicAssumptionsResolver(session=session),
        "property_overrides_resolver": DBPropertyOverridesResolver(session=session),
        # A33.l8 (ADR-137): catálogo de instituições p/ injection nos prompts LLM.
        "institution_catalog_provider": DBInstitutionCatalogProvider(session=session),
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
        imoveis_no_if=_read_imoveis_no_if(ws_id, session),
        **_db_resolvers(session),
    )


def _attach_llm_budget_hooks(ctx, ws_id: str, run_id: str) -> None:
    # ADR-173: hard-stop de budget + LLMCallLog em toda chamada LLM. O service
    # é stateless entre instâncias (budget/gasto lidos do DB + cache Redis) —
    # instanciar por-stage produz a mesma semântica do por-run do Celery.
    from backend.app.services.llm_budget_service import LLMBudgetService

    ctx.llm_call_hooks = LLMBudgetService(ws_id, pipeline_run_id=run_id)


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
    materialize_tarefas: bool = False,
    session_factory: Optional[Callable[[], Session]] = None,
) -> HydratedContext:
    """Cria o ``WorkspaceContext`` hidratado. ``config_dir`` explícito vence; ausente → ``<root>/config``."""
    session = (session_factory or _default_session_factory)()
    ctx = _build_ctx(ws_id, tenant_root, run_id, config_dir, session=session)
    ctx.incremental, ctx.incremental_doc_paths = incremental, list(incremental_doc_paths or [])
    _attach_llm_budget_hooks(ctx, ws_id, run_id)
    _attach_llm_response_cache(ctx)
    _attach_llm_metrics_emitter(ctx)
    ctx.ensure_dirs()
    if materialize_tarefas:
        materialize_tarefas_md(ws_id, ctx)
    return HydratedContext(ctx=ctx, config_store_session=session)
