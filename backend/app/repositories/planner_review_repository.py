"""PlannerReviewRepository — persistência do aggregate ``PlannerReview`` (ADR-199 §D3). R13/R14 (ADR-101): toda query inclui ``workspace_id``; orchestration vive na application layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.planner_review import PlannerReview


class PlannerReviewRepository:
    """Single Responsibility: persistência do aggregate ``PlannerReview``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_by_id(self, workspace_id: str, review_id: str) -> Optional[PlannerReview]:
        result = await self._session.execute(
            select(PlannerReview).where(
                PlannerReview.workspace_id == workspace_id,
                PlannerReview.id == review_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_for_run(
        self, workspace_id: str, pipeline_run_id: str
    ) -> Optional[PlannerReview]:
        """Parecer mais recente para um par (workspace, pipeline_run) — UNIQUE garante ≤1 row."""
        result = await self._session.execute(
            select(PlannerReview).where(
                PlannerReview.workspace_id == workspace_id,
                PlannerReview.pipeline_run_id == pipeline_run_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_for_workspace(self, workspace_id: str) -> Optional[PlannerReview]:
        """Parecer mais recente do workspace (ordena por created_at desc)."""
        result = await self._session.execute(
            select(PlannerReview)
            .where(PlannerReview.workspace_id == workspace_id)
            .order_by(PlannerReview.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: str) -> list[PlannerReview]:
        result = await self._session.execute(
            select(PlannerReview)
            .where(PlannerReview.workspace_id == workspace_id)
            .order_by(PlannerReview.created_at.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def add(self, review: PlannerReview) -> PlannerReview:
        self._session.add(review)
        await self._session.flush()
        return review

    async def publish(self, review_id: str, *, immutable_hash: str) -> None:
        """Flippa status Gerado → Publicado (ADR-204 §D2) — caller valida transição + gera hash."""
        now = datetime.now(timezone.utc)
        await self._session.execute(
            update(PlannerReview)
            .where(PlannerReview.id == review_id)
            .values(
                status="Publicado",
                published_at=now,
                immutable_hash=immutable_hash,
            )
        )

    async def mark_as_superseded(self, review_id: str, *, superseded_by_id: str) -> None:
        """Flippa status Publicado → Superseded (ADR-204 §D3) — caller já inseriu o sucessor."""
        now = datetime.now(timezone.utc)
        await self._session.execute(
            update(PlannerReview)
            .where(PlannerReview.id == review_id)
            .values(
                status="Superseded",
                superseded_by_id=superseded_by_id,
                superseded_at=now,
            )
        )

    async def create_or_get_for_run(self, review: PlannerReview) -> PlannerReview:
        """Persiste novo PlannerReview ou retorna existente (UNIQUE ws+run, ADR-199 §D3). Supersedure entre runs distintos via ``mark_as_superseded`` + ``supersedes_id``."""
        existing = await self.get_latest_for_run(review.workspace_id, review.pipeline_run_id)
        if existing is not None:
            return existing
        self._session.add(review)
        await self._session.flush()
        return review
