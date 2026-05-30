"""Dedup de imóveis co-declarados em IRPFs cônjuge↔titular como policy sobre
``run_entity_dedup`` (ADR-246, ADR-265, ADR-276); diferente de investimentos,
imóvel não é marca-a-mercado (maior-valor-vence) e ``remap_groups`` reagrupa por
endereço canônico (cross-código ADR-246 + fuzzy via/número ADR-265) antes de emitir.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pipeline.domain.services.canonical_fuzzy_match import (
    extract_complemento,
    matches_fuzzy,
)
from pipeline.domain.services.entity_dedup import (
    DedupOutcome,
    GroupedEntries,
    log_dedup,
    run_entity_dedup,
)
from pipeline.domain.services.entity_dedup import (
    DedupWarning as _CoreWarning,
)

_DIVERGENCE_THRESHOLD_PCT = 10.0
_CASAL_LABEL = "casal"
# Subcódigos específicos do Grupo 01 (Bens Imóveis) RFB (espelha dev/dedup_property_identity.py).
# "01" e "" são genéricos (grupo-pai sem subcódigo, ex.: comprovantes de bem ADR-239).
_SPECIFIC_CODIGOS_RFB = frozenset({"11", "12", "13", "14", "15", "17", "19"})


@dataclass(frozen=True)
class DedupWarning:
    property_id: str | None
    type: str  # "valor_divergente"
    values: tuple[float, ...]
    diff_pct: float


@dataclass(frozen=True)
class DedupResult:
    imoveis: list[dict]
    warnings: tuple[DedupWarning, ...]
    count_before: int
    count_after: int
    dropped_property_ids: tuple[str, ...]


def dedup_imoveis_consolidados(
    imoveis: list[dict] | None,
    *,
    titular_key: str | None = None,
) -> DedupResult:
    """Deduplica imoveis_consolidados por identidade cross-IRPF (ADR-246, ADR-265)."""
    outcome = run_entity_dedup(imoveis, _ImovelPolicy(titular_key))
    log_dedup("consolidate.imoveis_dedup", outcome, dropped_key="dropped_property_ids")
    return _to_result(outcome)


def _to_result(outcome: DedupOutcome) -> DedupResult:
    return DedupResult(
        imoveis=outcome.items,
        warnings=tuple(_to_imovel_warning(w) for w in outcome.warnings),
        count_before=outcome.count_before,
        count_after=outcome.count_after,
        dropped_property_ids=outcome.dropped_ids,
    )


def _to_imovel_warning(w: _CoreWarning) -> DedupWarning:
    return DedupWarning(property_id=w.entity_id, type=w.type, values=w.values, diff_pct=w.diff_pct)


class _ImovelPolicy:
    """Chave `pid`/`canon`; reagrupa por cross-código + fuzzy; maior-valor-vence."""

    def __init__(self, titular_key: str | None) -> None:
        self._titular_key = titular_key

    def identity_key(self, entry: dict) -> tuple | None:
        return _identity_key(entry)

    def remap_groups(self, grouped: GroupedEntries) -> GroupedEntries:
        # Reusa os passes verbatim sobre a forma dict+order (ADR-246/265).
        as_dict = {key: group for key, group in grouped}
        order = [key for key, _ in grouped]
        _merge_cross_codigo(as_dict, order)
        _merge_fuzzy_via_num(as_dict, order)
        return [(key, as_dict[key]) for key in order]

    def emit_group(
        self, group: list[dict]
    ) -> tuple[list[dict], tuple[_CoreWarning, ...], tuple[str, ...]]:
        if len(group) == 1:
            return [group[0]], (), ()
        merged, warning = _merge_group(group, titular_key=self._titular_key)
        warnings = (warning,) if warning is not None else ()
        dropped = _dropped_pids(group, merged.get("property_id"))
        return [merged], warnings, dropped


def _dropped_pids(group: list[dict], winner_pid: object) -> tuple[str, ...]:
    out: list[str] = []
    for entry in group:
        pid = entry.get("property_id")
        if pid and pid != winner_pid:
            out.append(str(pid))
    return tuple(out)


def _merge_cross_codigo(grouped: dict[tuple, list[dict]], order: list[tuple]) -> None:
    """Cross-codigo: funde grupos canonical-comum quando 1 lado é genérico (01/'')."""
    by_canonical = _index_by_canonical(grouped, order)
    for keys in by_canonical.values():
        if _should_merge_cross_codigo(grouped, keys):
            _consolidate_keys(grouped, order, keys)


def _index_by_canonical(
    grouped: dict[tuple, list[dict]], order: list[tuple]
) -> dict[str, list[tuple]]:
    by_canonical: dict[str, list[tuple]] = {}
    for key in order:
        canon = _group_canonical(grouped[key])
        if canon:
            by_canonical.setdefault(canon, []).append(key)
    return by_canonical


def _should_merge_cross_codigo(grouped: dict[tuple, list[dict]], keys: list[tuple]) -> bool:
    if len(keys) <= 1:
        return False
    if not _has_generic_codigo_in_groups(grouped, keys):
        return False
    return not _has_conflicting_specific_codigos_in_groups(grouped, keys)


def _group_canonical(entries: list[dict]) -> str:
    for e in entries:
        canon = e.get("endereco_canonical")
        if canon:
            return str(canon)
    return ""


def _group_codigos(entries: list[dict]) -> set[str]:
    return {(e.get("codigo_rfb") or "").strip() for e in entries}


def _has_generic_codigo_in_groups(grouped: dict[tuple, list[dict]], keys: list[tuple]) -> bool:
    all_codigos: set[str] = set()
    for key in keys:
        all_codigos |= _group_codigos(grouped[key])
    return any(cod not in _SPECIFIC_CODIGOS_RFB for cod in all_codigos)


def _has_conflicting_specific_codigos_in_groups(
    grouped: dict[tuple, list[dict]], keys: list[tuple]
) -> bool:
    """True se 2+ codigos específicos divergentes (ex.: 11 e 12) — conflito humano, não merge."""
    specifics: set[str] = set()
    for key in keys:
        specifics |= _group_codigos(grouped[key]) & _SPECIFIC_CODIGOS_RFB
    return len(specifics) >= 2


def _consolidate_keys(
    grouped: dict[tuple, list[dict]], order: list[tuple], keys: list[tuple]
) -> None:
    """Funde todas as keys: grupo com cod específico ganha posição; outros vêm depois."""
    primary = _pick_primary_key(grouped, keys)
    for key in keys:
        if key == primary:
            continue
        grouped[primary].extend(grouped[key])
        order.remove(key)
        del grouped[key]


def _pick_primary_key(grouped: dict[tuple, list[dict]], keys: list[tuple]) -> tuple:
    """Específico (11/12/...) vence sobre genérico (01/'')."""
    for key in keys:
        if _group_codigos(grouped[key]) & _SPECIFIC_CODIGOS_RFB:
            return key
    return keys[0]


def _merge_fuzzy_via_num(grouped: dict[tuple, list[dict]], order: list[tuple]) -> None:
    """Funde grupos com mesma via e Δ numérico ≤ K (ADR-265, pós-cross-codigo)."""
    keys = list(order)
    merged_into: set[tuple] = set()
    for i, key_a in enumerate(keys):
        if key_a in merged_into or key_a not in grouped:
            continue
        _fuzzy_merge_into(grouped, order, key_a, keys[i + 1 :], merged_into)


def _fuzzy_merge_into(
    grouped: dict[tuple, list[dict]],
    order: list[tuple],
    key_a: tuple,
    candidates: list[tuple],
    merged_into: set[tuple],
) -> None:
    for key_b in candidates:
        if key_b in merged_into or key_b not in grouped:
            continue
        if _should_merge_fuzzy(grouped, key_a, key_b):
            _consolidate_keys(grouped, order, [key_a, key_b])
            merged_into.add(key_b)


def _should_merge_fuzzy(grouped: dict[tuple, list[dict]], key_a: tuple, key_b: tuple) -> bool:
    """True quando os grupos têm via+número próximos e nenhum conflito."""
    canon_a = _group_canonical(grouped[key_a])
    canon_b = _group_canonical(grouped[key_b])
    if not canon_a or not canon_b or canon_a == canon_b:
        return False
    complemento_a = _group_complemento(grouped[key_a])
    complemento_b = _group_complemento(grouped[key_b])
    if not matches_fuzzy(
        canon_a, canon_b, complemento_a=complemento_a, complemento_b=complemento_b
    ):
        return False
    return not _has_conflicting_specific_codigos_in_groups(grouped, [key_a, key_b])


def _group_complemento(entries: list[dict]) -> str | None:
    """Primeiro complemento extraído da descrição das entries do grupo."""
    for e in entries:
        complemento = extract_complemento(e.get("descricao"))
        if complemento:
            return complemento
    return None


def _identity_key(entry: dict) -> tuple | None:
    pid = entry.get("property_id")
    if pid:
        return ("pid", str(pid))
    codigo = (entry.get("codigo_rfb") or "").strip()
    canonical = entry.get("endereco_canonical")
    if codigo and canonical:
        return ("canon", codigo, str(canonical))
    return None


def _merge_group(group: list[dict], *, titular_key: str | None) -> tuple[dict, _CoreWarning | None]:
    """Merge N entries do mesmo imóvel — maior valor vence; co-titularidade aditiva."""
    ordered = sorted(group, key=lambda e: _winner_sort_key(e, titular_key), reverse=True)
    winner = dict(ordered[0])
    _apply_proprietarios(winner, ordered)
    warning = _maybe_warning(ordered, winner.get("property_id"))
    if warning is not None:
        winner["_dedup_warning"] = {
            "type": warning.type,
            "values": list(warning.values),
            "diff_pct": warning.diff_pct,
        }
    return winner, warning


def _apply_proprietarios(winner: dict, group: list[dict]) -> None:
    proprietarios = _union_proprietarios(group)
    if len(proprietarios) > 1:
        winner["proprietarios"] = proprietarios
        winner["proprietario"] = _CASAL_LABEL
    elif proprietarios:
        winner["proprietarios"] = proprietarios


def _winner_sort_key(entry: dict, titular_key: str | None) -> tuple:
    valor = float(_entry_value(entry))
    ano = _latest_year(entry)
    is_titular = _is_titular(entry, titular_key)
    return (valor, ano, is_titular)


def _is_titular(entry: dict, titular_key: str | None) -> int:
    if not titular_key:
        return 0
    proprio = (entry.get("proprietario") or "").strip().lower()
    return 1 if proprio == titular_key.lower() else 0


def _entry_value(entry: dict) -> Decimal:
    vals = entry.get("valores_31_12") or {}
    if isinstance(vals, dict) and vals:
        latest = _latest_year(entry)
        if latest:
            return _safe_decimal(vals.get(latest))
    return _safe_decimal(entry.get("valor", 0))


def _latest_year(entry: dict) -> str:
    vals = entry.get("valores_31_12") or {}
    if not isinstance(vals, dict) or not vals:
        return ""
    try:
        return max(str(k) for k in vals.keys())
    except ValueError:
        return ""


def _safe_decimal(v: Any) -> Decimal:
    if v is None or isinstance(v, bool):
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _union_proprietarios(group: list[dict]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for entry in group:
        _accumulate_unique(_entry_proprietarios(entry), out, seen)
    return out


def _accumulate_unique(values: list[str], out: list[str], seen: set[str]) -> None:
    for p in values:
        key = p.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(p.strip())


def _entry_proprietarios(entry: dict) -> list[str]:
    props = entry.get("proprietarios")
    if isinstance(props, list) and props:
        return [str(p) for p in props if p]
    prop = entry.get("proprietario")
    if isinstance(prop, str) and prop.strip():
        return [prop]
    return []


def _maybe_warning(group: list[dict], property_id: str | None) -> _CoreWarning | None:
    values = [float(_entry_value(e)) for e in group]
    if not values:
        return None
    max_v = max(values)
    if max_v <= 0:
        return None
    diff_pct = (max_v - min(values)) / max_v * 100.0
    if diff_pct <= _DIVERGENCE_THRESHOLD_PCT:
        return None
    return _CoreWarning(
        entity_id=str(property_id) if property_id else None,
        type="valor_divergente",
        values=tuple(values),
        diff_pct=round(diff_pct, 2),
    )


__all__ = [
    "DedupResult",
    "DedupWarning",
    "dedup_imoveis_consolidados",
]
