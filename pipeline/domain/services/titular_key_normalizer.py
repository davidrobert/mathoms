"""Normaliza titular_key extraído por LLM ao canônico do workspace (ADR-215 fix-B3)."""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.domain.types.config import FamilyMembersConfig


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _to_tokens(raw: str) -> frozenset[str]:
    if not raw:
        return frozenset()
    norm = _strip_accents(raw).lower()
    # `raw` chega como "mariana_teixeira_ferreira" (LLM) ou full_name livre
    norm = norm.replace("_", " ").replace("-", " ")
    return frozenset(t for t in norm.split() if t)


def _member_alias_tokens(member) -> frozenset[str]:
    """Tokens canônicos do member (key + full_name + aliases extras)."""
    tokens: set[str] = set()
    tokens |= _to_tokens(member.key)
    tokens |= _to_tokens(member.full_name)
    extra_aliases = (
        member.extra.get("titular_key_aliases") if isinstance(member.extra, dict) else None
    )
    if isinstance(extra_aliases, (list, tuple)):
        for alias in extra_aliases:
            if isinstance(alias, str):
                tokens |= _to_tokens(alias)
    return frozenset(tokens)


def normalize_titular_key(raw: str, family_members: "FamilyMembersConfig | None") -> str:
    """Mapeia LLM-extracted raw key → canônico do workspace."""
    # Retorna `raw` se nenhum member tiver token em comum (preserva legado).
    # Match wins por maior intersection de tokens.
    if not raw or family_members is None:
        return raw
    raw_tokens = _to_tokens(raw)
    if not raw_tokens:
        return raw
    best_key, best_score = raw, 0
    for member in family_members.members:
        if raw == member.key:
            return member.key
        score = len(raw_tokens & _member_alias_tokens(member))
        if score > best_score:
            best_key, best_score = member.key, score
    return best_key


__all__ = ["normalize_titular_key"]
