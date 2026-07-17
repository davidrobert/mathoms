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


def scrub_identifiers(text: str) -> str:
    """Substitui CPF e CNPJ por token de redação (idempotente)."""
    return _CNPJ.sub(_REDACTED, _CPF.sub(_REDACTED, text))


def contains_identifier(text: str) -> bool:
    """True se o texto contém CPF ou CNPJ — usado pelo gate PII-scan."""
    return bool(_CPF.search(text) or _CNPJ.search(text))
