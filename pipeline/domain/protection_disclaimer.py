"""Ressalva fiduciária canônica de cobertura recomendada (ADR-192 · A40.l60)."""

from __future__ import annotations

DISCLAIMER_MARK = "não constitui recomendação fiduciária"


def fiduciary_disclaimer(methodology: str, effective_date: str | None = None) -> str:
    date = effective_date or "data corrente"
    return (
        f"Estimativa baseada em metodologia consagrada de planejamento patrimonial "
        f"brasileiro ({methodology}); {DISCLAIMER_MARK}. Consultar corretor "
        f"habilitado pela Susep e planejador CFP®. Dados fiscais válidos para {date}."
    )


__all__ = ["DISCLAIMER_MARK", "fiduciary_disclaimer"]
