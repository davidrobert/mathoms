"""Dedup de investimentos cross-IRPF — cross-year + cross-declarante (ADR-271)."""

# Espelha imoveis_dedup (ADR-246) com duas divergências de domínio, detalhadas
# na ADR-271: (1) cross-year une `valores_31_12` e o valor corrente é o ano mais
# recente — investimento é marcado a mercado, não piso histórico como imóvel;
# (2) cross-declarante funde APENAS quando o valor 31/12 é idêntico ao centavo
# (conta conjunta = mesmo saldo declarado 2×). Calibração conservadora:
# falso-positivo (some patrimônio real) é pior que falso-negativo (infla PL).

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from pipeline.domain.services._tx_identity import cents_int, normalize_descricao

logger = logging.getLogger("mathoms.pipeline.consolidate")

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
    items = [e for e in (investimentos or []) if isinstance(e, dict)]
    result = _dedup_grouped(items)
    _log_if_deduped(result)
    return result


def _dedup_grouped(items: list[dict]) -> InvestDedupResult:
    grouped, order, unidentified = _group_by_identity(items)
    out: list[dict] = []
    warnings: list[InvestDedupWarning] = []
    dropped: list[str] = []
    for key in order:
        _emit_group(key, grouped[key], out, warnings, dropped)
    out.extend(unidentified)
    return InvestDedupResult(
        investimentos=out,
        warnings=tuple(warnings),
        count_before=len(items),
        count_after=len(out),
        dropped_keys=tuple(dropped),
    )


def _group_by_identity(
    items: list[dict],
) -> tuple[dict[tuple, list[dict]], list[tuple], list[dict]]:
    grouped: dict[tuple, list[dict]] = {}
    order: list[tuple] = []
    unidentified: list[dict] = []
    for entry in items:
        key = _identity_key(entry)
        if key is None:
            unidentified.append(entry)
            continue
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(entry)
    return grouped, order, unidentified


def _identity_key(entry: dict) -> tuple | None:
    """Chave do ATIVO, agnóstica a ano e proprietário. ``None`` = unidentified."""
    desc = normalize_descricao(entry.get("descricao"))
    if not desc:
        return None
    tipo = (entry.get("tipo") or "").strip().lower()
    inst = normalize_descricao(entry.get("instituicao"))
    return (tipo, inst, desc)


def _investment_id(key: tuple) -> str:
    raw = "|".join(str(p) for p in key)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _emit_group(
    key: tuple,
    group: list[dict],
    out: list[dict],
    warnings: list[InvestDedupWarning],
    dropped: list[str],
) -> None:
    inv_id = _investment_id(key)
    if len(group) == 1:
        out.append(_stamp_id(group[0], inv_id))
        return
    per_owner = _merge_cross_year(group, inv_id, warnings)
    if len(per_owner) == 1:
        out.append(per_owner[0])
        _record_dropped(group, inv_id, kept=1, dropped=dropped)
        return
    _emit_cross_declarante(inv_id, per_owner, out, warnings, dropped, group)


def _merge_cross_year(
    group: list[dict],
    inv_id: str,
    warnings: list[InvestDedupWarning],
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
    warnings: list[InvestDedupWarning],
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
    warnings: list[InvestDedupWarning],
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
    out: list[dict],
    warnings: list[InvestDedupWarning],
    dropped: list[str],
    group: list[dict],
) -> None:
    """Mesmo ativo, proprietários distintos: funde só se valor idêntico ao centavo."""
    if _is_joint_account(per_owner):
        out.append(_merge_joint(per_owner, inv_id))
        _record_dropped(group, inv_id, kept=1, dropped=dropped)
        return
    for entry in per_owner:
        stamped = dict(entry)
        stamped["_dedup_warning"] = {"type": "possivel_duplicata"}
        out.append(stamped)
    warnings.append(_duplicata_warning(inv_id, per_owner))


def _duplicata_warning(inv_id: str, per_owner: list[dict]) -> InvestDedupWarning:
    return InvestDedupWarning(
        investment_id=inv_id,
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


def _year_conflict_warning(inv_id: str, a: float, b: float) -> InvestDedupWarning:
    diff_pct = abs(a - b) / max(abs(a), abs(b)) * 100 if max(abs(a), abs(b)) else 0.0
    return InvestDedupWarning(
        investment_id=inv_id,
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


def _record_dropped(group: list[dict], inv_id: str, *, kept: int, dropped: list[str]) -> None:
    for _ in range(max(0, len(group) - kept)):
        dropped.append(inv_id)


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _log_if_deduped(result: InvestDedupResult) -> None:
    if result.count_after >= result.count_before:
        return
    logger.info(
        "consolidate.investimentos_dedup",
        extra={
            "stage": "E1.5c",
            "count_before": result.count_before,
            "count_after": result.count_after,
            "dropped_keys": list(result.dropped_keys),
            "warnings_count": len(result.warnings),
        },
    )
