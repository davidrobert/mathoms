"""Revisão do executor — normalização do valor pinado no launch (ADR-362).

Módulo sem imports de propósito: o teste alcança sem puxar `Settings` (que
carrega Fernet no import).
"""

from __future__ import annotations

_SHA_LEN = 12
_DIRTY_SUFFIX = "-dirty"


def normalize_executor_revision(raw: str | None) -> str | None:
    """Trunca o sha a 12 chars preservando `-dirty`; None ≡ desconhecido."""
    # Truncar no boundary é a defesa de largura: `varchar` no Postgres REJEITA o
    # INSERT acima do limite, e o CI injeta `${{ github.sha }}` de 40 chars. Sem
    # isto, um typo de env var derrubaria o INSERT do primeiro stage de todo run.
    # Nunca levanta: o campo é observabilidade, e o critério da ADR-362 exige que
    # o processo SUBA sem a env — matar o boot por causa dele inverteria o trade.
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value:
        return None
    dirty = value.endswith(_DIRTY_SUFFIX)
    sha = value[: -len(_DIRTY_SUFFIX)] if dirty else value
    sha = sha.strip()
    if not sha:
        return None
    return f"{sha[:_SHA_LEN]}{_DIRTY_SUFFIX if dirty else ''}"
