"""Matching determinístico documento→membro por CPF (ADR-259 §2 · A20.l15).

O LLM não emite CPF; o matching acontece FORA do boundary LLM: regex sobre o
texto do documento original × CPFs (decriptados in-memory) do config de
membros. O CPF nunca persiste em artifact nem em log — só o ``member_key``
resolvido.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional, Protocol

from pipeline.domain.services._cpf_identity import normalize_cpf

# CPF com ou sem máscara: 123.456.789-09 | 12345678909. Grupos de pontuação
# opcionais evitam capturar sequências de 11 dígitos dentro de números maiores.
_CPF_RE = re.compile(r"(?<!\d)(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})(?!\d)")


class _MemberWithCpf(Protocol):
    key: str
    cpf: Optional[str]


def extract_document_cpfs(text: str) -> set[str]:
    """CPFs normalizados (11 dígitos) encontrados no texto do documento."""
    return {"".join(m.groups()) for m in _CPF_RE.finditer(text or "")}


def resolve_member_key_by_cpf(text: str, members: Iterable[_MemberWithCpf]) -> Optional[str]:
    """``member_key`` cujo CPF (config) aparece no documento; ambíguo (0 ou 2+ matches, ex. IRPF conjunta) degrada para ``None`` — atribuição errada é pior que ausente."""
    doc_cpfs = extract_document_cpfs(text)
    if not doc_cpfs:
        return None
    matched = {m.key for m in members if normalize_cpf(m.cpf or "") in doc_cpfs}
    return matched.pop() if len(matched) == 1 else None
