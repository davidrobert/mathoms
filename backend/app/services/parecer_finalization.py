"""Finalização do parecer pós-LLM (ADR-202/204/207)."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

from backend.app.services.parecer_citation_catalog import ancora_format_hint
from pipeline.llm.schemas.parecer_planejador import (
    Ancora,
    Metadata,
    ParecerPlanejadorOutput,
    PontoForte,
    Risco,
    Sugestao,
)
from pipeline.llm.tools.planner_drill_down import PlannerDrillDown
from pipeline.llm.value_formatter import format_value

# Termos sigilo §13 — camada 2 de defesa (persona é 1, UI é 3 — ADR-207).
_FORBIDDEN_TERMS = (
    "Perini",
    "Bruno Perini",
    "Cerbasi",
    "Gustavo Cerbasi",
    "Raul Sena",
    "AUVP",
    "Viver de Renda",
    "Equilíbrio Financeiro",
    "Casais Inteligentes",
    "A Única Verdade Possível",
    "Diagrama do Cerrado",
    "Anderson Investimentos",
)

_FORBIDDEN_LOWER = tuple(t.lower() for t in _FORBIDDEN_TERMS)


def compute_suggestion_dedup_key(*, workspace_id: str, ancora: str, acao: str) -> str:
    """sha256 hex (64) determinístico — mesma (ws, ancora, ação normalizada) → mesma key."""
    acao_norm = re.sub(r"\s+", " ", acao.strip().lower())[:100]
    composite = f"{workspace_id}|{ancora}|{acao_norm}"
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()


def compute_suggestion_thesis_key(
    *,
    workspace_id: str,
    tema_canonico: Optional[str],
    section_id: Optional[str],
    ancora: Optional[str],
) -> Optional[str]:
    """Identidade semântica da tese (ADR-290 B1) — estável entre runs, independe de redação/valor. Campo-fonte ausente → None (linha fica fora do supersede)."""
    if not (tema_canonico and section_id and ancora):
        return None
    composite = f"{workspace_id}|{tema_canonico}|{section_id}|{ancora}"
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()


def severity_from_prioridade(prio: str) -> str:
    """Mapping ADR-153: P0→danger, P1→warning, P2→info."""
    return {"P0": "danger", "P1": "warning", "P2": "info"}.get(prio, "info")


def _scan_field(field_name: str, text: str | None, violations: list[str]) -> None:
    """Append a violations cada termo proibido encontrado."""
    if not text:
        return
    lowered = text.lower()
    for term, term_lower in zip(_FORBIDDEN_TERMS, _FORBIDDEN_LOWER):
        if term_lower in lowered:
            violations.append(f"{field_name}: termo {term!r}")


def _scan_riscos(output: ParecerPlanejadorOutput, v: list[str]) -> None:
    for i, r in enumerate(output.riscos):
        _scan_field(f"riscos[{i}].descricao", r.descricao, v)
        _scan_field(f"riscos[{i}].titulo", r.titulo, v)
        _scan_field(f"riscos[{i}].evidencia", r.evidencia, v)


def _scan_sugestoes(output: ParecerPlanejadorOutput, v: list[str]) -> None:
    for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
        for i, s in enumerate(getattr(output, horizon)):
            _scan_field(f"{horizon}[{i}].acao", s.acao, v)
            _scan_field(f"{horizon}[{i}].impacto_qualitativo", s.impacto_qualitativo, v)


def validate_anti_sigilo(output: ParecerPlanejadorOutput) -> list[str]:
    """Retorna lista de violações sigilo §13 sobre o output completo."""
    violations: list[str] = []
    _scan_field("diagnostico_geral", output.diagnostico_geral, violations)
    for i, p in enumerate(output.pontos_fortes):
        _scan_field(f"pontos_fortes[{i}].descricao", p.descricao, violations)
    _scan_riscos(output, violations)
    _scan_sugestoes(output, violations)
    for i, n in enumerate(output.notas_metodologicas):
        _scan_field(f"notas_metodologicas[{i}].conteudo", n.conteudo, violations)
        _scan_field(f"notas_metodologicas[{i}].titulo", n.titulo, violations)
    return violations


def _fix_dedup_keys(sugs: list[Sugestao], workspace_id: str) -> list[Sugestao]:
    """Recalcula suggestion_dedup_key determinístico para lista de sugestões."""
    out: list[Sugestao] = []
    for s in sugs:
        key = compute_suggestion_dedup_key(
            workspace_id=workspace_id, ancora=s.ancora_metodologica, acao=s.acao
        )
        out.append(s.model_copy(update={"suggestion_dedup_key": key}))
    return out


# ADR-290 F3 — cap de geração. Prompt (regra 13) é best-effort; invariante
# de produto é garantido aqui, deterministicamente, antes do persist.
GENERATION_CAP_PER_HORIZON = 3


def _truncation_rank(s: Sugestao) -> tuple[int, int]:
    """(P0 primeiro, |impacto| desc) — P0 sem valor nunca é cortado por R$ alto
    de prioridade menor (proteção fiduciária; count(P0) ≤ 2 cabe no cap)."""
    cents = (
        abs(int(round(s.impacto_estimado.valor_estimado_brl * 100)))
        if s.impacto_estimado is not None
        else -1
    )
    return (1 if s.prioridade == "P0" else 0, cents)


def _truncate_horizon(sugs: list[Sugestao]) -> list[Sugestao]:
    """Mantém as GENERATION_CAP_PER_HORIZON de maior rank, na ordem original."""
    if len(sugs) <= GENERATION_CAP_PER_HORIZON:
        return list(sugs)
    ranked = sorted(sugs, key=_truncation_rank, reverse=True)
    keep = {id(s) for s in ranked[:GENERATION_CAP_PER_HORIZON]}
    return [s for s in sugs if id(s) in keep]


def _finalize_horizon(sugs: list[Sugestao], workspace_id: str) -> list[Sugestao]:
    return _fix_dedup_keys(_truncate_horizon(sugs), workspace_id)


def _capped_horizons(
    output: ParecerPlanejadorOutput, workspace_id: str
) -> dict[str, list[Sugestao]]:
    return {
        h: _finalize_horizon(getattr(output, h), workspace_id)
        for h in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas")
    }


def _stamped_metadata(
    output: ParecerPlanejadorOutput,
    *,
    persona_hash: str,
    manifest_version: str,
    model_id: str,
    tier: str,
) -> Metadata:
    return output.metadata.model_copy(
        update={
            "persona_hash": persona_hash,
            "manifest_version": manifest_version,
            "model_id": model_id,
            "tier_at_generation": tier,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def _resolve_ancora(ancora: Ancora, drill: PlannerDrillDown) -> Ancora:
    """Resolve path→valor_renderizado com dispatch por tipo de folha (ADR-296 · A28.l10):
    o hint vem de ``ancora_format_hint`` (catálogo de citação — a folha conhece seu
    campo), não de heurística sobre o valor. Prob → "31%", idade → "53 anos",
    moeda → "R$ …" (ADR-090)."""
    if ancora.path is None:
        return ancora
    result = drill.get_e5_jsonpath(ancora.path)
    if not result.found:
        return ancora
    rendered = format_value(result.value, ancora_format_hint(ancora.path))
    return ancora.model_copy(update={"valor_renderizado": rendered})


def _stamp_item(item: Risco | Sugestao, drill: PlannerDrillDown) -> Risco | Sugestao:
    if not item.ancoras:
        return item
    return item.model_copy(update={"ancoras": [_resolve_ancora(a, drill) for a in item.ancoras]})


def stamp_ancora_values(
    output: ParecerPlanejadorOutput, drill: PlannerDrillDown
) -> ParecerPlanejadorOutput:
    """ADR-296: grava o snapshot valor_renderizado de cada âncora (LLM não autora o número)."""
    update: dict = {"riscos": [_stamp_item(r, drill) for r in output.riscos]}
    for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
        update[horizon] = [_stamp_item(s, drill) for s in getattr(output, horizon)]
    return output.model_copy(update=update)


def finalize_output(
    *,
    output: ParecerPlanejadorOutput,
    workspace_id: str,
    tier: str,
    model_id: str,
    persona_hash: str,
    manifest_version: str,
) -> ParecerPlanejadorOutput:
    """Sobrescreve metadata + cap de geração (ADR-290 F3) + dedup_keys determinísticos."""
    metadata = _stamped_metadata(
        output,
        persona_hash=persona_hash,
        manifest_version=manifest_version,
        model_id=model_id,
        tier=tier,
    )
    return output.model_copy(
        update={"metadata": metadata, **_capped_horizons(output, workspace_id)}
    )


_PLACEHOLDER_PONTO = PontoForte(
    titulo="placeholder",
    descricao="needs_review placeholder",
    ancora_metodologica="convergencia",
)


def empty_needs_review_output(
    *, persona_hash: str, manifest_version: str, model_id: str, tier: str
) -> ParecerPlanejadorOutput:
    """Placeholder needs_review — não é salvo nem publicado, só serializado pro caller."""
    metadata = Metadata(
        persona_hash=persona_hash,
        manifest_version=manifest_version,
        model_id=model_id,
        tier_at_generation=tier,  # type: ignore[arg-type]
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return ParecerPlanejadorOutput(
        version="1.0",
        metadata=metadata,
        diagnostico_geral=(
            "Geração interrompida — parecer marcado para revisão. "
            "Inspecione _meta.error_detail para diagnóstico."
        ),
        pontos_fortes=[_PLACEHOLDER_PONTO] * 3,
        riscos=[],
        sugestoes_execucao=[],
        sugestoes_taticas=[],
        sugestoes_estrategicas=[],
        metricas=[],
        notas_metodologicas=[],
    )
