"""Base compartilhada de response DTOs do agregado ``Goal``.

Campos comuns a todos os 4 tipos (IF, Aporte, Dólar, Alocação) ficam
em ``GoalResponseBase``. Cada tipo estende com ``inputs`` e ``derived``
específicos + ``type`` como ``Literal``.

Renomeado do legado ``_GoalResponseBase`` (leading underscore removido
— é intencionalmente público agora, ponto de extensão comum para os 4
response types do pacote).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GoalResponseBase(BaseModel):
    """Campos comuns a todas as respostas de Goal."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    meta_version: int = Field(
        1,
        description="Versão do schema canônico em `params_json` (goal.*.schema.json).",
    )
    effective_from: date
    effective_to: Optional[date] = None
    is_template: bool = False
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_by_name: Optional[str] = Field(
        None,
        description=(
            "Nome humano do autor da versão (join com users.full_name). "
            "Usado para atribuição de autoria na UI (F9)."
        ),
    )
    created_at: datetime
    updated_at: datetime
