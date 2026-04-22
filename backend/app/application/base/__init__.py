"""Base types da application layer — erros de domínio (ADR-101 R15)."""

from backend.app.application.base.errors import (
    AuthenticationError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)

__all__ = [
    "AuthenticationError",
    "ConflictError",
    "DomainError",
    "NotFoundError",
    "ValidationError",
]
