"""Seed service — imports existing pipeline reports into the database."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.report import Report
from backend.app.models.user import User
from backend.app.models.workspace import Workspace


async def seed_existing_reports(
    db: AsyncSession,
    user_id: str,
    workspace_id: str,
    output_dir: Optional[Path] = None,
) -> list[dict]:
    """Scan output/ for HTML reports and import them into the database.

    Returns list of dicts with imported report info.
    """
    if output_dir is None:
        from backend.app.core.config import settings
        output_dir = Path(settings.PIPELINE_ROOT) / "output"

    if not output_dir.is_dir():
        return []

    html_files = sorted(output_dir.glob("relatorio_financeiro_*.html"))
    if not html_files:
        return []

    imported = []
    for html_path in html_files:
        existing = await db.execute(
            select(Report).where(Report.html_path == str(html_path))
        )
        if existing.scalar_one_or_none():
            continue

        date_match = re.search(r"(\d{8})", html_path.stem)
        date_str = date_match.group(1) if date_match else ""
        period = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}" if len(date_str) == 8 else ""

        report = Report(
            workspace_id=workspace_id,
            title=f"Relatório Financeiro — {period}" if period else html_path.stem,
            period=period,
            html_path=str(html_path.resolve()),
            size_bytes=html_path.stat().st_size,
        )
        db.add(report)
        imported.append({"title": report.title, "path": str(html_path), "size": report.size_bytes})

    if imported:
        await db.commit()

    return imported


async def ensure_seed_user(db: AsyncSession) -> tuple[User, Workspace]:
    """Get or create the default seed user + workspace for CLI-generated reports."""
    from backend.app.core.security import hash_password

    result = await db.execute(select(User).where(User.email == "admin@fin.app"))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email="admin@fin.app",
            hashed_password=hash_password("admin"),
            full_name="Admin (Seed)",
        )
        db.add(user)
        await db.flush()

        ws = Workspace(name="Workspace Principal", owner_id=user.id)
        db.add(ws)
        await db.commit()
        await db.refresh(user)
    else:
        ws_result = await db.execute(
            select(Workspace).where(Workspace.owner_id == user.id)
        )
        ws = ws_result.scalar_one_or_none()

    return user, ws
