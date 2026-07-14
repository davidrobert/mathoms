"""Re-bucketização de ``por_fonte`` em naturezas de renda, derivada e fora de ``por_fonte`` (ADR-330)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

# Códigos de RECEITA-PJ do classifier (``transaction_classifier_pj``): pró-labore +
# lucros distribuídos. ``das_simples``/``iss``/``folha_pj`` são DESPESA — não são renda.
RECEITA_PJ_CODES = ("pro_labore", "lucros_distribuidos")


def _cents(value: float) -> int:
    # Espelha o `_cents` de tests/test_e5_conservation_invariants.py (ROUND_HALF_UP sobre
    # round(v,2)) para casar exatamente o `por_fonte` emitido pelo enricher.
    return int((Decimal(str(round(value, 2))) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def compute_receita_por_natureza(por_fonte: dict, receita_total: float) -> dict[str, float]:
    """``receita_pj`` = pró-labore + lucros; ``receita_outras`` = resíduo; soma == ``receita_total`` (cents)."""
    pj = sum(_cents(por_fonte.get(code, 0.0)) for code in RECEITA_PJ_CODES)
    clt = _cents(por_fonte.get("receita_clt", 0.0))
    aluguel = _cents(por_fonte.get("receita_aluguel", 0.0))
    outras = _cents(receita_total) - pj - clt - aluguel
    return {
        "receita_pj": pj / 100.0,
        "receita_clt": clt / 100.0,
        "receita_aluguel": aluguel / 100.0,
        "receita_outras": outras / 100.0,
    }
