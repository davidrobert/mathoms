"""VaultService — Fernet-encrypted password storage for PDF unlocking."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from backend.app.core.config import settings


class VaultService:
    """Encrypts/decrypts PDF passwords using Fernet symmetric encryption."""

    def __init__(self, key: str = ""):
        fernet_key = key or settings.FERNET_KEY
        if not fernet_key:
            fernet_key = Fernet.generate_key().decode()
        self._fernet = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a password. Returns base64-encoded ciphertext."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str | None:
        """Decrypt a password. Returns None if decryption fails."""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except (InvalidToken, Exception):
            return None
