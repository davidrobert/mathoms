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

from backend.app.models.planner_review import ParecerRetentionReason
from pipeline.llm.schemas.parecer_planejador import ParecerPlanejadorOutput

# Citação que resolve ERRADO — derruba item. missing_path (cobertura) fica fora.
# ADR-296: pairing_mismatch (rotulo ↔ root incoerente) substitui value_mismatch.
# ADR-358: entrada nova aqui exige ADR própria + budget de produção declarado.
# number_in_prose foi removido (ADR-304 §Emenda 2026-08-03): é detector de
# PRESENÇA de R$ na prosa, não de divergência — a âncora do item segue verificada,
# então a premissa da ADR-295 ("silenciar ≡ emitir número errado") não transfere.
_HARD_LAYERS = frozenset({"whitelist_miss", "resolve_null", "pairing_mismatch"})
_HIGH_SEVERIDADE = frozenset({"Crítica", "Alta"})
_SUGESTAO_HORIZONS = frozenset(
    {"sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"}
)


# Estrutural por construção: sem prosa, sem valor monetário, sem texto do item —
# mesmo padrão PII-safe que `_record` já aplica às entries (ADR-366 §D3).
@dataclass(frozen=True)
class DroppedItem:
    """Item removido pelo enforcement, com a camada e a severidade que se perdiam."""

    item_type: str
    index: int
    layer: str
    severidade: Optional[str]

    def as_dict(self) -> dict:
        """Forma serializada no summary do stage (``output_summary``), não no artifact."""
        return {
            "item_type": self.item_type,
            "index": self.index,
            "layer": self.layer,
            "severidade": self.severidade,
        }


@dataclass(frozen=True)
class StrictDecision:
    """Resultado do enforcement: output (talvez com itens removidos) + veredito."""

    output: ParecerPlanejadorOutput
    needs_review_reason: Optional[str]
    # Classe fechada client-facing; acompanha `needs_review_reason` (ADR-366 §D3).
    retention_reason: Optional[ParecerRetentionReason]
    # Removidos de um parecer ENTREGUE. Alimenta `items_dropped_count`, e por isso
    # fica vazio quando o parecer inteiro é retido — lá nada foi removido.
    dropped: tuple[DroppedItem, ...]
    # Item que reteve o parecer INTEIRO. Diagnóstico; nunca vira contagem.
    retention_trigger: Optional[DroppedItem]


def _parse_hard_violations(violations: list[str]) -> list[tuple[str, int, str]]:
    """``"tipo:índice:camada"`` → ``(tipo, índice, camada)`` só das hard, deduplicado."""
    # Dedupe por (tipo, índice): item cujas DUAS âncoras falham (ex.: whitelist_miss +
    # resolve_null) cai uma vez — `items_dropped` conta itens, não violações. A camada
    # preservada é a da PRIMEIRA violação do item; é a que o dedupe manteve.
    out: list[tuple[str, int, str]] = []
    seen: set[tuple[str, int]] = set()
    for raw in violations:
        item_type, index, layer = raw.split(":")
        key = (item_type, int(index))
        if layer in _HARD_LAYERS and key not in seen:
            seen.add(key)
            out.append((item_type, int(index), layer))
    return out


def _attr_for(item_type: str) -> str:
    return "riscos" if item_type == "risco" else item_type


def _severity_label(output: ParecerPlanejadorOutput, item_type: str, index: int) -> Optional[str]:
    """Rótulo de escalada do item: severidade do risco, prioridade da sugestão."""
    if item_type == "risco":
        return output.riscos[index].severidade
    if item_type in _SUGESTAO_HORIZONS:
        return getattr(output, item_type)[index].prioridade
    return None


def _is_high_severity(output: ParecerPlanejadorOutput, item_type: str, index: int) -> bool:
    """Risco Crítica/Alta ou Sugestão P0 = alto (não silenciar sem revisão humana)."""
    label = _severity_label(output, item_type, index)
    if item_type == "risco":
        return label in _HIGH_SEVERIDADE
    return label == "P0" if item_type in _SUGESTAO_HORIZONS else False


def _drop_items(
    output: ParecerPlanejadorOutput, targets: list[tuple[str, int, str]]
) -> ParecerPlanejadorOutput:
    """Remove os itens (por tipo+índice) do output — listas sem mínimo, drop é seguro."""
    by_attr: dict[str, set[int]] = {}
    for item_type, index, _layer in targets:
        by_attr.setdefault(_attr_for(item_type), set()).add(index)
    update = {
        attr: [x for j, x in enumerate(getattr(output, attr)) if j not in idxs]
        for attr, idxs in by_attr.items()
    }
    return output.model_copy(update=update)


def _as_dropped(
    output: ParecerPlanejadorOutput, hard: list[tuple[str, int, str]]
) -> tuple[DroppedItem, ...]:
    """Congela severidade ANTES do drop — pós-`model_copy` os índices deslocam."""
    return tuple(
        DroppedItem(item_type=t, index=i, layer=layer, severidade=_severity_label(output, t, i))
        for (t, i, layer) in hard
    )


def no_enforcement(output: ParecerPlanejadorOutput) -> StrictDecision:
    """Decisão neutra — sem violação hard, ou modo não-strict."""
    return StrictDecision(
        output=output,
        needs_review_reason=None,
        retention_reason=None,
        dropped=(),
        retention_trigger=None,
    )


def _withhold_all(output: ParecerPlanejadorOutput, trigger: tuple[str, int, str]) -> StrictDecision:
    """Severidade alta: o parecer INTEIRO é retido — `dropped` fica vazio de propósito."""
    item_type, index, _layer = trigger
    return StrictDecision(
        output=output,
        needs_review_reason=f"evidencia unverified (severidade alta): {item_type}:{index}",
        retention_reason=ParecerRetentionReason.citacao_nao_confirmada,
        dropped=(),
        retention_trigger=_as_dropped(output, [trigger])[0],
    )


def _drop_offenders(
    output: ParecerPlanejadorOutput, hard: list[tuple[str, int, str]]
) -> StrictDecision:
    """Severidade baixa: itens saem, parecer é entregue com a lacuna declarada."""
    return StrictDecision(
        output=_drop_items(output, hard),
        needs_review_reason=None,
        retention_reason=ParecerRetentionReason.citacao_nao_confirmada,
        dropped=_as_dropped(output, hard),
        retention_trigger=None,
    )


def enforce_strict_per_item(
    output: ParecerPlanejadorOutput, violations: list[str]
) -> StrictDecision:
    """Aplica a política per-item (ADR-295) sobre as violações hard."""
    hard = _parse_hard_violations(violations)
    if not hard:
        return no_enforcement(output)
    high = [(t, i, layer) for (t, i, layer) in hard if _is_high_severity(output, t, i)]
    return _withhold_all(output, high[0]) if high else _drop_offenders(output, hard)


__all__ = [
    "DroppedItem",
    "StrictDecision",
    "enforce_strict_per_item",
    "no_enforcement",
]
