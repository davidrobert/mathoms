"""Schema do Certificado de Registro e Licenciamento de Veículo eletrônico (CRLV-e) — A18 L1 P2 (ADR-239)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Bump quando alterar prompt ``crlv`` de modo que afete output (ADR-144 cache).
# Semver puro pós-A20.l12 (errata ADR-233 §Migration) — era "crlv-v1.0.0".
PROMPT_VERSION = "1.0.0"


# Combustíveis canônicos do DETRAN — lista core. Outros aceitos via str
# livre quando o DETRAN trouxer variação regional (ex.: "ÁLCOOL/GASOLINA").
COMBUSTIVEIS_CANONICOS = (
    "gasolina",
    "alcool",
    "flex",
    "diesel",
    "gnv",
    "eletrico",
    "hibrido",
)

CATEGORIAS_CANONICAS = ("particular", "comercial", "aluguel", "oficial", "diplomatico")


class CRLVPayload(BaseModel):
    """Payload strict do CRLV-e (ADR-239 D1; Pydantic boundary regex completo)."""

    model_config = ConfigDict(extra="forbid")

    placa: str = Field(
        ...,
        pattern=r"^[A-Z]{3}\d[A-Z\d]\d{2}$",
        description=(
            "Placa Mercosul (ABC1D23) ou legado (ABC1234), upper sem hífen. "
            "Normalização (upper + strip hífen/espaço) feita em ``mode='before'`` "
            "antes da validação do pattern."
        ),
    )
    renavam: str = Field(
        ...,
        pattern=r"^[0-9]{9,11}$",
        description="RENAVAM (9-11 dígitos). Validação completa cf. ADR-239 D1 CHECK BD.",
    )
    marca: str = Field(..., min_length=2, max_length=60)
    modelo: str = Field(..., min_length=1, max_length=120)
    ano_modelo: int = Field(..., ge=1900, le=2100)
    ano_fabricacao: int = Field(..., ge=1900, le=2100)
    cor: Optional[str] = Field(None, max_length=30)
    combustivel: Optional[str] = Field(
        None,
        max_length=20,
        description="Lowercase canonical quando possível; aceita string livre se DETRAN traz variação.",
    )
    exercicio: int = Field(
        ...,
        ge=2000,
        le=2100,
        description="Ano-exercício do licenciamento (geralmente ano corrente do CRLV).",
    )
    categoria: str = Field(..., min_length=2, max_length=40)
    proprietario_cpf_masked: Optional[str] = Field(
        None,
        pattern=r"^[\d\*]{3}\.[\d\*]{3}\.[\d\*]{3}-[\d\*]{2}$",
        description=(
            "CPF do proprietário com máscara parcial (ex.: ``***.456.789-**``). "
            "Mascaramento feito em Python pós-LLM — instrução SYSTEM_PROMPT força null."
        ),
    )
    proprietario_nome: Optional[str] = Field(None, max_length=120)
    municipio_emplacamento: Optional[str] = Field(None, max_length=80)
    uf_emplacamento: Optional[str] = Field(
        None,
        pattern=r"^[A-Z]{2}$",
        description="UF emplacamento (2 letras maiúsculas).",
    )
    data_emissao: Optional[date] = Field(
        None,
        description="Data de emissão do CRLV-e. ISO 8601 (YYYY-MM-DD); None se ausente do documento.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Confiança da extração. < 0.7 → ``needs_review=True`` automático no orquestrador."
        ),
    )
    needs_review: bool = Field(
        default=False,
        description="True quando confidence < 0.7 ou colisão placa↔renavam detectada no upsert.",
    )
    prompt_version: str = Field(
        default=PROMPT_VERSION,
        description="Versão do prompt LLM (gate dev/check_prompt_version_bumped.py).",
    )
    notas: Optional[str] = Field(None, max_length=500)

    @field_validator("placa", mode="before")
    @classmethod
    def _normalize_placa(cls, v):
        """Upper + strip de hífens/espaços ANTES do pattern (Pydantic V2)."""
        if not isinstance(v, str):
            return v
        return v.upper().replace("-", "").replace(" ", "")
