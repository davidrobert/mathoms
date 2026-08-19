"""Casamento entre chave de membro e texto livre ([[ADR-243]] · [[ADR-394]] §Emenda (b) D8).

`titular_key in nome` casa **dentro** de nome alheio: `"ana"` entra em
`"mariana"`, `"luis"` em `"luisa"`, `"marco"` em `"marcos"`. O casamento é por
**token normalizado** — a chave tem de ser um token inteiro do texto, não um
pedaço de um. Preserva o caso legítimo (`"david"` ↔ `"David Robert Silva"`), que
é por onde o baseline em lista-de-dicts resolve membro, e mata a colisão.
"""

from __future__ import annotations

import re
import unicodedata

_SEPARADORES = re.compile(r"[^a-z0-9]+")


def normalizar(texto: str | None) -> str:
    """ASCII minúsculo sem acento; `None`/vazio viram string vazia."""
    if not texto:
        return ""
    decomposto = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return sem_acento.lower().strip()


def tokens(texto: str | None) -> tuple[str, ...]:
    """Tokens normalizados do texto — a unidade de comparação."""
    return tuple(t for t in _SEPARADORES.split(normalizar(texto)) if t)


def matches_member_key(key: str | None, texto: str | None) -> bool:
    """`True` quando `key` é um token inteiro de `texto` (ou o texto todo)."""
    chave = normalizar(key)
    if not chave or not texto:
        return False
    alvo = tokens(texto)
    chave_tokens = tokens(key)
    # Chave multi-token (`"david_robert"`, `"maria clara"`) casa como subsequência
    # de tokens; chave de 1 token casa por pertencimento.
    if len(chave_tokens) > 1:
        return _subsequencia(chave_tokens, alvo)
    return chave in alvo


def _subsequencia(agulha: tuple[str, ...], palheiro: tuple[str, ...]) -> bool:
    n = len(agulha)
    return any(palheiro[i : i + n] == agulha for i in range(len(palheiro) - n + 1))


def matches_member_exclusively(key: str | None, outra_key: str | None, texto: str | None) -> bool:
    """`texto` nomeia `key` e **não** a outra — o predicado de posse exclusiva."""
    if not key or not matches_member_key(key, texto):
        return False
    return not matches_member_key(outra_key, texto)


__all__ = ["matches_member_exclusively", "matches_member_key", "normalizar", "tokens"]
