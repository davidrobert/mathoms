"""Finalização do parecer pós-LLM (ADR-202/204/207)."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

from pipeline.llm.schemas.parecer_planejador import (
    Metadata,
    ParecerPlanejadorOutput,
    PontoForte,
    Sugestao,
)

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


def finalize_output(
    *,
    output: ParecerPlanejadorOutput,
    workspace_id: str,
    tier: str,
    model_id: str,
    persona_hash: str,
    manifest_version: str,
) -> ParecerPlanejadorOutput:
    """Sobrescreve metadata + recalcula suggestion_dedup_keys determinísticos."""
    now_iso = datetime.now(timezone.utc).isoformat()
    metadata = output.metadata.model_copy(
        update={
            "persona_hash": persona_hash,
            "manifest_version": manifest_version,
            "model_id": model_id,
            "tier_at_generation": tier,
            "generated_at": now_iso,
        }
    )
    return output.model_copy(
        update={
            "metadata": metadata,
            "sugestoes_execucao": _fix_dedup_keys(output.sugestoes_execucao, workspace_id),
            "sugestoes_taticas": _fix_dedup_keys(output.sugestoes_taticas, workspace_id),
            "sugestoes_estrategicas": _fix_dedup_keys(output.sugestoes_estrategicas, workspace_id),
        }
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
