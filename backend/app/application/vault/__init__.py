"""Use cases do agregado ``PasswordVault`` (ADR-072 · ADR-101 R15).

Secrets Fernet-cifrados (PDF passwords, LLM keys). Cryptography delegada
a :class:`VaultService`; use cases apenas orquestram persistência.
"""

from backend.app.application.vault.create_password import create_password
from backend.app.application.vault.delete_password import delete_password
from backend.app.application.vault.list_passwords import list_passwords

__all__ = ["create_password", "delete_password", "list_passwords"]
