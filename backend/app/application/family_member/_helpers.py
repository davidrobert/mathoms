"""Helpers internos do agregado ``FamilyMember`` — slug + birth_name.

Funções puras extraídas do antigo router ``config.py`` para que os use
cases fiquem curtos. Não dependem de repo, vault, session.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from backend.app.application.base.errors import ConflictError
from backend.app.application.family_member._protocols import (
    FamilyMemberRepositoryProtocol,
)


def slug_member_key_from_full_name(full_name: str, *, max_len: int = 50) -> str:
    """Normaliza ``full_name`` para um slug ASCII-lowercase-underscore."""
    s = unicodedata.normalize("NFKD", (full_name or "").strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_") or "membro"
    if len(s) > max_len:
        s = s[:max_len].rstrip("_") or "membro"
    return s


async def allocate_unique_member_key(
    repo: FamilyMemberRepositoryProtocol,
    workspace_id: str,
    base: str,
    *,
    max_len: int = 50,
) -> str:
    """Busca primeira variação ``base``, ``base_1``, ``base_2``… livre no workspace."""
    base = (base or "membro")[:max_len].rstrip("_") or "membro"
    for n in range(0, 10_000):
        candidate = base if n == 0 else f"{base}_{n}"
        if len(candidate) > max_len:
            candidate = candidate[:max_len]
        if not await repo.key_exists(workspace_id, candidate):
            return candidate
    raise ConflictError(
        "Não foi possível gerar um identificador interno único; "
        "tente informar o identificador manualmente.",
        code="key_allocation_exhausted",
    )


def extra_with_birth_name(
    current: dict[str, Any] | None,
    birth_name: str | None,
) -> dict[str, Any] | None:
    """Aplica ``birth_name`` ao dict ``extra``, preservando outras chaves.

    - ``birth_name=None`` → mantém extra como está (ausente = sem update).
    - ``birth_name`` string não-vazia → seta ``extra['nome_nascimento']``.
    - ``birth_name`` whitespace/vazio → remove ``nome_nascimento``.
    """
    extra = dict(current or {})
    if birth_name is None:
        return extra or None
    s = birth_name.strip()
    if s:
        extra["nome_nascimento"] = s
    else:
        extra.pop("nome_nascimento", None)
    return extra or None
