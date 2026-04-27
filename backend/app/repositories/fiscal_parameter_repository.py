"""FiscalParameterRepository — leitura sync por vigência (ADR-135 · A7.2b)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.fiscal_parameter import FiscalParameter


class FiscalParameterAmbiguous(RuntimeError):
    """Mais de uma row de ``fiscal_parameters`` cobre o período solicitado."""


class FiscalParameterNotFound(RuntimeError):
    """Nenhuma row de ``fiscal_parameters`` cobre o período solicitado."""


class FiscalParameterRepository:
    """Leitura sync de ``fiscal_parameters`` (consumido pelo worker)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_covering_period(self, period_start: date, period_end: date) -> list[FiscalParameter]:
        """Lista rows com vigência cobrindo ``[period_start, period_end]``."""
        stmt = (
            select(FiscalParameter)
            .where(FiscalParameter.effective_from <= period_start)
            .where(
                (FiscalParameter.effective_to.is_(None))
                | (FiscalParameter.effective_to >= period_end)
            )
            .order_by(FiscalParameter.effective_from.desc())
        )
        return list(self._session.execute(stmt).scalars().all())

    def get_for_period(self, period_start: date, period_end: date) -> FiscalParameter:
        """Retorna a única row cobrindo o período; raise se 0 ou ≥2."""
        rows = self.list_covering_period(period_start, period_end)
        if not rows:
            raise FiscalParameterNotFound(
                f"No fiscal_parameters row covers [{period_start}, {period_end}]."
            )
        if len(rows) > 1:
            ids = ", ".join(str(r.id) for r in rows)
            raise FiscalParameterAmbiguous(
                f"Multiple fiscal_parameters rows cover [{period_start}, {period_end}]: {ids}. "
                "Adjust effective_from/to ranges to be exclusive (ADR-135)."
            )
        return rows[0]

    def get_by_year(self, year: int) -> FiscalParameter | None:
        """Lookup direto por ano fiscal (helper para seeds e admin)."""
        stmt = select(FiscalParameter).where(FiscalParameter.year == year)
        return self._session.execute(stmt).scalars().first()

    def list_all(self) -> list[FiscalParameter]:
        """Lista todas as rows ordenadas por ``effective_from`` desc."""
        stmt = select(FiscalParameter).order_by(FiscalParameter.effective_from.desc())
        return list(self._session.execute(stmt).scalars().all())
