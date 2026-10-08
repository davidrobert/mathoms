"""Predicado único de conformidade contra limiar — alvo do catálogo e gatilho de risco.

Existia só dentro do ``risk_trigger_registry``; o veredito do parecer ([[A40.l92]]) seria a
terceira cópia, e cópia de comparador diverge exatamente na fronteira — foi assim que
``<`` (catálogo) e ``<=`` (gatilho) discordaram em 50,00 sobre a mesma grandeza.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal, InvalidOperation
from typing import Any, Callable, Optional, Union

Numero = Union[float, Decimal]

_PREDICADOS: dict[str, Callable[[Any, Any], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}
_PISOS = frozenset({">", ">="})


def conforme_ao_limiar(observado: Numero, operador: str, limiar: Numero) -> bool:
    """``observado operador limiar`` — operador fora do vocabulário levanta, nunca julga."""
    predicado = _PREDICADOS.get(operador)
    if predicado is None:
        raise ValueError(f"operador {operador!r} fora do vocabulário {tuple(_PREDICADOS)}")
    return predicado(observado, limiar)


@dataclass(frozen=True)
class VereditoDoComparador:
    """O que o comparador licencia: conformidade, e progresso só no piso (A40.l92)."""

    operador: str
    conforme: bool
    # Teto nunca tem progresso; o default é a forma do teto, não um "desconhecido".
    progresso_pct: Optional[int] = None


def veredito_do_comparador(
    observado: Any,
    operador: Optional[str],  # órfã publica `None` — sem operador não há veredito
    limiar: Any,
) -> Optional[VereditoDoComparador]:
    """Julga o BRUTO, na escala do produtor; ``None`` se um lado não é número finito."""
    obs, lim = numero_finito(observado), numero_finito(limiar)
    if obs is None or lim is None or operador not in _PREDICADOS:
        return None
    conforme = conforme_ao_limiar(obs, operador, lim)
    return VereditoDoComparador(operador, conforme, _progresso_pct(obs, operador, lim, conforme))


# Teto não tem progresso: abaixo dele "menor" não é "melhor" em nenhuma das três
# metodologias (co-design financial-planner). No piso, 100 SÓ se conforme — pela
# estrutura, não pela aritmética: em float, floor(0,29 × 100) dá 28.
def _progresso_pct(obs: Decimal, operador: str, lim: Decimal, conforme: bool) -> Optional[int]:
    if operador not in _PISOS or lim <= 0:
        return None
    if conforme:
        return 100
    fracao = (obs / lim * 100).to_integral_value(rounding=ROUND_FLOOR)
    return int(min(Decimal(99), max(Decimal(0), fracao)))


# `str(float)` é o repr mais curto que volta ao mesmo float, logo preserva a ordem. NaN e
# ±inf fabricariam "violado": o comparador some em vez de julgar.
def numero_finito(valor: Any) -> Optional[Decimal]:
    """Decimal do valor numérico (aceita string com vírgula); ``None`` se não for finito."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str, Decimal)):
        return None
    try:
        numero = Decimal(str(valor).strip().replace(",", "."))
    except InvalidOperation:
        return None
    return numero if numero.is_finite() else None


__all__ = ["VereditoDoComparador", "conforme_ao_limiar", "numero_finito", "veredito_do_comparador"]
