"""BusinessProfile — perfil tributário/PJ do workspace (Sprint A10.7 · ADR-A10.7)."""

# Substitui a chave `tributario` da bag PLANNING_CONTEXT (legado goals.json).
# Estrutura simples, cliente-PJ-específica — JSON livre em
# Workspace.business_profile_json valida shape via este model no boundary HTTP.
# Aggregate dedicado fica como follow-up A11+ se surgir demanda de versionamento.

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# Regimes PJ aceitos. ``None`` = ainda não definido (workspace recém-criado).
RegimeTributario = Literal[
    "mei",
    "lucro_presumido",
    "lucro_real",
    "simples",
]


class BusinessProfile(BaseModel):
    """Perfil tributário/PJ do workspace (todos campos opcionais até consultor preencher)."""

    contador: Optional[str] = Field(
        default=None,
        description="Nome ou contato do contador responsável (texto livre).",
        max_length=255,
    )
    regime: Optional[RegimeTributario] = Field(
        default=None,
        description="Regime tributário PJ atual.",
    )
    holding_prazo_meses: Optional[int] = Field(
        default=None,
        description="Prazo (em meses) para constituir holding patrimonial.",
        ge=0,
        le=240,  # 20 anos — limite sensato; manualmente revisado
    )

    model_config = {"extra": "forbid"}


class BusinessProfileResponse(BaseModel):
    """Resposta do GET/PATCH — espelha shape de `BusinessProfile`."""

    contador: Optional[str] = None
    regime: Optional[RegimeTributario] = None
    holding_prazo_meses: Optional[int] = None
