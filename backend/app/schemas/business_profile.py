"""BusinessProfile — perfil tributário/PJ do workspace (Sprint A10.7 + A16 · ADR-236)."""

# Substitui a chave `tributario` da bag PLANNING_CONTEXT (legado goals.json).
# Estrutura simples, cliente-PJ-específica — JSON livre em
# Workspace.business_profile_json valida shape via este model no boundary HTTP.
#
# Sprint A16 (ADR-236) — expandido com 4 campos declarados-pelo-consultor
# (anexo_simples, iss_aliquota_pct, cnae_principal, tipo_declaracao_ir).
# Demais inputs da cascata fiscal (pró-labore, lucros, folha, DAS, ISS,
# receita PJ, renda tributável PF) **derivam** de E3/E4/E1.6 — não vivem
# aqui (ADR-236 §D2 "derivado ≫ declarado").

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

# Anexo Simples Nacional relevante para serviços (fator-R) — só faz sentido
# quando regime=simples. III: fator-R ≥ 0,28; V: < 0,28.
AnexoSimples = Literal["III", "V"]

# Modelo IRPF da pessoa física — simplificada anula dedução PGBL
# (desconto simplificado substitui deduções legais).
TipoDeclaracaoIR = Literal["completa", "simplificada"]


class BusinessProfile(BaseModel):
    """Perfil tributário/PJ do workspace (todos campos opcionais até consultor preencher)."""

    # Campos A10.7 (preservados — não-breaking).
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
        le=240,
    )

    # Campos A16 (novos — ADR-236 §D1).
    anexo_simples: Optional[AnexoSimples] = Field(
        default=None,
        description=(
            "Anexo do Simples Nacional (relevante só quando regime=simples). "
            "III: serviços com fator-R ≥ 0,28; V: < 0,28."
        ),
    )
    iss_aliquota_pct: Optional[float] = Field(
        default=None,
        description=(
            "Alíquota ISS municipal aplicável ao CNAE principal. "
            "2-5% conforme Lei Complementar 116/2003."
        ),
        ge=2.0,
        le=5.0,
    )
    cnae_principal: Optional[str] = Field(
        default=None,
        description=(
            "CNAE 7-dígitos da atividade principal (formato 'NNNN-N/NN'). "
            "Valida Anexo Simples + ISS aplicável."
        ),
        max_length=10,
    )
    tipo_declaracao_ir: Optional[TipoDeclaracaoIR] = Field(
        default=None,
        description=(
            "Modelo IRPF da pessoa física. Simplificada anula dedução PGBL "
            "(desconto simplificado substitui deduções legais)."
        ),
    )

    model_config = {"extra": "forbid"}


class BusinessProfileResponse(BaseModel):
    """Resposta do GET/PATCH — espelha shape de `BusinessProfile`."""

    contador: Optional[str] = None
    regime: Optional[RegimeTributario] = None
    holding_prazo_meses: Optional[int] = None
    anexo_simples: Optional[AnexoSimples] = None
    iss_aliquota_pct: Optional[float] = None
    cnae_principal: Optional[str] = None
    tipo_declaracao_ir: Optional[TipoDeclaracaoIR] = None
