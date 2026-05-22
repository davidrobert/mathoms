"""Schema apólice de seguro polimórfica (Discriminated Union 2 níveis) — A18 L2 P1 (ADR-239 D2)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Bump quando alterar prompt ``apolice`` de modo que afete output (ADR-144 cache).
PROMPT_VERSION = "apolice-v1.0.0"


# ===========================================================================
# Sub-models — strict, antecipam V2 (vida/saúde/acidentes) já em V1
# ===========================================================================


class EnderecoStruct(BaseModel):
    """Endereço estruturado de imóvel segurado (ADR-216 alinhado)."""

    model_config = ConfigDict(extra="forbid")

    logradouro: str = Field(..., min_length=2, max_length=200)
    numero: Optional[str] = Field(None, max_length=20)
    complemento: Optional[str] = Field(None, max_length=80)
    bairro: Optional[str] = Field(None, max_length=80)
    cidade: str = Field(..., min_length=2, max_length=80)
    uf: str = Field(..., pattern=r"^[A-Z]{2}$")
    cep: Optional[str] = Field(None, pattern=r"^\d{5}-?\d{3}$")


class CongenereRef(BaseModel):
    """Apólice anterior em outra seguradora (preserva classe de bônus inter-seguradora)."""

    model_config = ConfigDict(extra="forbid")

    seguradora: str = Field(..., min_length=2, max_length=60)
    apolice_numero: str = Field(..., min_length=1, max_length=40)


class CorretorRef(BaseModel):
    """Corretor PJ (CNPJ majoritário) ou PF (CPF + SUSEP) com discriminator."""

    model_config = ConfigDict(extra="forbid")

    susep_code: str = Field(..., pattern=r"^\d{6,12}$")
    nome: str = Field(..., min_length=2, max_length=120)
    cpf_or_cnpj: str = Field(..., pattern=r"^\d{11}$|^\d{14}$")
    cnpj_or_cpf_kind: Literal["cnpj", "cpf"]

    @field_validator("cpf_or_cnpj", mode="before")
    @classmethod
    def _strip_punctuation(cls, v):
        if not isinstance(v, str):
            return v
        return v.replace(".", "").replace("-", "").replace("/", "").strip()


class BeneficiarioRef(BaseModel):
    """Beneficiário de cobertura vida (V2 placeholder em V1)."""

    model_config = ConfigDict(extra="forbid")

    nome: str = Field(..., min_length=2, max_length=120)
    parentesco: Optional[str] = Field(None, max_length=40)
    family_member_id: Optional[str] = Field(None, max_length=36)
    percentual: Decimal = Field(..., ge=0, le=100)


# ---- Coberturas (Discriminated Union por `tipo`) -------------------------


class CoberturaMaterial(BaseModel):
    """Cobertura material (auto: colisão/incêndio/roubo; imóvel: incêndio/vendaval/raio)."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["material"]
    nome: str = Field(..., min_length=2, max_length=120)
    ramo_susep: Optional[str] = Field(None, max_length=20)
    lmi_modo: Literal["valor_fixo", "fipe_percentual", "primeiro_risco_absoluto"]
    lmi_brl: Optional[Decimal] = Field(None, ge=0)
    lmi_fipe_percentual: Optional[Decimal] = Field(None, ge=0, le=2)
    franquia_brl: Optional[Decimal] = Field(None, ge=0)
    premio_brl: Decimal = Field(..., ge=0)


class CoberturaRcfv(BaseModel):
    """Responsabilidade Civil Facultativa de Veículo (danos a terceiros)."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["rcfv"]
    nome: Literal["danos_materiais", "danos_corporais", "danos_morais"]
    lmi_brl: Decimal = Field(..., ge=0)
    premio_brl: Decimal = Field(..., ge=0)


class CoberturaVida(BaseModel):
    """V2 — placeholder em V1 (schema antecipa para evitar migration breaking)."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["vida"]
    capital_segurado_brl: Decimal = Field(..., ge=0)
    beneficiarios: list[BeneficiarioRef] = Field(default_factory=list)
    premio_brl: Decimal = Field(..., ge=0)


class CoberturaSaude(BaseModel):
    """V2 — placeholder em V1."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["saude"]
    rede_credenciada: Optional[str] = Field(None, max_length=200)
    capital_segurado_brl: Optional[Decimal] = Field(None, ge=0)
    premio_brl: Decimal = Field(..., ge=0)


class CoberturaAcidentes(BaseModel):
    """V2 — placeholder em V1."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["acidentes"]
    capital_segurado_morte_brl: Decimal = Field(..., ge=0)
    capital_segurado_invalidez_brl: Optional[Decimal] = Field(None, ge=0)
    premio_brl: Decimal = Field(..., ge=0)


CoberturaDiscriminated = Annotated[
    Union[CoberturaMaterial, CoberturaRcfv, CoberturaVida, CoberturaSaude, CoberturaAcidentes],
    Field(discriminator="tipo"),
]


# ---- Bens segurados (Discriminated Union por `tipo`) ---------------------


class BemSeguradoVeiculo(BaseModel):
    """Veículo segurado — FK opcional para vehicles (reconciliação assíncrona D3)."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["veiculo"]
    placa: str = Field(..., pattern=r"^[A-Z]{3}\d[A-Z\d]\d{2}$")
    fipe_code: Optional[str] = Field(None, pattern=r"^[0-9\-]{4,20}$")
    marca: str = Field(..., min_length=2, max_length=60)
    modelo: str = Field(..., min_length=1, max_length=120)
    ano_modelo: int = Field(..., ge=1900, le=2100)
    veiculo_id: Optional[str] = Field(None, max_length=36)
    coberturas: list[CoberturaDiscriminated] = Field(default_factory=list)

    @field_validator("placa", mode="before")
    @classmethod
    def _normalize_placa(cls, v):
        if not isinstance(v, str):
            return v
        return v.upper().replace("-", "").replace(" ", "")


class BemSeguradoImovel(BaseModel):
    """Imóvel segurado — FK opcional para real_estate_assets (ADR-216)."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["imovel"]
    endereco: EnderecoStruct
    tipo_imovel: Literal["casa", "apartamento", "comercial"]
    imovel_id: Optional[str] = Field(None, max_length=36)
    coberturas: list[CoberturaDiscriminated] = Field(default_factory=list)


class BemSeguradoPessoa(BaseModel):
    """V2 — vida/saúde/acidentes. CPF mascarado em Python pós-LLM (LGPD ADR-231 D8)."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["pessoa"]
    pessoa_cpf_masked: Optional[str] = Field(
        None,
        pattern=r"^[\d\*]{3}\.[\d\*]{3}\.[\d\*]{3}-[\d\*]{2}$",
        description="Sempre None no payload LLM; Python mascara pós-extração.",
    )
    family_member_id: Optional[str] = Field(None, max_length=36)
    coberturas: list[CoberturaDiscriminated] = Field(default_factory=list)


BemSeguradoDiscriminated = Annotated[
    Union[BemSeguradoVeiculo, BemSeguradoImovel, BemSeguradoPessoa],
    Field(discriminator="tipo"),
]


# ===========================================================================
# ApolicePayload — top-level (ADR-238 D2: top-level lenient, sub-models strict)
# ===========================================================================


class ApolicePayload(BaseModel):
    """Apólice polimórfica (top-level lenient ADR-238 D2; sub-models strict)."""

    model_config = ConfigDict(extra="allow")

    apolice_numero: str = Field(..., min_length=1, max_length=40)
    seguradora: str = Field(
        ...,
        min_length=2,
        max_length=60,
        description="Code canônico de institution_catalog (porto, tokiomarine, ...).",
    )
    vigencia_inicio: date
    vigencia_fim: date
    classe_bonus: Optional[int] = Field(None, ge=0, le=10)
    congenere_anterior: Optional[CongenereRef] = None
    premio_total_brl: Decimal = Field(..., ge=0)
    forma_pagamento: Literal["a_vista", "cartao", "boleto", "debito"]
    pagador_cpf_masked: Optional[str] = Field(
        None,
        pattern=r"^[\d\*]{3}\.[\d\*]{3}\.[\d\*]{3}-[\d\*]{2}$",
        description="Sempre None no payload LLM; Python mascara pós-extração (LGPD).",
    )
    pagador_family_member_id: Optional[str] = Field(None, max_length=36)
    segurado_cpf_masked: Optional[str] = Field(
        None,
        pattern=r"^[\d\*]{3}\.[\d\*]{3}\.[\d\*]{3}-[\d\*]{2}$",
        description="Sempre None no payload LLM; Python mascara pós-extração (LGPD).",
    )
    segurado_family_member_id: Optional[str] = Field(None, max_length=36)
    corretor: CorretorRef
    bens_segurados: list[BemSeguradoDiscriminated] = Field(..., min_length=1)
    sinistro_indenizacao_recebida_brl: Optional[Decimal] = Field(
        None,
        ge=0,
        description=(
            "Placeholder V1 (sempre None) — evita migration breaking quando ADR-238 "
            "integrar IR sobre indenização recebida. NÃO popular em L1/L2."
        ),
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    needs_review: bool = Field(default=False)
    prompt_version: str = Field(default=PROMPT_VERSION)
    cascade_triggered: bool = Field(
        default=False,
        description=(
            "True quando cascata Haiku→Sonnet foi disparada (combinada ou "
            "confidence baixo). Pipeline registra para telemetria sem PII."
        ),
    )
    notas: Optional[str] = Field(None, max_length=500)
