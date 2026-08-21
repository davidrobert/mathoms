"""Locator PII-free de uma posição de investimento ([[ADR-405]]).

O locator é o `investment_id` que `investimentos_dedup` já carimba no baseline —
sha256 de `tipo|instituicao|descricao`. Reusá-lo, em vez de nomear a instituição
na razão, evita recriar em superfície durável o acoplamento a rótulo volátil que
a [[ADR-400]] acabou de cortar da entrada do classificador.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Any, Mapping


def safe_float(val: Any) -> float:
    """Coerção tolerante: `None`/lixo → 0,0; decimal com vírgula é aceito."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.replace(",", "."))
        except ValueError:
            return 0.0
    return 0.0


def valor_da_posicao(inv: Mapping[str, Any]) -> Decimal:
    """Valor da posição — `valor` quando presente, senão o campo do baseline."""
    return Decimal(str(safe_float(inv.get("valor", inv.get("valor_31_12_ano_base", 0)))))


def locator_da_posicao(inv: Mapping[str, Any]) -> str:
    """`investment_id` do baseline; fallback derivado só da descrição."""
    inv_id = str(inv.get("investment_id") or "").strip()
    if inv_id:
        return inv_id
    desc = str(inv.get("descricao") or inv.get("description") or "").strip().lower()
    return "h:" + hashlib.sha256(desc.encode("utf-8")).hexdigest()[:16]


__all__ = ["locator_da_posicao", "safe_float", "valor_da_posicao"]
