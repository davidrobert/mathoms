"""DTOs do agregado ``Debt`` (ADR-227 §D1) — re-exports."""

from backend.app.schemas.dto.debt.command import DebtCreate, DebtUpdate
from backend.app.schemas.dto.debt.response import DebtResponse

__all__ = ["DebtCreate", "DebtUpdate", "DebtResponse"]
