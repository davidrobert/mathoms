"""E1.6 (`extract_irpf_full`) — schema completo de declaração IRPF (ADR-157)."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Versão do prompt — incluída no payload por sub-decisão #7 da ADR-157.
# Bump quando alterar o prompt ``e16_irpf_full`` de modo que afete output.
# v1.1.0 (ADR-215): + extração de `contribuinte.endereco` (signal pré-seleção residência).
# v1.1.1 (ADR-268): rejeita Contribuinte.nome com sufixo PJ (LTDA/S.A./EIRELI...).
# v1.1.2 (ADR-268 rev): sufixo PJ vira sinal needs_review (guardrail pós-LLM
#   ``detect_pj_suffix``), não validator de schema — raise brickava read de E5.
# Semver puro pós-A20.l12 (errata ADR-233 §Migration) — era "e16-v1.1.2".
PROMPT_VERSION = "1.1.2"

# ADR-268 (rev) — detecção PF vs PJ no Contribuinte.nome. IRPF é declaração de
# PF; nome com sufixo de personificação jurídica (LTDA, S.A., EIRELI, ME, EPP,
# MEI, SOCIEDADE, ASSOCIAÇÃO, FUNDAÇÃO, COOPERATIVA) indica documento PJ
# mal-classificado em E0. NÃO é validator de schema que raise: documento
# genuinamente PJ não é erro de extração do LLM — raise dispararia retry storm
# no write (anti-padrão [[ADR-238]]) e brickaria a desserialização de artifacts
# persistidos no read (E5). Usado como guardrail determinístico pós-extração.
_PJ_SUFFIX_RE = re.compile(
    r"\b(?:LTDA|S\.?\s*A\.?|EIRELI|MEI|ME|EPP|SOCIEDADE|ASSOCIA[CÇ][AÃ]O|FUNDA[CÇ][AÃ]O|COOPERATIVA)\b",
    re.IGNORECASE,
)


def detect_pj_suffix(nome: str | None) -> str | None:
    """Sufixo PJ casado (ex.: ``'LTDA'``) ou ``None`` — guardrail ADR-268
    consumido por E1.6 (flag ``needs_review``) e read boundary de E5.
    """
    if not nome:
        return None
    m = _PJ_SUFFIX_RE.search(nome)
    return m.group() if m else None


# =============================================================================
# Coerção monetária (ADR-090)
# =============================================================================


def _coerce_decimal(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, float):
        raise TypeError(
            f"E1.6: float é proibido em campo monetário (ADR-090) — "
            f"recebido {v!r}; converta via Decimal(str(v)) no call-site"
        )
    if isinstance(v, (int, str)):
        return Decimal(str(v))
    raise TypeError(f"E1.6: não consigo coerce {type(v).__name__}={v!r} para Decimal")


# =============================================================================
# Enums por contexto (G2 dealbreaker — codigo_rfb solto vira string-matching)
# =============================================================================


class ModeloDeclaracao(str, Enum):
    completo = "completo"
    simplificado = "simplificado"


class NaturezaContribuinte(str, Enum):
    titular = "titular"
    dependente_titular = "dependente_titular"


class RelacaoDependente(str, Enum):
    """RFB instrução normativa lista 14 categorias canônicas."""

    conjuge_companheiro = "conjuge_companheiro"
    filho_filha = "filho_filha"
    enteado_enteada = "enteado_enteada"
    pai_mae = "pai_mae"
    avo = "avo"
    irmao_irma = "irmao_irma"
    bisavo = "bisavo"
    neto_neta = "neto_neta"
    bisneto_bisneta = "bisneto_bisneta"
    sogro_sogra = "sogro_sogra"
    menor_pobre = "menor_pobre"
    tutelado = "tutelado"
    incapaz = "incapaz"
    outro = "outro"


class CodigoRendimentoIsento(str, Enum):
    """Códigos RFB ficha de Rendimentos Isentos. Lista core; fallback ``99_outro``."""

    aposentadoria_pensao_65 = "10"
    aposentadoria_pensao_doenca_grave = "11"
    pensao_alimenticia_recebida = "12"
    bolsa_estudo = "13"
    fgts = "04"
    indenizacao_trabalho = "05"
    lucros_dividendos = "09"
    transferencia_doacao = "14"
    outro = "99_outro"


class CodigoRendimentoTribExclusiva(str, Enum):
    """Códigos RFB ficha de Tributação Exclusiva. Fallback ``99_outro``."""

    decimo_terceiro = "11"
    jcp = "10"
    ganho_capital = "06"
    rendimentos_aplicacoes_financeiras = "12"
    outro = "99_outro"


class CodigoPagamentoDedutivel(str, Enum):
    """Códigos RFB ficha de Pagamentos Efetuados. Tetos diferem por código (G0)."""

    saude = "10"
    educacao = "11"
    pensao_alimenticia_judicial = "30"
    pensao_alimenticia_acordo_extrajudicial = "31"
    pensao_alimenticia_escritura = "33"
    previdencia_oficial = "35"
    pgbl = "36"
    contribuicao_funpresp = "37"
    contribuicao_entidade_filantropica = "40"
    contribuicao_inss_empregado = "50"
    livro_caixa = "60"
    outro = "99_outro"


# =============================================================================
# Bases — sub-models strict (ADR-157 sub-decisão 4)
# =============================================================================


class _SubModel(BaseModel):
    """Sub-schemas: ``additionalProperties: false`` por design (G2)."""

    model_config = ConfigDict(extra="forbid")


class _TopModel(BaseModel):
    """Top-level: ``additionalProperties: true`` com WARNING em telemetry."""

    model_config = ConfigDict(extra="allow")


# =============================================================================
# Sub-schemas
# =============================================================================


_CPF_MASKED_PATTERN = r"^\*{3}\.\*{3}\.\*{3}-\d{2}$"
# CNPJ é público (não-PII) — aceita real ou parcialmente mascarado.
_CNPJ_PATTERN = r"^[\d*]{2}\.[\d*]{3}\.[\d*]{3}/[\d*]{4}-[\d*]{2}$"
# Beneficiário PJ ou PF (médico/hospital/escola): aceita CPF mascarado ou CNPJ.
_CPF_OR_CNPJ_PATTERN = (
    r"^(?:\*{3}\.\*{3}\.\*{3}-\d{2}|[\d*]{2}\.[\d*]{3}\.[\d*]{3}/[\d*]{4}-[\d*]{2})$"
)


class Contribuinte(_SubModel):
    cpf_masked: str = Field(..., pattern=_CPF_MASKED_PATTERN)
    nome: str = Field(..., min_length=1)
    ano_base: int = Field(..., ge=2000, le=2100)
    exercicio: int = Field(..., ge=2000, le=2100)
    modelo: ModeloDeclaracao
    natureza: NaturezaContribuinte
    # ADR-215: endereço da seção "Dados do Contribuinte" — signal para
    # pré-seleção heurística de residência principal. NÃO é prova de
    # residência (pode ser PJ, casa dos pais, corretora). Lazy fill:
    # IRPFs anteriores ficam None até re-rodar E1.6 com prompt v1.1.0+.
    endereco: Optional[str] = Field(default=None, min_length=1)


class FontePagadoraPJ(_SubModel):
    cnpj: str = Field(..., pattern=_CNPJ_PATTERN)
    nome: str = Field(..., min_length=1)
    rendimentos_tributaveis_brl: Decimal
    contrib_previdenciaria_brl: Decimal
    ir_retido_brl: Decimal
    decimo_terceiro_bruto_brl: Optional[Decimal] = None
    decimo_terceiro_ir_retido_brl: Optional[Decimal] = None

    @field_validator(
        "rendimentos_tributaveis_brl",
        "contrib_previdenciaria_brl",
        "ir_retido_brl",
        "decimo_terceiro_bruto_brl",
        "decimo_terceiro_ir_retido_brl",
        mode="before",
    )
    @classmethod
    def _to_decimal(cls, v):
        return _coerce_decimal(v)


class FontePagadoraPF(_SubModel):
    """Carnê-leão (PF→PF). Bucket canônico de aluguel recebido (G0)."""

    pagador_cpf_masked: Optional[str] = Field(None, pattern=_CPF_MASKED_PATTERN)
    pagador_nome: str = Field(..., min_length=1)
    valor_brl: Decimal
    ir_recolhido_brl: Decimal

    @field_validator("valor_brl", "ir_recolhido_brl", mode="before")
    @classmethod
    def _to_decimal(cls, v):
        return _coerce_decimal(v)


class RendimentoExterior(_SubModel):
    pais: str = Field(..., min_length=2)
    pagador: str = Field(..., min_length=1)
    valor_origem: Decimal
    moeda_origem: str = Field(..., min_length=3, max_length=3)
    taxa_conversao: Decimal
    data_conversao: date
    valor_brl: Decimal

    @field_validator("valor_origem", "taxa_conversao", "valor_brl", mode="before")
    @classmethod
    def _to_decimal(cls, v):
        return _coerce_decimal(v)


class RendimentoIsento(_SubModel):
    codigo_rfb: CodigoRendimentoIsento
    descricao: str = Field(..., min_length=1)
    valor_brl: Decimal
    fonte: Optional[str] = None

    @field_validator("valor_brl", mode="before")
    @classmethod
    def _to_decimal(cls, v):
        return _coerce_decimal(v)


class RendimentoTribExclusiva(_SubModel):
    codigo_rfb: CodigoRendimentoTribExclusiva
    descricao: str = Field(..., min_length=1)
    valor_brl: Decimal

    @field_validator("valor_brl", mode="before")
    @classmethod
    def _to_decimal(cls, v):
        return _coerce_decimal(v)


class PagamentoDedutivel(_SubModel):
    codigo_rfb: CodigoPagamentoDedutivel
    beneficiario_nome: str = Field(..., min_length=1)
    beneficiario_cpf_cnpj_masked: Optional[str] = Field(None, pattern=_CPF_OR_CNPJ_PATTERN)
    valor_pago_brl: Decimal
    valor_dedutivel_brl: Decimal
    teto_aplicado: bool = False

    @field_validator("valor_pago_brl", "valor_dedutivel_brl", mode="before")
    @classmethod
    def _to_decimal(cls, v):
        return _coerce_decimal(v)


class DividaOnusReal(_SubModel):
    codigo_rfb: str = Field(..., min_length=1)
    discriminacao: str = Field(..., min_length=1)
    valor_inicial_brl: Decimal
    valor_final_brl: Decimal

    @field_validator("valor_inicial_brl", "valor_final_brl", mode="before")
    @classmethod
    def _to_decimal(cls, v):
        return _coerce_decimal(v)


class ImpostoApurado(_SubModel):
    """Valores absolutos da ficha "Resumo da Declaração". Alíquotas derivadas em
    `IRPFAnalyzer` em pure Python — LLM não calcula proporção (ADR-157 sub-decisão 2)."""

    base_calculo_brl: Decimal
    ir_devido_brl: Decimal
    deducoes_totais_brl: Decimal
    ir_pago_brl: Decimal
    ir_a_pagar_brl: Optional[Decimal] = None
    ir_a_restituir_brl: Optional[Decimal] = None

    @field_validator(
        "base_calculo_brl",
        "ir_devido_brl",
        "deducoes_totais_brl",
        "ir_pago_brl",
        "ir_a_pagar_brl",
        "ir_a_restituir_brl",
        mode="before",
    )
    @classmethod
    def _to_decimal(cls, v):
        return _coerce_decimal(v)


class Dependente(_SubModel):
    cpf_masked: Optional[str] = Field(None, pattern=_CPF_MASKED_PATTERN)
    nome: str = Field(..., min_length=1)
    relacao: RelacaoDependente
    data_nascimento: Optional[date] = None


class PatrimonialItem(_SubModel):
    """Bens & Direitos — paridade com E1.5 mas em ``Decimal`` (ADR-157 sub-decisão 10)."""

    codigo: str = Field(..., min_length=1)
    descricao: str = Field(..., min_length=1)
    categoria: str = Field(..., min_length=1)
    instituicao: Optional[str] = None
    valor_brl: Decimal
    membro_key: str = Field(..., min_length=1)
    ano: int = Field(..., ge=2000, le=2100)

    @field_validator("valor_brl", mode="before")
    @classmethod
    def _to_decimal(cls, v):
        return _coerce_decimal(v)


# =============================================================================
# Top-level — `additionalProperties: true` para sobreviver shape novo de PDF
# =============================================================================


class IRPFFullOutput(_TopModel):
    """Output completo de uma declaração IRPF (top-level lenient — ADR-157 sub-decisão 4)."""

    contribuinte: Contribuinte
    rendimentos_pj: list[FontePagadoraPJ] = Field(default_factory=list)
    rendimentos_pf: list[FontePagadoraPF] = Field(default_factory=list)
    rendimentos_exterior: list[RendimentoExterior] = Field(default_factory=list)
    rendimentos_isentos: list[RendimentoIsento] = Field(default_factory=list)
    rendimentos_tributacao_exclusiva: list[RendimentoTribExclusiva] = Field(default_factory=list)
    pagamentos_efetuados: list[PagamentoDedutivel] = Field(default_factory=list)
    dividas_onus: list[DividaOnusReal] = Field(default_factory=list)
    imposto_apurado: ImpostoApurado
    dependentes: list[Dependente] = Field(default_factory=list)
    bens_direitos: list[PatrimonialItem] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: Optional[str] = None
    prompt_version: str = PROMPT_VERSION


__all__ = [
    "PROMPT_VERSION",
    "detect_pj_suffix",
    "ModeloDeclaracao",
    "NaturezaContribuinte",
    "RelacaoDependente",
    "CodigoRendimentoIsento",
    "CodigoRendimentoTribExclusiva",
    "CodigoPagamentoDedutivel",
    "Contribuinte",
    "FontePagadoraPJ",
    "FontePagadoraPF",
    "RendimentoExterior",
    "RendimentoIsento",
    "RendimentoTribExclusiva",
    "PagamentoDedutivel",
    "DividaOnusReal",
    "ImpostoApurado",
    "Dependente",
    "PatrimonialItem",
    "IRPFFullOutput",
]
