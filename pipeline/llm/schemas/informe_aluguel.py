"""Schema estruturado de Informe de Rendimentos de Imobiliária — Onda 0.5 (ADR-216)."""

from __future__ import annotations

import re
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# 2.0.0: ADR-259 §2 / A20.l15 (LGPD) — LLM não emite CPF (locador_cpf →
#   locador_cpf_present; locatario_cpf_cnpj → locatario_cnpj, CNPJ é público);
#   formato migra para semver puro (errata ADR-233 §Migration).
PROMPT_VERSION = "2.0.0"

_NON_DIGITS = re.compile(r"\D")


def _normalize_pii_digits(v, *, expected_len: int) -> Optional[str]:
    """Identificador fiscal no boundary LLM: strip de máscara; ilegível/sentinel → None (ADR-288)."""
    # Sentinels (<UNKNOWN>, N/A…) e truncados não somam expected_len dígitos e
    # degradam para None — documento sobrevive em vez de queimar retries (ADR-238).
    if v is None:
        return None
    digits = _NON_DIGITS.sub("", v if isinstance(v, str) else str(v))
    return digits if len(digits) == expected_len else None


def _coerce_decimal(v):
    """Coerção monetária no boundary do LLM (ADR-090): aceita ``float`` aqui porque JSON não tem Decimal nativo e este validator é o call-site canônico para ``Decimal(str(v))`` — o float chega literal do parser, sem aritmética intermediária."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, str, float)):
        return Decimal(str(v))
    raise TypeError(f"informe_aluguel: não consigo coerce {type(v).__name__}={v!r} para Decimal")


class IndiceReajuste(str, Enum):
    """Índices de reajuste contratual típicos no mercado de aluguel BR."""

    igpm = "IGPM"
    ipca = "IPCA"
    ipc_fipe = "IPC-FIPE"
    inpc = "INPC"
    sem_reajuste = "sem_reajuste"
    nao_informado = "nao_informado"


class _SubModel(BaseModel):
    """Sub-schemas: ``additionalProperties: false`` por design."""

    model_config = ConfigDict(extra="forbid")


class InformeAluguelImovel(_SubModel):
    """Linha por imóvel administrado pela imobiliária — valores anuais."""

    endereco: str = Field(..., min_length=4, description="Endereço completo do imóvel.")
    iptu_municipal: Optional[str] = Field(
        None,
        description="Número da inscrição imobiliária/IPTU municipal (identificador único quando disponível).",
    )
    # ADR-259 §2 (A20.l15): CPF de locatário é PII de terceiro — nunca emitido.
    # CNPJ é registro público (exceção ADR-259) e carrega o sinal fiscal
    # relevante: pagador PJ tipicamente tem IR retido na fonte.
    locatario_cnpj: Optional[str] = Field(
        None,
        description=(
            "CNPJ do locatário quando o pagador é PJ (14 dígitos; máscara normalizada). "
            "Se o locatário for PF, NÃO transcreva o CPF — deixe None."
        ),
    )
    aluguel_bruto_anual: Decimal = Field(
        ..., description="Aluguel bruto recebido no período (somatório anual)."
    )
    taxa_administracao_anual: Decimal = Field(
        ..., description="Total pago à imobiliária como taxa de administração no período."
    )
    ir_retido_anual: Decimal = Field(
        default=Decimal("0"),
        description=(
            "IR retido na fonte pelo locatário PJ (somatório). PF→PF residencial não retém — default 0."
        ),
    )
    iptu_anual_pago: Optional[Decimal] = Field(
        None,
        description=(
            "IPTU pago pela imobiliária no período (descontado do aluguel). "
            "None quando o locador paga diretamente ou imobiliária não administra IPTU."
        ),
    )
    condominio_anual_pago: Optional[Decimal] = Field(
        None,
        description=(
            "Condomínio pago pela imobiliária no período. "
            "None quando o locador paga diretamente ou imobiliária não administra."
        ),
    )
    aluguel_liquido_anual: Decimal = Field(
        ...,
        description=(
            "Aluguel líquido efetivamente transferido ao locador no período "
            "(bruto − taxa adm − IR retido − IPTU descontado − condomínio descontado)."
        ),
    )
    meses_locado_no_periodo: int = Field(
        ...,
        ge=0,
        le=12,
        description="Número de meses com contrato ativo no período. Vacância empírica = (12 − meses_locado) / 12.",
    )
    mes_inicial: Optional[int] = Field(
        None,
        ge=1,
        le=12,
        description="Mês de início da locação no período (1-12). None se contrato pré-existente cobriu todo o período.",
    )
    indice_reajuste: IndiceReajuste = Field(
        default=IndiceReajuste.nao_informado,
        description="Índice de reajuste do contrato — extraído quando informado no documento.",
    )
    data_ultimo_reajuste: Optional[str] = Field(
        None,
        pattern=r"^\d{4}-\d{2}(-\d{2})?$",
        description="Data do último reajuste contratual aplicado (YYYY-MM ou YYYY-MM-DD).",
    )
    notas: Optional[str] = Field(
        None,
        description="Observações livres extraídas do informe (ex.: descontos, ressarcimentos).",
    )

    @field_validator(
        "aluguel_bruto_anual",
        "taxa_administracao_anual",
        "ir_retido_anual",
        "iptu_anual_pago",
        "condominio_anual_pago",
        "aluguel_liquido_anual",
        mode="before",
    )
    @classmethod
    def _decimal_money(cls, v):
        return _coerce_decimal(v)

    @field_validator("locatario_cnpj", mode="before")
    @classmethod
    def _normalize_locatario_cnpj(cls, v):
        return _normalize_pii_digits(v, expected_len=14)


class InformeAluguelExtract(_SubModel):
    """Top-level — informe anual da imobiliária para um locador no ano de referência."""

    imobiliaria_cnpj: Optional[str] = Field(
        None,
        pattern=r"^\d{14}$",
        description=(
            "CNPJ da imobiliária (somente dígitos, 14 chars) ou None quando ilegível/ausente "
            "no documento. Máscara é normalizada deterministicamente no validator (ADR-288)."
        ),
    )
    imobiliaria_nome: str = Field(
        ..., min_length=2, description="Razão social ou nome fantasia da imobiliária."
    )
    ano_referencia: int = Field(
        ...,
        ge=2000,
        le=2100,
        description="Ano calendário coberto pelo informe (geralmente o ano-base do IRPF do contribuinte).",
    )
    # ADR-259 §2 (A20.l15): o VALOR do CPF do locador nunca sai do LLM nem
    # persiste no artifact. O matching com membro é determinístico: regex
    # sobre o TEXTO do documento × CPFs (Fernet) do config de membros.
    locador_cpf_present: bool = Field(
        False,
        description=("True quando o informe contém o CPF do locador — NUNCA transcreva o número."),
    )
    membro_key: Optional[str] = Field(
        None,
        description=(
            "Chave do membro da família a quem pertence o informe. "
            "Populada pelo matcher determinístico do stage (regex doc × config), não pelo LLM."
        ),
    )
    imoveis: list[InformeAluguelImovel] = Field(
        default_factory=list,
        description="Lista de imóveis administrados pela imobiliária no período.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Confiança da extração. 1.0 = informe estruturado claro; "
            "<0.7 = ambíguo (campos faltantes ou inconsistentes — revisão humana recomendada)."
        ),
    )
    notes: Optional[str] = Field(
        None,
        description="Observações gerais do extractor (ambiguidades, valores conflitantes).",
    )
    prompt_version: str = Field(
        default=PROMPT_VERSION,
        description="Versão do prompt que produziu o output — usado para invalidação de cache (ADR-157 sub-decisão 7).",
    )

    @field_validator("imobiliaria_cnpj", mode="before")
    @classmethod
    def _normalize_cnpj(cls, v):
        return _normalize_pii_digits(v, expected_len=14)
