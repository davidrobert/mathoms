"""VaultService — Fernet-encrypted storage for secrets (PDF passwords, LLM keys, CPF).

Fail-fast sem `FERNET_KEY`: sem uma chave estável, secrets cifrados viram
ilegíveis no próximo restart (regressão OP-008). Por isso, instanciar
`VaultService()` sem `settings.FERNET_KEY` definido levanta `RuntimeError`.

Todos os módulos devem usar `get_vault()` (singleton process-wide) para
garantir a mesma chave — evita o bug onde `VaultService()` no topo de
módulos distintos gerava chaves diferentes e cifras não decifravam cruzadas.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from backend.app.core.config import settings


class VaultService:
    """Encrypts/decrypts secrets using Fernet symmetric encryption."""

    def __init__(self, key: str = ""):
        fernet_key = key or settings.FERNET_KEY
        if not fernet_key:
            raise RuntimeError(
                "MATHOMS_FERNET_KEY não configurada. Gere uma key estável e "
                "adicione ao .env do backend:\n"
                '  python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"\n'
                "Depois: MATHOMS_FERNET_KEY=<valor> em .env e reinicie o backend."
            )
        self._fernet = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a secret. Returns base64-encoded ciphertext."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str | None:
        """Decrypt a secret. Returns None if decryption fails."""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except (InvalidToken, Exception):
            return None


_singleton: VaultService | None = None


def get_vault() -> VaultService:
    """Singleton accessor — garante a mesma Fernet key em todos os módulos."""
    global _singleton
    if _singleton is None:
        _singleton = VaultService()
    return _singleton
