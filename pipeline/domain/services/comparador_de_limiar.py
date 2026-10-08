"""Predicado único de conformidade contra limiar — alvo do catálogo e gatilho de risco.

Existia só dentro do ``risk_trigger_registry``; o veredito do parecer ([[A40.l92]]) seria a
terceira cópia, e cópia de comparador diverge exatamente na fronteira — foi assim que
``<`` (catálogo) e ``<=`` (gatilho) discordaram em 50,00 sobre a mesma grandeza.
"""

from __future__ import annotations

import operator
from typing import Callable

_PREDICADOS: dict[str, Callable[[float, float], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def conforme_ao_limiar(observado: float, operador: str, limiar: float) -> bool:
    """``observado operador limiar`` — operador fora do vocabulário levanta, nunca julga."""
    predicado = _PREDICADOS.get(operador)
    if predicado is None:
        raise ValueError(f"operador {operador!r} fora do vocabulário {tuple(_PREDICADOS)}")
    return predicado(observado, limiar)


__all__ = ["conforme_ao_limiar"]
