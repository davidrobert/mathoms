"""Ids de ``pipeline_artifacts`` intocáveis por qualquer rotina de deleção (ADR-371).

Fonte única. Antes desta extração cada rotina decidia sozinha o que era
intocável: ``artifact_prune`` excluía os referenciados, ``pipeline_reset`` e
``purge_reports`` não excluíam nada. Com ``PRAGMA foreign_keys=ON`` essa
divergência deixou de ser silenciosa — ``RESTRICT`` em
``report_publications.artifact_id`` e ``planner_reviews.e5_artifact_id``
aborta a transação inteira, e ``SET NULL``/``CASCADE`` destrói relatório
ou parecer publicado.

Toda coluna nova que aponte para ``pipeline_artifacts.id`` entra aqui —
o gate ``dev/check_delete_routine_coverage.py`` falha se ficar de fora.
"""

from __future__ import annotations

from typing import Collection

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.app.models.planner_review import PlannerReview
from backend.app.models.report import Report
from backend.app.models.report_publication import ReportPublication

__all__ = ["REFERENCING_COLUMNS", "referenced_artifact_ids", "referenced_artifact_ids_async"]

REFERENCING_COLUMNS = (
    Report.analysis_artifact_id,
    ReportPublication.artifact_id,
    PlannerReview.pipeline_artifact_id,
    PlannerReview.e5_artifact_id,
)


def _statements(ignore_report_ids: Collection[str] = ()) -> tuple[sa.Select, ...]:
    """``ignore_report_ids`` existe porque ``purge_reports`` deleta o Report e o
    artefato dele na mesma transação: a referência que o próprio purgado detém
    não pode bloquear o delete. Nenhum outro detentor é removível assim."""
    stmts = []
    for col in REFERENCING_COLUMNS:
        stmt = sa.select(col).where(col.is_not(None))
        if col is Report.analysis_artifact_id and ignore_report_ids:
            stmt = stmt.where(Report.id.not_in(ignore_report_ids))
        stmts.append(stmt)
    return tuple(stmts)


def referenced_artifact_ids(db: Session) -> frozenset[int]:
    """Ids referenciados por report / publicação / parecer — nunca deletáveis."""
    ids: set[int] = set()
    for stmt in _statements():
        ids.update(i for (i,) in db.execute(stmt) if i is not None)
    return frozenset(ids)


async def referenced_artifact_ids_async(
    db: AsyncSession, *, ignore_report_ids: Collection[str] = ()
) -> frozenset[int]:
    """Variante async — mesmo conjunto de colunas, para os call-sites do console."""
    ids: set[int] = set()
    for stmt in _statements(ignore_report_ids):
        ids.update(i for (i,) in await db.execute(stmt) if i is not None)
    return frozenset(ids)
