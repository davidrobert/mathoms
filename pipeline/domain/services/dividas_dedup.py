"""Dedup de dívidas cross-IRPF (cross-year + cross-declarante) como policy sobre
``run_entity_dedup`` (ADR-301, ADR-276). Espelha ``investimentos_dedup`` (ADR-271)
com três divergências de domínio: a chave prefere ``numero_contrato`` (discriminador
forte) e degrada para ``(tipo, credor_norm, descricao_norm)``; cross-year une
``saldo_31_12`` (foto recente = ano máximo, dívida não é marca-a-mercado mas a série
sobrevive); e emite ``saldo_nao_monotonico`` SÓ para dívida amortizável de prestação
fixa cujo saldo nominal cresceu — revolvente/indexada/sem-tipo não dispara (saldo
crescente é legítimo; warning ingênuo geraria FP em massa).
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

# Só dívida amortizável de prestação fixa tem saldo monotonicamente decrescente
# esperado. Revolvente (cheque especial/cartão/rotativo), bullet/balloon e indexada
# podem crescer legitimamente — não disparam warning (ADR-301 §3, financial-planner).
_AMORTIZAVEL_FIXO = frozenset(
    {
        "financiamento_imobiliario",
        "financiamento_veiculo",
        "emprestimo_pessoal",
        "consignado",
    }
)


@dataclass(frozen=True)
class DividaDedupWarning:
    divida_id: str | None
    type: str  # "saldo_divergente_ano" | "saldo_nao_monotonico" | "possivel_duplicata"
    values: tuple[float, ...]
    diff_pct: float


@dataclass(frozen=True)
class DividaDedupResult:
    dividas: list[dict]
    warnings: tuple[DividaDedupWarning, ...]
    count_before: int
    count_after: int
    dropped_keys: tuple[str, ...]


def dedup_dividas_consolidadas(dividas: list[dict] | None) -> DividaDedupResult:
    """Deduplica ``dividas`` consolidadas por identidade cross-IRPF (ADR-301)."""
    outcome = run_entity_dedup(dividas, _DividaPolicy())
    log_dedup("consolidate.dividas_dedup", outcome, dropped_key="dropped_keys")
    return _to_result(outcome)


def _to_result(outcome: DedupOutcome) -> DividaDedupResult:
    return DividaDedupResult(
        dividas=outcome.items,
        warnings=tuple(_to_divida_warning(w) for w in outcome.warnings),
        count_before=outcome.count_before,
        count_after=outcome.count_after,
        dropped_keys=outcome.dropped_ids,
    )


def _to_divida_warning(w: DedupWarning) -> DividaDedupWarning:
    return DividaDedupWarning(
        divida_id=w.entity_id, type=w.type, values=w.values, diff_pct=w.diff_pct
    )


class _DividaPolicy:
    """Chave ``numero_contrato`` ⊳ ``(tipo, credor_norm, desc_norm)``; sem reagrupamento."""

    def identity_key(self, entry: dict) -> tuple | None:
        return _identity_key(entry)

    def remap_groups(self, grouped: GroupedEntries) -> GroupedEntries:
        return grouped

    def emit_group(
        self, group: list[dict]
    ) -> tuple[list[dict], tuple[DedupWarning, ...], tuple[str, ...]]:
        div_id = _divida_id(_identity_key(group[0]))
        if len(group) == 1:
            return [_stamp_id(group[0], div_id)], (), ()
        warnings: list[DedupWarning] = []
        per_owner = _merge_cross_year(group, div_id, warnings)
        if len(per_owner) == 1:
            return per_owner, tuple(warnings), _dropped(group, div_id)
        entries, dec_warnings, dropped = _emit_cross_declarante(div_id, per_owner, group)
        return entries, tuple(warnings) + dec_warnings, dropped


def _identity_key(entry: dict) -> tuple | None:
    """Chave da DÍVIDA, agnóstica a ano e proprietário; ``None`` = unidentified."""
    desc = normalize_descricao(entry.get("descricao"))
    if not desc:
        return None
    # numero_contrato é o discriminador mais forte (descrição livre varia entre
    # anos); renegociação muda o contrato → vira dívida nova, não funde (ADR-301 §2).
    contrato = (entry.get("numero_contrato") or "").strip()
    if contrato:
        return ("contrato", contrato)
    tipo = (entry.get("tipo") or "").strip().lower()
    credor = normalize_descricao(entry.get("credor"))
    return ("desc", tipo, credor, desc)


def _divida_id(key: tuple | None) -> str:
    raw = "|".join(str(p) for p in (key or ()))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _dropped(group: list[dict], div_id: str) -> tuple[str, ...]:
    return tuple(div_id for _ in range(max(0, len(group) - 1)))


def _merge_cross_year(
    group: list[dict],
    div_id: str,
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
    return [_merge_owner_entries(by_owner[o], div_id, warnings) for o in order]


def _merge_owner_entries(
    entries: list[dict],
    div_id: str,
    warnings: list[DedupWarning],
) -> dict:
    if len(entries) == 1:
        return _stamp_id(entries[0], div_id)
    merged = dict(entries[0])
    saldos: dict[str, float] = {}
    for entry in entries:
        _union_saldos(saldos, entry, div_id, warnings)
    merged["saldo_31_12"] = saldos
    _check_monotonicidade(merged, saldos, div_id, warnings)
    return _stamp_id(merged, div_id)


def _union_saldos(
    acc: dict[str, float],
    entry: dict,
    div_id: str,
    warnings: list[DedupWarning],
) -> None:
    for ano, valor in (entry.get("saldo_31_12") or {}).items():
        v = _safe_float(valor)
        if ano in acc and cents_int(acc[ano]) != cents_int(v):
            warnings.append(_year_conflict_warning(div_id, acc[ano], v))
            acc[ano] = max(acc[ano], v)
        else:
            acc[ano] = v


def _check_monotonicidade(
    entry: dict,
    saldos: dict[str, float],
    div_id: str,
    warnings: list[DedupWarning],
) -> None:
    """Warning SÓ para dívida amortizável de prestação fixa cujo saldo cresceu
    ano-a-ano. Tipo ausente / revolvente / indexada → silêncio (ADR-301 §3)."""
    tipo = (entry.get("tipo") or "").strip().lower()
    if tipo not in _AMORTIZAVEL_FIXO or entry.get("indexador"):
        return
    anos = sorted(saldos.keys())
    for prev, cur in zip(anos, anos[1:]):
        if cents_int(saldos[cur]) > cents_int(saldos[prev]):
            warnings.append(_monotonicidade_warning(div_id, saldos[prev], saldos[cur]))
            return


def _emit_cross_declarante(
    div_id: str,
    per_owner: list[dict],
    group: list[dict],
) -> tuple[list[dict], tuple[DedupWarning, ...], tuple[str, ...]]:
    """Mesma dívida, proprietários distintos: funde "casal" só se saldo idêntico
    ao centavo (financiamento conjunto); divergente → preserva ambas + warning."""
    if _is_joint_debt(per_owner):
        return [_merge_joint(per_owner, div_id)], (), _dropped(group, div_id)
    entries: list[dict] = []
    for entry in per_owner:
        stamped = dict(entry)
        stamped["_dedup_warning"] = {"type": "possivel_duplicata"}
        entries.append(stamped)
    return entries, (_duplicata_warning(div_id, per_owner),), ()


def _duplicata_warning(div_id: str, per_owner: list[dict]) -> DedupWarning:
    return DedupWarning(
        entity_id=div_id,
        type="possivel_duplicata",
        values=tuple(_latest_value(e) for e in per_owner),
        diff_pct=0.0,
    )


def _is_joint_debt(per_owner: list[dict]) -> bool:
    """True quando todos os declarantes trazem o MESMO saldo 31/12 (ao centavo)."""
    cents = {cents_int(_latest_value(e)) for e in per_owner}
    return len(cents) == 1 and 0 not in cents


def _merge_joint(per_owner: list[dict], div_id: str) -> dict:
    winner = dict(per_owner[0])
    owners = sorted({_owner(e) for e in per_owner if _owner(e)})
    winner["proprietarios"] = owners
    winner["proprietario"] = _CASAL_LABEL
    return _stamp_id(winner, div_id)


def _owner(entry: dict) -> str:
    return (entry.get("proprietario") or "").strip().lower()


def _latest_value(entry: dict) -> float:
    saldos = entry.get("saldo_31_12") or {}
    if isinstance(saldos, dict) and saldos:
        latest = max(saldos.keys())
        return _safe_float(saldos.get(latest))
    return _safe_float(entry.get("saldo_devedor", 0))


def _year_conflict_warning(div_id: str, a: float, b: float) -> DedupWarning:
    diff_pct = abs(a - b) / max(abs(a), abs(b)) * 100 if max(abs(a), abs(b)) else 0.0
    return DedupWarning(
        entity_id=div_id,
        type="saldo_divergente_ano",
        values=(a, b),
        diff_pct=round(diff_pct, 1),
    )


def _monotonicidade_warning(div_id: str, anterior: float, atual: float) -> DedupWarning:
    diff_pct = (atual - anterior) / anterior * 100 if anterior else 0.0
    return DedupWarning(
        entity_id=div_id,
        type="saldo_nao_monotonico",
        values=(anterior, atual),
        diff_pct=round(diff_pct, 1),
    )


def _stamp_id(entry: dict, div_id: str) -> dict:
    if entry.get("divida_id") == div_id:
        return entry
    out = dict(entry)
    out["divida_id"] = div_id
    return out


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


__all__ = [
    "DividaDedupResult",
    "DividaDedupWarning",
    "dedup_dividas_consolidadas",
]
