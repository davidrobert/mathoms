"""Schema estruturado de Informe de Rendimentos de Imobiliária — Onda 0.5 (ADR-216)."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

PROMPT_VERSION = "informe-aluguel-v1.1.0"


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
    locatario_cpf_cnpj: Optional[str] = Field(
        None,
        description=(
            "CPF ou CNPJ do locatário (anonimizar em logs — PII). "
            "Quando CNPJ, pagador é PJ e tipicamente há IR retido."
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


class InformeAluguelExtract(_SubModel):
    """Top-level — informe anual da imobiliária para um locador no ano de referência."""

    imobiliaria_cnpj: str = Field(
        ...,
        pattern=r"^\d{14}$",
        description="CNPJ da imobiliária (somente dígitos, 14 chars). Coercionar de '12.345.678/0001-90' no extractor.",
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
    locador_cpf: Optional[str] = Field(
        None,
        pattern=r"^\d{11}$",
        description=(
            "CPF do locador (11 dígitos sem máscara). PII — usado pelo orquestrador para matching com "
            "``member_key``, não persistido no payload final."
        ),
    )
    membro_key: Optional[str] = Field(
        None,
        description=(
            "Chave do membro da família a quem pertence o informe. "
            "Populada pelo orquestrador a partir de ``locador_cpf``, não pelo LLM."
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
