"""Erros de domínio tipados da application layer (ADR-101 R15).

Use cases levantam estas exceções ao invés de ``HTTPException``. Routers
traduzem para HTTP no boundary — mapping tipo → status HTTP vive nos
routers (404, 409, 422).

Campo ``code`` permite discriminar ramos do mesmo tipo no router quando
preciso (ex.: ``ConflictError(code="duplicate_key", ...)``).
"""

from __future__ import annotations


class DomainError(Exception):
    """Base de todos os erros de negócio emitidos por use cases.

    Nunca seja levantada diretamente — use subclasses específicas
    (``NotFoundError``, ``ConflictError``, ``ValidationError``).
    """

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.code = code
        super().__init__(message)


class NotFoundError(DomainError):
    """Recurso solicitado não existe no workspace. Router → 404."""


class ConflictError(DomainError):
    """Violação de invariante de unicidade (key/code duplicado). Router → 409."""


class ValidationError(DomainError):
    """Input passou pela validação do DTO mas viola regra de negócio. Router → 422."""


class AuthenticationError(DomainError):
    """Credenciais inválidas ou ausentes. Router → 401."""


class AccountLockedError(AuthenticationError):
    """Conta bloqueada por excesso de tentativas (7B.13). Router → 429 + Retry-After."""

    def __init__(
        self, message: str, *, retry_after_s: int, code: str | None = "account_locked"
    ) -> None:
        super().__init__(message, code=code)
        self.retry_after_s = int(retry_after_s)
