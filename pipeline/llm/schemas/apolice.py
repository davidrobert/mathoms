"""Schema apólice de seguro polimórfica (Discriminated Union 2 níveis) — A18 L2 P1 (ADR-239 D2)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

# Bump quando alterar prompt ``apolice`` de modo que afete output (ADR-144 cache).
# v1.2.0 — A33.l8 (ADR-137): bump pareado com o prompt (tabela de seguradoras
# sai do system prompt; user prompt ganha `{seguradoras_catalog}` injetado).
# Schema em si não mudou.
# v1.1.1 — coerção explícita string→date/Decimal pós-strip. ``model_validator(mode="before")``
# v1.1.0 quebra a coerção JSON-nativa do Pydantic strict mode (Instructor TOOLS path):
# antes do v1.1.0, ``model_validate_json(strict=True)`` aceitava ``"2026-04-05"`` para
# ``date`` e ``"1500.00"`` para ``Decimal``; depois, Pydantic re-valida o dict retornado
# pelo model_validator em modo Python strict e rejeita strings (``type=date_type``,
# ``type=is_instance_of``). Incidente prod 2026-05-22: ~28 validation errors por apólice
# combinada multi-bem (1 erro por campo Decimal/date). Fix: BeforeValidator por campo
# coage tipos antes do strict check; strip continua atacando aspas spurious do Haiku.
# Semver puro pós-A20.l12 (errata ADR-233 §Migration) — era "apolice-v1.1.1".
PROMPT_VERSION = "1.2.0"


def _strip_spurious_quotes(value):
    """LLM Haiku às vezes vaza aspas dos exemplos do prompt como notação visual,
    gerando ``'"4509.98"'`` (string com aspas literais). Decimal/Literal/date
    falham determinístico. Strip cobre aspas duplas e simples nas pontas; cascade
    recursivo em dict/list para sub-models (BemSegurado*, Cobertura*)."""
    if isinstance(value, str):
        stripped = value.strip()
        if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in ('"', "'"):
            return stripped[1:-1]
        return value
    if isinstance(value, dict):
        return {k: _strip_spurious_quotes(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip_spurious_quotes(item) for item in value]
    return value


# ``model_validator(mode="before")`` (strip) faz Pydantic re-validar em Python strict — strings
# ISO/decimal são rejeitadas. Coerção explícita restaura aceitação sem renunciar a strict mode.


def _coerce_date(value):
    """ISO string → ``date``; passthrough caso contrário."""
    if isinstance(value, str):
        return date.fromisoformat(value.strip())
    return value


def _coerce_decimal(value):
    """String/int/float → ``Decimal``; None/Decimal passthrough (Float via str — ADR-090)."""
    if value is None or isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        try:
            return Decimal(value.strip())
        except InvalidOperation:
            return value  # deixa Pydantic raise com mensagem específica
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return value


# Aliases reutilizáveis — aplicam ``_coerce_*`` antes da validação strict do Pydantic.
ApoliceDate = Annotated[date, BeforeValidator(_coerce_date)]
ApoliceMoney = Annotated[Decimal, BeforeValidator(_coerce_decimal)]


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
    percentual: ApoliceMoney = Field(..., ge=0, le=100)


# ---- Coberturas (Discriminated Union por `tipo`) -------------------------


class CoberturaMaterial(BaseModel):
    """Cobertura material (auto: colisão/incêndio/roubo; imóvel: incêndio/vendaval/raio)."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["material"]
    nome: str = Field(..., min_length=2, max_length=120)
    ramo_susep: Optional[str] = Field(None, max_length=20)
    lmi_modo: Literal["valor_fixo", "fipe_percentual", "primeiro_risco_absoluto"]
    lmi_brl: Optional[ApoliceMoney] = Field(None, ge=0)
    lmi_fipe_percentual: Optional[ApoliceMoney] = Field(None, ge=0, le=2)
    franquia_brl: Optional[ApoliceMoney] = Field(None, ge=0)
    premio_brl: ApoliceMoney = Field(..., ge=0)


class CoberturaRcfv(BaseModel):
    """Responsabilidade Civil Facultativa de Veículo (danos a terceiros)."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["rcfv"]
    nome: Literal["danos_materiais", "danos_corporais", "danos_morais"]
    lmi_brl: ApoliceMoney = Field(..., ge=0)
    premio_brl: ApoliceMoney = Field(..., ge=0)


class CoberturaVida(BaseModel):
    """V2 — placeholder em V1 (schema antecipa para evitar migration breaking)."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["vida"]
    capital_segurado_brl: ApoliceMoney = Field(..., ge=0)
    beneficiarios: list[BeneficiarioRef] = Field(default_factory=list)
    premio_brl: ApoliceMoney = Field(..., ge=0)


class CoberturaSaude(BaseModel):
    """V2 — placeholder em V1."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["saude"]
    rede_credenciada: Optional[str] = Field(None, max_length=200)
    capital_segurado_brl: Optional[ApoliceMoney] = Field(None, ge=0)
    premio_brl: ApoliceMoney = Field(..., ge=0)


class CoberturaAcidentes(BaseModel):
    """V2 — placeholder em V1."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["acidentes"]
    capital_segurado_morte_brl: ApoliceMoney = Field(..., ge=0)
    capital_segurado_invalidez_brl: Optional[ApoliceMoney] = Field(None, ge=0)
    premio_brl: ApoliceMoney = Field(..., ge=0)


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

    @model_validator(mode="before")
    @classmethod
    def _strip_llm_quotes(cls, data):
        """Strip aspas spurious do Haiku (vira a coerção JSON-nativa do Pydantic — ver módulo)."""
        if isinstance(data, dict):
            return {k: _strip_spurious_quotes(v) for k, v in data.items()}
        return data

    apolice_numero: str = Field(..., min_length=1, max_length=40)
    seguradora: str = Field(
        ...,
        min_length=2,
        max_length=60,
        description="Code canônico de institution_catalog (porto, tokiomarine, ...).",
    )
    vigencia_inicio: ApoliceDate
    vigencia_fim: ApoliceDate
    classe_bonus: Optional[int] = Field(None, ge=0, le=10)
    congenere_anterior: Optional[CongenereRef] = None
    premio_total_brl: ApoliceMoney = Field(..., ge=0)
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
    sinistro_indenizacao_recebida_brl: Optional[ApoliceMoney] = Field(
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
