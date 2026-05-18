"""Snapshot serializer das premissas econômicas para E5 (ADR-219 wave 2)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from pipeline.domain.types.economic_assumption import ResolvedAssumption
from pipeline.ports import EconomicAssumptionsResolver

# Snapshot payload — top-level tem string/list misturados (status, snapshot_at, classes).
# Documentado no schema E5 §premissas_economicas; aqui mantemos dict[str, Any] no boundary
# pra compor naturalmente com o output legacy.
SnapshotPayload = dict[str, Any]
ClassRow = dict[str, str | None]


def build_premissas_economicas_snapshot(
    resolver: EconomicAssumptionsResolver | None = None,
    *,
    as_of: date,
    workspace_id: Optional[str] = None,
) -> Optional[SnapshotPayload]:
    """Constrói o snapshot a embutir no payload E5 (ADR-219 D5)."""
    if resolver is None:
        return None
    rows = resolver.get_vigentes_em(as_of, workspace_id=workspace_id)
    if not rows:
        return None
    status = "parcial" if any(r.status == "indisponivel" for r in rows) else "completo"
    return {
        "status": status,
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "classes": [_serialize_row(r) for r in rows],
    }


def _serialize_row(r: ResolvedAssumption) -> ClassRow:
    return {
        "classe_auvp": r.classe_auvp,
        "status": r.status,
        "retorno_real_esperado_pct_anual": (
            str(r.retorno_real_esperado_pct_anual)
            if r.retorno_real_esperado_pct_anual is not None
            else None
        ),
        "sigma_anual_pct": (str(r.sigma_anual_pct) if r.sigma_anual_pct is not None else None),
        "fonte": r.fonte,
        "fonte_origem": r.fonte_origem,
        "effective_from": (r.effective_from.isoformat() if r.effective_from else None),
        "justificativa": r.justificativa,
        "razao_indisponivel": r.razao_indisponivel,
    }
