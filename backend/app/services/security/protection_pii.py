"""PII helpers para `Protection` (ADR-192) — Fernet vault + coverage bucketing."""

from __future__ import annotations

from typing import Optional

from backend.app.services.vault import get_vault

# Faixas (cents):
#   bucket 0  → < R$ 100k
#   bucket 1  → R$ 100k - 1M
#   bucket 2  → R$ 1M - 5M
#   bucket 3  → R$ 5M - 10M
#   bucket 4  → R$ 10M - 50M
#   bucket 5  → R$ 50M+
_COVERAGE_BUCKET_CEILINGS_CENTS: tuple[int, ...] = (
    100_000_00,
    1_000_000_00,
    5_000_000_00,
    10_000_000_00,
    50_000_000_00,
)


def encrypt_policy_ref(plaintext: Optional[str] = None) -> Optional[str]:
    """``None``/empty → ``None``. Caso contrário, retorna ciphertext Fernet."""
    if plaintext is None:
        return None
    stripped = plaintext.strip()
    if not stripped:
        return None
    try:
        return get_vault().encrypt(stripped)
    except RuntimeError:
        # Sem FERNET_KEY (dev/test sem vault) — preserva valor original.
        return stripped


def decrypt_policy_ref(ciphertext: Optional[str] = None) -> Optional[str]:
    """Decifra ``policy_ref`` cifrado; retorna ``None`` em falha."""
    if ciphertext is None:
        return None
    try:
        decrypted = get_vault().decrypt(ciphertext)
    except RuntimeError:
        return ciphertext
    return decrypted if decrypted is not None else None


def mask_coverage_bucket(coverage_brl_cents: Optional[int] = None) -> int:
    """Capital segurado → índice 0-5 (anti-fingerprinting em logs)."""
    if coverage_brl_cents is None or coverage_brl_cents <= 0:
        return 0
    for idx, ceiling in enumerate(_COVERAGE_BUCKET_CEILINGS_CENTS):
        if coverage_brl_cents < ceiling:
            return idx
    return len(_COVERAGE_BUCKET_CEILINGS_CENTS)
