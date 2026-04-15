"""CPF mod-11 generator determinístico — F6.5D.7.

# Por que determinístico

Tests precisam de CPFs válidos (passam validação mod-11) mas SEM usar CPFs
reais. Gerador aqui recebe um seed inteiro e produz o mesmo CPF sempre →
reproducibilidade + zero risco LGPD.

# Regra mod-11

Cálculo dos dois dígitos verificadores:
- DV1: soma(digito_i * (10 - i), i=0..8) mod 11. Se resultado < 2, DV1 = 0,
  senão DV1 = 11 - resultado.
- DV2: soma(digito_i * (11 - i), i=0..9) mod 11. Mesma regra para < 2.

# Uso em tests

    from tests.utils.cpf import generate_valid_cpf, cpf_formatted

    cpf_plain = generate_valid_cpf(seed=42)      # determinístico  # noqa: PII-ok
    cpf_fmt = cpf_formatted(seed=42)             # "XXX.XXX.XXX-YY" formatado  # noqa: PII-ok

# Lint anti-PII

Ver `tests/utils/lint_no_real_pii.py` — escaneia repositório por CPFs
que parecem reais (padrão `\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}` fora de lista
branca de generated-for-test). Rodar em CI.
"""

from __future__ import annotations

import hashlib


def _dv(digits: list[int], factor_start: int) -> int:
    total = sum(d * (factor_start - i) for i, d in enumerate(digits))
    rem = total % 11
    return 0 if rem < 2 else 11 - rem


def generate_valid_cpf(seed: int) -> str:
    """Retorna um CPF numérico válido (11 dígitos) derivado deterministicamente
    do `seed`. Formato: string sem pontuação, ex: "12345678909"."""
    # Deriva 9 dígitos do seed via hash (reproduzível)
    h = hashlib.sha256(str(seed).encode("ascii")).hexdigest()
    # Pega 9 chars hex e reduz para 0-9
    base = [int(h[i], 16) % 10 for i in range(9)]
    # Evita CPFs com todos os dígitos iguais (regra de negócio comum)
    if len(set(base)) == 1:
        base[0] = (base[0] + 1) % 10
    dv1 = _dv(base, 10)
    dv2 = _dv(base + [dv1], 11)
    return "".join(str(d) for d in base + [dv1, dv2])


def cpf_formatted(seed: int) -> str:
    """Retorna o CPF no formato brasileiro: 'XXX.XXX.XXX-YY'."""
    c = generate_valid_cpf(seed)
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"


def is_valid_cpf(cpf: str) -> bool:
    """Valida um CPF (com ou sem formatação) via mod-11."""
    nums = [int(c) for c in cpf if c.isdigit()]
    if len(nums) != 11:
        return False
    if len(set(nums)) == 1:
        return False  # todos iguais
    base = nums[:9]
    dv1 = _dv(base, 10)
    if nums[9] != dv1:
        return False
    dv2 = _dv(base + [dv1], 11)
    return nums[10] == dv2
