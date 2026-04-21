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
