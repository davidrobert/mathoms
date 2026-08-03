"""``DBTributarioSectionResolver`` — impl DB do port (RV3-11 · A40.l9 PR2)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("mathoms.tributario.section_resolver")


# Injetado em WorkspaceContext.tributario_section_resolver por
# run_context_factory._db_resolvers; a sessão é a mesma read-only que respalda
# o ConfigStore (viva durante o run inteiro).
@dataclass(frozen=True)
class DBTributarioSectionResolver:
    """Resolve a seção tributária em stage-time, do último run COM E4."""

    session: Session

    def resolve(self, workspace_id: str) -> Optional[dict[str, Any]]:
        # Import local: pipeline_adapter importa meio backend; manter lazy evita
        # ciclo com run_context_factory (mesmo padrão dos demais resolvers).
        from backend.app.services.pipeline.pipeline_adapter import (
            _build_tributario_section_sync,
        )

        try:
            return dict(_build_tributario_section_sync(workspace_id, db=self.session))
        except Exception as exc:  # noqa: BLE001 — resolver é best-effort; caller degrada
            logger.warning(
                "tributario_section_resolver_failed",
                extra={"workspace_id": workspace_id, "error": type(exc).__name__},
            )
            return None
