"""F11.6b — snapshot mínimo de premissas no momento da geração do relatório."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.goal import VALID_GOAL_TYPES, Goal


def build_premissas_snapshot_sync(
    workspace_id: str,
    tenant_root: Path,
    db: Session,
) -> dict | None:
    """Monta referência para comparação mês a mês: hash do ``goals.json``
    materializado + metadados das metas vigentes no DB.

    Retorna ``None`` se não há ``goals.json`` nem metas ativas (workspace vazio).
    """
    goals_path = tenant_root / "config" / "goals.json"
    sha256: str | None = None
    if goals_path.is_file():
        raw = goals_path.read_bytes()
        sha256 = hashlib.sha256(raw).hexdigest()

    stmt = select(Goal).where(
        Goal.workspace_id == workspace_id,
        Goal.effective_to.is_(None),
    )
    goals = list(db.scalars(stmt).all())
    # Filtra tipos removidos do contrato (ex.: PLANNING_CONTEXT pós-ADR-180):
    # linhas órfãs em workspaces seedados antes de A10.6 não devem vazar para o
    # relatório.
    active_refs = [
        {
            "type": g.type,
            "id": g.id,
            "effective_from": g.effective_from.isoformat(),
        }
        for g in goals
        if g.type in VALID_GOAL_TYPES
    ]

    if sha256 is None and not active_refs:
        return None

    return {
        "schema": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "goals_json_sha256": sha256,
        "active_goals": active_refs,
    }
