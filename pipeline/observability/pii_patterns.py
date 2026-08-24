"""Regex de CONTEÚDO para identificadores pessoais — CTO-03 / [[ADR-332]].

``redaction.py`` é key-based (redige por nome de chave, deixa o valor intacto).
Este módulo redige por padrão do VALOR, para o sanitizer do contexto do parecer
(``parecer_context_sanitizer``) garantir que nenhum identificador chegue ao
provider LLM por nenhum egresso (distiller + tool ``get_e5_section``).

Formatos específicos (CPF/CNPJ com máscara) → baixo falso-positivo: datas
(``2024-12-31``) e valores não casam. Endereço/matrícula/nº de contrato em
``top_ativos[].nome`` já saem sanitizados na fonte ([[ADR-337]]); aqui é
defesa-em-profundidade sobre a cauda das seções que a tool devolve inteiras.
"""

from __future__ import annotations

import re

_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_CNPJ = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
_REDACTED = "[id-redigido]"

# Forma SEM máscara. Dígito verificador mod-11 é o filtro de falso-positivo:
# um número de conta/protocolo de 11 dígitos passa em 1/121 dos casos, e o
# custo de errar aqui é um token de redação a mais, não perda de dado.
# Escopo deliberado: só o gate do view-model consome (A40.l6 §Ataque A6).
# `scrub_identifiers` — que alimenta o sanitizer do parecer — fica intacto:
# alargar o input do LLM exige eval ([[ADR-337]] §Consequências).
_CPF_NU = re.compile(r"(?<!\d)(\d{11})(?!\d)")
_CNPJ_NU = re.compile(r"(?<!\d)(\d{14})(?!\d)")


def scrub_identifiers(text: str) -> str:
    """Substitui CPF e CNPJ por token de redação (idempotente)."""
    return _CNPJ.sub(_REDACTED, _CPF.sub(_REDACTED, text))


def contains_identifier(text: str) -> bool:
    """True se o texto contém CPF ou CNPJ — usado pelo gate PII-scan."""
    return bool(_CPF.search(text) or _CNPJ.search(text))


def _mod11(digits: str, factor_start: int) -> int:
    total = sum(int(d) * (factor_start - i) for i, d in enumerate(digits))
    rem = total % 11
    return 0 if rem < 2 else 11 - rem


def _cpf_digits_valid(digits: str) -> bool:
    if len(set(digits)) == 1:
        return False
    return _mod11(digits[:9], 10) == int(digits[9]) and _mod11(digits[:10], 11) == int(digits[10])


def _cnpj_digits_valid(digits: str) -> bool:
    def dv(base: str) -> int:
        weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(base) :]
        rem = sum(int(d) * w for d, w in zip(base, weights)) % 11
        return 0 if rem < 2 else 11 - rem

    return dv(digits[:12]) == int(digits[12]) and dv(digits[:13]) == int(digits[13])


def _bare_matches(text: str) -> list[re.Match[str]]:
    """Matches de CPF/CNPJ sem máscara cujo dígito verificador confere."""
    cpf = [m for m in _CPF_NU.finditer(text) if _cpf_digits_valid(m.group(1))]
    return cpf + [m for m in _CNPJ_NU.finditer(text) if _cnpj_digits_valid(m.group(1))]


def contains_bare_identifier(text: str) -> bool:
    """True se há CPF/CNPJ sem máscara com dígito verificador válido."""
    return bool(_bare_matches(text))


def scrub_bare_identifiers(text: str) -> str:
    """Redige CPF/CNPJ sem máscara (idempotente); complementa ``scrub_identifiers``."""
    out = text
    for match in sorted(_bare_matches(text), key=lambda m: m.start(), reverse=True):
        out = out[: match.start(1)] + _REDACTED + out[match.end(1) :]
    return out
