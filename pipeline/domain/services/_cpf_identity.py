"""Normalização de CPF para identidade canônica de membro (ADR-266)."""

from __future__ import annotations


def normalize_cpf(value: str | None) -> str:
    """Strip não-dígitos, exige 11 chars (CPF), rejeita CNPJ (14 dígitos)."""
    if not value:
        return ""
    digits = "".join(c for c in str(value) if c.isdigit())
    # ADR-266 D3: CPF = exatamente 11 dígitos. CNPJ (14) e mascarado parcial
    # (<11) são rejeitados — caller cai no fallback name resolver.
    return digits if len(digits) == 11 else ""
