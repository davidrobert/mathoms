"""VaultService — Fernet-encrypted storage for secrets (PDF passwords, LLM keys, CPF).

Fail-fast sem `FERNET_KEY`: sem uma chave estável, secrets cifrados viram
ilegíveis no próximo restart (regressão OP-008). Por isso, instanciar
`VaultService()` sem `settings.FERNET_KEY` definido levanta `RuntimeError`.

Rotação (ADR-171): `MATHOMS_FERNET_KEYS=key_nova,key_antiga` (CSV) monta
`MultiFernet` — encrypt sempre com a primeira (primária); decrypt tenta
todas. `FERNET_KEY` single permanece o caminho default fora de janela de
rotação. Re-encrypt em batch via task `rotate_fernet_secrets` (runbook em
docs/reference/runbooks/fernet_rotation.md).

Todos os módulos devem usar `get_vault()` (singleton process-wide) para
garantir a mesma chave — evita o bug onde `VaultService()` no topo de
módulos distintos gerava chaves diferentes e cifras não decifravam cruzadas.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from backend.app.core.config import settings


def resolve_fernet_keys(explicit: str = "") -> list[str]:
    """Chaves ativas em ordem: primeira = primária (encrypt), demais decrypt-only.

    Precedência: ``explicit`` (testes) > ``FERNET_KEYS`` CSV (janela de
    rotação, ADR-171) > ``FERNET_KEY`` single.
    """
    raw = explicit or settings.FERNET_KEYS or settings.FERNET_KEY
    return [k.strip() for k in raw.split(",") if k.strip()] if raw else []


def primary_fernet_key() -> str:
    """Key primária vigente — fonte do ``kid`` de artifacts (crypto._key_id)."""
    keys = resolve_fernet_keys()
    return keys[0] if keys else ""


class VaultService:
    """Encrypts/decrypts secrets using Fernet symmetric encryption."""

    def __init__(self, key: str = ""):
        keys = resolve_fernet_keys(key)
        if not keys:
            raise RuntimeError(
                "MATHOMS_FERNET_KEY não configurada. Gere uma key estável e "
                "adicione ao .env do backend:\n"
                '  python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"\n'
                "Depois: MATHOMS_FERNET_KEY=<valor> em .env e reinicie o backend.\n"
                "Em janela de rotação: MATHOMS_FERNET_KEYS=key_nova,key_antiga (ADR-171)."
            )
        fernets = [Fernet(k.encode() if isinstance(k, str) else k) for k in keys]
        self._primary = fernets[0]
        self._fernet = MultiFernet(fernets)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a secret with the primary key. Returns base64-encoded ciphertext."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str | None:
        """Decrypt a secret (tries every active key). Returns None if decryption fails."""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except (InvalidToken, Exception):
            return None

    def needs_rotation(self, ciphertext: str) -> bool:
        """True se o ciphertext só decifra com key secundária (re-encrypt pendente)."""
        try:
            self._primary.decrypt(ciphertext.encode())
            return False
        except (InvalidToken, Exception):
            pass
        return self.decrypt(ciphertext) is not None


_singleton: VaultService | None = None


def get_vault() -> VaultService:
    """Singleton accessor — garante a mesma Fernet key em todos os módulos."""
    global _singleton
    if _singleton is None:
        _singleton = VaultService()
    return _singleton
