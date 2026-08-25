"""Leitura da base declarada por superfície read-time ([[ADR-412]] §D8).

Superfície que recompõe artefato antigo com código novo produz híbrido sem
rótulo — o que a [[ADR-403]] criou `definicao_versao` para impedir. Estes
leitores são o contrato mínimo: **qual** base o produtor usou, e **se** a série
é a corrente. Ausência é sempre "não sei", nunca "série corrente".
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from pipeline.domain.services.bases_financeiras import BASE_VERSAO_CORRENTE, BaseFinanceira


def denominador_declarado(patrimonio: dict, *, legado: str = "investivel_financeiro") -> Decimal:
    """Base publicada; cai no campo `legado` em artefato anterior ao PR2."""
    bases = patrimonio.get("bases")
    if isinstance(bases, dict):
        declarada = bases.get(BaseFinanceira.carteira_financeira_familia.value)
        if isinstance(declarada, dict) and declarada.get("valor_brl") is not None:
            return _decimal(declarada["valor_brl"])
    return _decimal(patrimonio.get(legado) or patrimonio.get("investivel"))


def serie_corrente(patrimonio: dict) -> bool:
    """`False` em artefato sem `base_versao` — ausência não é série corrente."""
    return patrimonio.get("base_versao") == BASE_VERSAO_CORRENTE


def cobertura_apurada(bloco: object) -> bool:
    """Todos os componentes apurados — o mesmo predicado do `_tier` do E5."""
    componentes = bloco.get("componentes") if isinstance(bloco, dict) else None
    if not isinstance(componentes, dict) or not componentes:
        return False
    return all(
        isinstance(c, dict) and c.get("cobertura") == "apurado" for c in componentes.values()
    )


def _decimal(valor: Any) -> Decimal:
    try:
        return Decimal(str(valor)) if valor is not None else Decimal(0)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(0)
