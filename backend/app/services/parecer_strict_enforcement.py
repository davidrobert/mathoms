"""Enforcement por-item da citação verificada no modo strict (ADR-295 · A26.l8)."""

# No strict, a citação que falha derruba o ITEM (risco/sugestão), não o parecer
# inteiro — preserva o sinal (remove, não falsifica) e fecha a aritmética do gate
# per-parecer. needs_review só quando o item ofensor é severidade alta (silenciar
# risco crítico ≡ emitir número errado). missing_path é cobertura (fail-open), não
# derruba item. Auto-correção de número foi REJEITADA (ADR-295). Read-only sobre o
# verificador: consome `violations`, nunca remuta a verificação.

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pipeline.llm.schemas.parecer_planejador import ParecerPlanejadorOutput

# Citação que resolve ERRADO — derruba item. missing_path (cobertura) fica fora.
# ADR-296: pairing_mismatch (rotulo ↔ root incoerente) substitui value_mismatch.
_HARD_LAYERS = frozenset({"whitelist_miss", "resolve_null", "pairing_mismatch"})
_HIGH_SEVERIDADE = frozenset({"Crítica", "Alta"})
_SUGESTAO_HORIZONS = frozenset(
    {"sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"}
)


@dataclass(frozen=True)
class StrictDecision:
    """Resultado do enforcement: output (talvez com itens removidos) + veredito."""

    output: ParecerPlanejadorOutput
    needs_review_reason: Optional[str]
    dropped: tuple[tuple[str, int], ...]


def _parse_hard_violations(violations: list[str]) -> list[tuple[str, int]]:
    """``"tipo:índice:camada"`` → ``(tipo, índice)`` só das camadas hard."""
    out: list[tuple[str, int]] = []
    for raw in violations:
        item_type, index, layer = raw.split(":")
        if layer in _HARD_LAYERS:
            out.append((item_type, int(index)))
    return out


def _attr_for(item_type: str) -> str:
    return "riscos" if item_type == "risco" else item_type


def _is_high_severity(output: ParecerPlanejadorOutput, item_type: str, index: int) -> bool:
    """Risco Crítica/Alta ou Sugestão P0 = alto (não silenciar sem revisão humana)."""
    if item_type == "risco":
        return output.riscos[index].severidade in _HIGH_SEVERIDADE
    if item_type in _SUGESTAO_HORIZONS:
        return getattr(output, item_type)[index].prioridade == "P0"
    return False


def _drop_items(
    output: ParecerPlanejadorOutput, targets: list[tuple[str, int]]
) -> ParecerPlanejadorOutput:
    """Remove os itens (por tipo+índice) do output — listas sem mínimo, drop é seguro."""
    by_attr: dict[str, set[int]] = {}
    for item_type, index in targets:
        by_attr.setdefault(_attr_for(item_type), set()).add(index)
    update = {
        attr: [x for j, x in enumerate(getattr(output, attr)) if j not in idxs]
        for attr, idxs in by_attr.items()
    }
    return output.model_copy(update=update)


def enforce_strict_per_item(
    output: ParecerPlanejadorOutput, violations: list[str]
) -> StrictDecision:
    """Aplica a política per-item (ADR-295) sobre as violações hard."""
    hard = _parse_hard_violations(violations)
    if not hard:
        return StrictDecision(output=output, needs_review_reason=None, dropped=())
    high = [(t, i) for (t, i) in hard if _is_high_severity(output, t, i)]
    if high:
        t, i = high[0]
        reason = f"evidencia unverified (severidade alta): {t}:{i}"
        return StrictDecision(output=output, needs_review_reason=reason, dropped=())
    return StrictDecision(
        output=_drop_items(output, hard), needs_review_reason=None, dropped=tuple(hard)
    )


__all__ = ["StrictDecision", "enforce_strict_per_item"]
