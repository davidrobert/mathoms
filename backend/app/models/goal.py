"""Goal model — ADR-073.

Meta versionada por workspace. Cada edição cria novo registro com
`effective_from = hoje` e fecha o anterior com `effective_to = ontem`.
Registro vigente é único por `(workspace_id, type)` e tem
`effective_to IS NULL`.

`params_json` segue o schema canônico por tipo:
  - `INDEPENDENCIA_FINANCEIRA` → `config/schemas/goal.if.schema.json`

`derived_json` é snapshot dos valores calculados no momento da criação
do registro. Função pura `goal_service.compute_if_derived(inputs)` é a
única fonte desses valores — frontend chama `/goals/if/compute` para
preview, pipeline usa o mesmo service via adapter.

Em F8.1 apenas `INDEPENDENCIA_FINANCEIRA` é implementado. Outros tipos
(APORTE_MENSAL, DOLARIZACAO, ALOCACAO_ALVO) ficam como débito F8.5+ e
continuam sendo servidos pelo adapter a partir de `config/goals.json`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, date
from typing import Optional

from sqlalchemy import String, DateTime, Date, ForeignKey, JSON, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


# Tipos aceitos. Mantido como frozenset para permitir adicionar novos
# valores sem migration (só adicionar a literal aqui + validar no service).
#
# F8.1 — INDEPENDENCIA_FINANCEIRA (único tipo inicial)
# F8.4 — adicionados APORTE_MENSAL, DOLARIZACAO, ALOCACAO_ALVO para
#        destravar migração completa do `config/goals.json` (ADR-075).
VALID_GOAL_TYPES: frozenset[str] = frozenset(
    {
        "INDEPENDENCIA_FINANCEIRA",
        "APORTE_MENSAL",
        "DOLARIZACAO",
        "ALOCACAO_ALVO",
        # F8.4: bucket genérico para seções restantes do goals.json
        # que não justificam um Goal type dedicado (fase_f1f2, seguros,
        # tributario, imoveis, riscos, referencias, etc.)
        "PLANNING_CONTEXT",
    }
)


class Goal(Base):
    """Meta financeira versionada. Imutável por design — edições criam
    novo registro, não atualizam o anterior."""

    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    params_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    derived_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Flag indicando seed template (força wizard no onboarding)
    is_template: Mapped[bool] = mapped_column(
        default=False, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    workspace = relationship("Workspace")
    creator = relationship("User")

    __table_args__ = (
        # Lookup do vigente por (workspace, type, effective_to IS NULL)
        Index("ix_goals_ws_type_effective_to", "workspace_id", "type", "effective_to"),
        # Histórico ordenado por effective_from
        Index("ix_goals_ws_type_effective_from", "workspace_id", "type", "effective_from"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Goal ws={self.workspace_id} type={self.type} "
            f"effective_from={self.effective_from} "
            f"{'vigente' if self.effective_to is None else f'fechado {self.effective_to}'}>"
        )
