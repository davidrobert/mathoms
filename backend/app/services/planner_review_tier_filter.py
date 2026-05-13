"""Tier filter para ``PlannerReview`` (ADR-208 §gating freemium) — converte artifact dict (schema interno com ancora) em DTO user-facing (sigilo §13 atravessa aqui)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Optional

from backend.app.schemas.dto.planner_review.response import (
    GatedCounts,
    ImpactoEstimadoDTO,
    MetricaDTO,
    NotaMetodologicaDTO,
    ParecerContentMeta,
    ParecerPlanejadorContent,
    PontoForteDTO,
    RiscoDTO,
    SugestaoDTO,
    Tier,
)


@dataclass(frozen=True)
class TierLimits:
    """Cap por bucket (None = sem cap)."""

    pontos_fortes: Optional[int]
    riscos: Optional[int]
    sugestoes: Optional[int]  # aplicado a cada horizonte separadamente
    metricas: Optional[int]
    notas: Optional[int]


# ADR-208 §D2 — free teaser conservador, premium destrava plano completo.
FREE_TIER_LIMITS = TierLimits(
    pontos_fortes=3,
    riscos=1,
    sugestoes=0,
    metricas=0,
    notas=0,
)

PREMIUM_TIER_LIMITS = TierLimits(
    pontos_fortes=None,
    riscos=None,
    sugestoes=None,
    metricas=None,
    notas=None,
)


def _limits_for(tier: Tier) -> TierLimits:
    return FREE_TIER_LIMITS if tier == "free" else PREMIUM_TIER_LIMITS


def _truncate(items: list, cap: Optional[int] = None) -> tuple[list, int]:
    """Aplica cap (None = noop); retorna (visíveis, gated_count)."""
    if cap is None or len(items) <= cap:
        return items, 0
    return items[:cap], len(items) - cap


def _by_severity(riscos: list[dict]) -> list[dict]:
    """Ordena por severidade descendente (Crítica > Alta > Média > Baixa)."""
    order = {"Crítica": 0, "Alta": 1, "Média": 2, "Baixa": 3}
    return sorted(riscos, key=lambda r: order.get(r.get("severidade", "Baixa"), 4))


def _ponto_dto(raw: Mapping[str, Any]) -> PontoForteDTO:
    """Pula ancora_metodologica (sigilo §13 · ADR-207)."""
    return PontoForteDTO(
        titulo=raw["titulo"],
        descricao=raw["descricao"],
        tema_canonico=raw.get("tema_canonico"),
        section_id=raw.get("section_id"),
    )


def _risco_dto(raw: Mapping[str, Any]) -> RiscoDTO:
    return RiscoDTO(
        severidade=raw["severidade"],
        titulo=raw["titulo"],
        descricao=raw["descricao"],
        tema_canonico=raw["tema_canonico"],
        evidencia=raw.get("evidencia"),
        evidencia_path=raw.get("evidencia_path"),
        section_id=raw["section_id"],
        confianca=raw.get("confianca"),
    )


def _impacto_dto(raw: Optional[Mapping[str, Any]] = None) -> Optional[ImpactoEstimadoDTO]:
    if not raw:
        return None
    # LLM emite float; DTO wire é Decimal (ADR-090). str(float) preserva
    # precisão sem reintroduzir float arithmetic.
    return ImpactoEstimadoDTO(
        valor_estimado_brl=Decimal(str(raw["valor_estimado_brl"])),
        unidade=raw["unidade"],
        caveat=raw["caveat"],
    )


def _sugestao_dto(raw: Mapping[str, Any]) -> SugestaoDTO:
    return SugestaoDTO(
        prioridade=raw["prioridade"],
        acao=raw["acao"],
        impacto_qualitativo=raw["impacto_qualitativo"],
        tema_canonico=raw["tema_canonico"],
        confianca=raw["confianca"],
        section_id=raw["section_id"],
        suggestion_dedup_key=raw["suggestion_dedup_key"],
        impacto_estimado=_impacto_dto(raw.get("impacto_estimado")),
        evidencia_path=raw.get("evidencia_path"),
    )


def _metrica_dto(raw: Mapping[str, Any]) -> MetricaDTO:
    return MetricaDTO(
        nome=raw["nome"],
        valor_atual=raw["valor_atual"],
        target=raw["target"],
        frequencia_revisao=raw["frequencia_revisao"],
        section_id=raw["section_id"],
        tema_canonico=raw.get("tema_canonico"),
    )


def _nota_dto(raw: Mapping[str, Any]) -> NotaMetodologicaDTO:
    """Mapeia ancoras (interno) → temas_canonicos (user-facing). Fallback [] quando ausente."""
    return NotaMetodologicaDTO(
        titulo=raw["titulo"],
        conteudo=raw["conteudo"],
        temas_canonicos=raw.get("temas_canonicos") or [],
    )


def _build_meta(
    *, tier: Tier, source_meta: Mapping[str, Any], gated: GatedCounts
) -> ParecerContentMeta:
    """Constrói meta DTO a partir do `metadata` do output canônico."""
    return ParecerContentMeta(
        tier_at_generation=tier,
        persona_hash=source_meta["persona_hash"],
        manifest_version=source_meta["manifest_version"],
        schema_version=source_meta.get("schema_version", "1.0"),
        model_id=source_meta["model_id"],
        generated_at=source_meta["generated_at"],
        gated_counts=gated,
    )


@dataclass(frozen=True)
class _TruncationResult:
    """Hold buckets truncados + gated counts agregados."""

    pontos: list
    riscos: list
    exec_: list
    tat: list
    estrat: list
    metricas: list
    notas: list
    gated: GatedCounts


def _truncate_horizontes(
    artifact: Mapping[str, Any], cap: Optional[int] = None
) -> tuple[list, list, list, int, int, int]:
    """Aplica cap em cada um dos 3 horizontes; retorna listas + gated counts."""
    exec_, g_exec = _truncate(list(artifact.get("sugestoes_execucao", [])), cap)
    tat, g_tat = _truncate(list(artifact.get("sugestoes_taticas", [])), cap)
    estrat, g_estrat = _truncate(list(artifact.get("sugestoes_estrategicas", [])), cap)
    return exec_, tat, estrat, g_exec, g_tat, g_estrat


def _truncate_all_buckets(artifact: Mapping[str, Any], limits: TierLimits) -> _TruncationResult:
    """Aplica caps em todos os buckets do artifact."""
    pontos, g_pontos = _truncate(list(artifact.get("pontos_fortes", [])), limits.pontos_fortes)
    riscos, g_riscos = _truncate(_by_severity(list(artifact.get("riscos", []))), limits.riscos)
    exec_, tat, estrat, g_exec, g_tat, g_estrat = _truncate_horizontes(artifact, limits.sugestoes)
    metricas, g_metricas = _truncate(list(artifact.get("metricas", [])), limits.metricas)
    notas, g_notas = _truncate(list(artifact.get("notas_metodologicas", [])), limits.notas)
    gated = GatedCounts(
        pontos_fortes=g_pontos,
        riscos=g_riscos,
        sugestoes_execucao=g_exec,
        sugestoes_taticas=g_tat,
        sugestoes_estrategicas=g_estrat,
        metricas=g_metricas,
        notas_metodologicas=g_notas,
    )
    return _TruncationResult(
        pontos=pontos,
        riscos=riscos,
        exec_=exec_,
        tat=tat,
        estrat=estrat,
        metricas=metricas,
        notas=notas,
        gated=gated,
    )


def _build_content(
    artifact: Mapping[str, Any], *, tier: Tier, truncated: _TruncationResult
) -> ParecerPlanejadorContent:
    """Mapeia buckets truncados para DTO user-facing."""
    return ParecerPlanejadorContent(
        version=artifact.get("version", "1.0"),
        diagnostico_geral=artifact["diagnostico_geral"],
        pontos_fortes=[_ponto_dto(p) for p in truncated.pontos],
        riscos=[_risco_dto(r) for r in truncated.riscos],
        sugestoes_execucao=[_sugestao_dto(s) for s in truncated.exec_],
        sugestoes_taticas=[_sugestao_dto(s) for s in truncated.tat],
        sugestoes_estrategicas=[_sugestao_dto(s) for s in truncated.estrat],
        metricas=[_metrica_dto(m) for m in truncated.metricas],
        notas_metodologicas=[_nota_dto(n) for n in truncated.notas],
        meta=_build_meta(tier=tier, source_meta=artifact["metadata"], gated=truncated.gated),
    )


def _sum_gated(gc: GatedCounts) -> int:
    return (
        gc.pontos_fortes
        + gc.riscos
        + gc.sugestoes_execucao
        + gc.sugestoes_taticas
        + gc.sugestoes_estrategicas
        + gc.metricas
        + gc.notas_metodologicas
    )


def apply_tier_filter(
    *, artifact: Mapping[str, Any], tier: Tier
) -> tuple[ParecerPlanejadorContent, int]:
    """Aplica gating freemium + converte schema interno → DTO user-facing. Retorna ``(content, items_gated_count)``."""
    truncated = _truncate_all_buckets(artifact, _limits_for(tier))
    content = _build_content(artifact, tier=tier, truncated=truncated)
    return content, _sum_gated(truncated.gated)


__all__ = [
    "FREE_TIER_LIMITS",
    "PREMIUM_TIER_LIMITS",
    "TierLimits",
    "apply_tier_filter",
]
