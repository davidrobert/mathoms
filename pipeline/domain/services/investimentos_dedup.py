"""Dedup de investimentos cross-IRPF (cross-year + cross-declarante) como policy
sobre ``run_entity_dedup`` (ADR-271, ADR-276); duas divergências vs. imóveis:
cross-year une ``valores_31_12`` marcando a mercado (ano mais recente, não piso),
e cross-declarante funde APENAS com valor 31/12 idêntico ao centavo (conta
conjunta) — calibração conservadora, falso-positivo (some PL) pior que falso-negativo.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pipeline.domain.services._tx_identity import cents_int, normalize_descricao
from pipeline.domain.services.entity_dedup import (
    DedupOutcome,
    DedupWarning,
    GroupedEntries,
    log_dedup,
    run_entity_dedup,
)

_CASAL_LABEL = "casal"


@dataclass(frozen=True)
class InvestDedupWarning:
    investment_id: str | None
    type: str  # "valor_divergente_ano" | "possivel_duplicata"
    values: tuple[float, ...]
    diff_pct: float


@dataclass(frozen=True)
class InvestDedupResult:
    investimentos: list[dict]
    warnings: tuple[InvestDedupWarning, ...]
    count_before: int
    count_after: int
    dropped_keys: tuple[str, ...]


def dedup_investimentos_consolidados(
    investimentos: list[dict] | None,
) -> InvestDedupResult:
    """Deduplica ``investimentos_consolidados`` por identidade cross-IRPF (ADR-271)."""
    outcome = run_entity_dedup(investimentos, _InvestmentPolicy())
    log_dedup("consolidate.investimentos_dedup", outcome, dropped_key="dropped_keys")
    return _to_result(outcome)


def _to_result(outcome: DedupOutcome) -> InvestDedupResult:
    return InvestDedupResult(
        investimentos=outcome.items,
        warnings=tuple(_to_invest_warning(w) for w in outcome.warnings),
        count_before=outcome.count_before,
        count_after=outcome.count_after,
        dropped_keys=outcome.dropped_ids,
    )


def _to_invest_warning(w: DedupWarning) -> InvestDedupWarning:
    return InvestDedupWarning(
        investment_id=w.entity_id, type=w.type, values=w.values, diff_pct=w.diff_pct
    )


class _InvestmentPolicy:
    """Chave exata `(tipo, instituicao_norm, descricao_norm)`; sem reagrupamento."""

    def identity_key(self, entry: dict) -> tuple | None:
        return _identity_key(entry)

    def remap_groups(self, grouped: GroupedEntries) -> GroupedEntries:
        return grouped

    def emit_group(
        self, group: list[dict]
    ) -> tuple[list[dict], tuple[DedupWarning, ...], tuple[str, ...]]:
        inv_id = _investment_id(_identity_key(group[0]))
        if len(group) == 1:
            return [_stamp_id(group[0], inv_id)], (), ()
        warnings: list[DedupWarning] = []
        per_owner = _merge_cross_year(group, inv_id, warnings)
        if len(per_owner) == 1:
            return per_owner, tuple(warnings), _dropped(group, inv_id)
        entries, dec_warnings, dropped = _emit_cross_declarante(inv_id, per_owner, group)
        return entries, tuple(warnings) + dec_warnings, dropped


def _identity_key(entry: dict) -> tuple | None:
    """Chave do ATIVO, agnóstica a ano e proprietário. ``None`` = unidentified."""
    desc = normalize_descricao(entry.get("descricao"))
    if not desc:
        return None
    tipo = (entry.get("tipo") or "").strip().lower()
    inst = normalize_descricao(entry.get("instituicao"))
    return (tipo, inst, desc)


def _investment_id(key: tuple | None) -> str:
    raw = "|".join(str(p) for p in (key or ()))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _dropped(group: list[dict], inv_id: str) -> tuple[str, ...]:
    return tuple(inv_id for _ in range(max(0, len(group) - 1)))


def _merge_cross_year(
    group: list[dict],
    inv_id: str,
    warnings: list[DedupWarning],
) -> list[dict]:
    """Funde entries do mesmo proprietário (anos sucessivos) em uma por owner."""
    by_owner: dict[str, list[dict]] = {}
    order: list[str] = []
    for entry in group:
        owner = _owner(entry)
        if owner not in by_owner:
            by_owner[owner] = []
            order.append(owner)
        by_owner[owner].append(entry)
    return [_merge_owner_entries(by_owner[o], inv_id, warnings) for o in order]


def _merge_owner_entries(
    entries: list[dict],
    inv_id: str,
    warnings: list[DedupWarning],
) -> dict:
    if len(entries) == 1:
        return _stamp_id(entries[0], inv_id)
    merged = dict(entries[0])
    valores: dict[str, float] = {}
    for entry in entries:
        _union_valores(valores, entry, inv_id, warnings)
    merged["valores_31_12"] = valores
    return _stamp_id(merged, inv_id)


def _union_valores(
    acc: dict[str, float],
    entry: dict,
    inv_id: str,
    warnings: list[DedupWarning],
) -> None:
    for ano, valor in (entry.get("valores_31_12") or {}).items():
        v = _safe_float(valor)
        if ano in acc and cents_int(acc[ano]) != cents_int(v):
            warnings.append(_year_conflict_warning(inv_id, acc[ano], v))
            acc[ano] = max(acc[ano], v)
        else:
            acc[ano] = v


def _emit_cross_declarante(
    inv_id: str,
    per_owner: list[dict],
    group: list[dict],
) -> tuple[list[dict], tuple[DedupWarning, ...], tuple[str, ...]]:
    """Mesmo ativo, proprietários distintos: funde só se valor idêntico ao centavo."""
    if _is_joint_account(per_owner):
        return [_merge_joint(per_owner, inv_id)], (), _dropped(group, inv_id)
    entries: list[dict] = []
    for entry in per_owner:
        stamped = dict(entry)
        stamped["_dedup_warning"] = {"type": "possivel_duplicata"}
        entries.append(stamped)
    return entries, (_duplicata_warning(inv_id, per_owner),), ()


def _duplicata_warning(inv_id: str, per_owner: list[dict]) -> DedupWarning:
    return DedupWarning(
        entity_id=inv_id,
        type="possivel_duplicata",
        values=tuple(_latest_value(e) for e in per_owner),
        diff_pct=0.0,
    )


def _is_joint_account(per_owner: list[dict]) -> bool:
    """True quando todos os declarantes trazem o MESMO valor 31/12 (ao centavo)."""
    cents = {cents_int(_latest_value(e)) for e in per_owner}
    return len(cents) == 1 and 0 not in cents


def _merge_joint(per_owner: list[dict], inv_id: str) -> dict:
    winner = dict(per_owner[0])
    owners = sorted({_owner(e) for e in per_owner if _owner(e)})
    winner["proprietarios"] = owners
    winner["proprietario"] = _CASAL_LABEL
    return _stamp_id(winner, inv_id)


def _owner(entry: dict) -> str:
    return (entry.get("proprietario") or "").strip().lower()


def _latest_value(entry: dict) -> float:
    vals = entry.get("valores_31_12") or {}
    if isinstance(vals, dict) and vals:
        latest = max(vals.keys())
        return _safe_float(vals.get(latest))
    return _safe_float(entry.get("valor", 0))


def _year_conflict_warning(inv_id: str, a: float, b: float) -> DedupWarning:
    diff_pct = abs(a - b) / max(abs(a), abs(b)) * 100 if max(abs(a), abs(b)) else 0.0
    return DedupWarning(
        entity_id=inv_id,
        type="valor_divergente_ano",
        values=(a, b),
        diff_pct=round(diff_pct, 1),
    )


def _stamp_id(entry: dict, inv_id: str) -> dict:
    if entry.get("investment_id") == inv_id:
        return entry
    out = dict(entry)
    out["investment_id"] = inv_id
    return out


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


__all__ = [
    "InvestDedupResult",
    "InvestDedupWarning",
    "dedup_investimentos_consolidados",
]
