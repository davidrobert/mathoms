"""Stage wrapper — review_finances_holistic (parecer planejador, ADR-199)."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext

logger = logging.getLogger("mathoms.pipeline.parecer_planejador")

STAGE_NAME = "review_finances_holistic"
ARTIFACT_STAGE = "E6-parecer"
ARTIFACT_KEY = "parecer_planejador"
_DEFAULT_MODEL = "anthropic/claude-sonnet-4-20250514"


def _is_enabled() -> bool:
    """Feature flag MATHOMS_ENABLE_PARECER_PLANEJADOR (default TRUE; ADR-199).

    Promovido a default-on em 2026-05-14 (Ato 6). Set
    MATHOMS_ENABLE_PARECER_PLANEJADOR=false como kill-switch operacional.
    """
    return os.environ.get("MATHOMS_ENABLE_PARECER_PLANEJADOR", "true").lower() in (
        "1",
        "true",
        "yes",
    )


def _resolve_tier(ctx: "WorkspaceContext") -> str:
    """Resolve tier do workspace (premium | free). Fallback premium em CLI/testes."""
    overrides = getattr(ctx, "config_overrides", None) or {}
    workspace_meta = overrides.get("workspace_meta") if isinstance(overrides, dict) else None
    if isinstance(workspace_meta, dict):
        tier = workspace_meta.get("tier")
        if tier in ("free", "premium"):
            return tier
    return "premium"


def _read_e5_artifact(store) -> dict | None:
    """Lê E5 com fallback de nome legado → descritivo."""
    e5 = store.read("E5", "analise_financeira")
    if e5 is None:
        e5 = store.read("analyze_finances", "analise_financeira")
    return e5


def _build_artifact_json(result) -> dict:
    """Serializa output + _meta para persistência via ArtifactStore."""
    # WHY exclude_none: ``campos_faltantes_pediria_se_iterasse`` é ausente vs array
    # vazio (semântica diferente para telemetria M4 — ADR-206).
    payload = result.output.model_dump(mode="json", exclude_none=True)
    payload["_meta"] = {
        "tool_trace": result.tool_trace,
        "cost_usd": result.cost_usd,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "latency_ms": result.latency_ms,
        "tool_iterations": result.tool_iterations,
        "cache_hit": result.cache_hit,
        "status": result.status,
        "schema_version": result.schema_version,
    }
    if result.error_detail:
        payload["_meta"]["error_detail"] = result.error_detail
    return payload


def _needs_review_return(result, workspace_id: str, store) -> dict:
    """Persiste artifact mínimo + retorna status needs_review."""
    logger.warning(
        "parecer_planejador_needs_review",
        extra={"workspace_id": workspace_id, "reason": result.error_detail},
    )
    store.write(ARTIFACT_STAGE, ARTIFACT_KEY, _build_artifact_json(result))
    return {
        "success": False,
        "status": "needs_review",
        "reason": result.error_detail,
        "tokens": {"in": result.tokens_in, "out": result.tokens_out},
        "cost_usd": result.cost_usd,
        "latency_ms": result.latency_ms,
    }


def _summary_counts(output) -> dict:
    """Contagens estruturais — usadas no log + retorno."""
    return {
        "riscos_count": len(output.riscos),
        "sugestoes_execucao_count": len(output.sugestoes_execucao),
        "sugestoes_taticas_count": len(output.sugestoes_taticas),
        "sugestoes_estrategicas_count": len(output.sugestoes_estrategicas),
        "metricas_count": len(output.metricas),
    }


def _success_return(result, workspace_id: str) -> dict:
    """Empacota status final para o orchestrator + caller backend."""
    summary = _summary_counts(result.output)
    logger.info(
        "parecer_planejador_generated",
        extra={
            "workspace_id": workspace_id,
            "persona_hash": result.persona_hash[:8],
            "manifest_version": result.manifest_version,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "cost_usd": result.cost_usd,
            "latency_ms": result.latency_ms,
            "cache_hit": result.cache_hit,
            "riscos_count": summary["riscos_count"],
        },
    )
    return {
        "success": True,
        "status": result.status,
        "cache_hit": result.cache_hit,
        "tokens": {"in": result.tokens_in, "out": result.tokens_out},
        "cost_usd": result.cost_usd,
        "latency_ms": result.latency_ms,
        "tool_iterations": result.tool_iterations,
        "model_id": result.model_id,
        "persona_hash": result.persona_hash,
        "manifest_version": result.manifest_version,
        "schema_version": result.schema_version,
        "tier_at_generation": result.tier_at_generation,
        "parecer_summary": summary,
    }


def _load_orchestrator():
    """Lazy import — None em runtime CLI sem backend instalado."""
    try:
        from backend.app.services.parecer_orchestrator import (
            ParecerOrchestratorConfig,
            generate_parecer,
        )

        return ParecerOrchestratorConfig, generate_parecer
    except ImportError as exc:
        return None, exc


def run(ctx: "WorkspaceContext") -> dict:
    """Executa o stage e devolve dict de status (convenção do orchestrator)."""
    if not _is_enabled():
        return {"skipped": True, "reason": "feature flag MATHOMS_ENABLE_PARECER_PLANEJADOR=false"}
    store = ctx.get_artifact_store()
    e5_data = _read_e5_artifact(store)
    if e5_data is None:
        return {"skipped": True, "reason": "E5 analysis artifact not found"}
    config_cls, gen_fn = _load_orchestrator()
    if config_cls is None:
        return {"skipped": True, "reason": f"backend orchestrator not available: {gen_fn}"}
    tier = _resolve_tier(ctx)
    if tier == "free":
        # ADR-208 §D1 — geração só roda pra premium.
        return {"skipped": True, "reason": "tier=free; parecer holístico é premium-only"}

    workspace_id = getattr(ctx, "workspace_id", None) or "cli-workspace"
    config = config_cls(
        workspace_id=workspace_id,
        tier=tier,
        model_id=os.environ.get("MATHOMS_PARECER_PLANEJADOR_MODEL", _DEFAULT_MODEL),
    )
    result = gen_fn(e5_data=e5_data, config=config)
    if result.status == "needs_review":
        return _needs_review_return(result, workspace_id, store)
    store.write(ARTIFACT_STAGE, ARTIFACT_KEY, _build_artifact_json(result))
    return _success_return(result, workspace_id)
