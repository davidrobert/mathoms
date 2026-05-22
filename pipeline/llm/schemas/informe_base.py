"""Schema-base polimórfico de Informes de Rendimentos anuais — A17 (ADR-238 D2); L1 aceita só previdencia_privada."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from pipeline.llm.schemas.informe_pj import InformeFinanceiroPJPayload
from pipeline.llm.schemas.informe_previdencia import InformePrevidenciaPayload

PROMPT_VERSION_FAMILY = "informe-anual"


class InformeRendimentosBase(BaseModel):
    """Top-level lenient com discriminator ``tipo_informe`` (ADR-238 D2); wire monetário ADR-090."""

    model_config = ConfigDict(extra="allow")

    ano_base: int = Field(
        ...,
        ge=2000,
        le=2100,
        description="Ano calendário coberto pelo informe (geralmente o ano-base do IRPF).",
    )
    tipo_informe: Literal["previdencia_privada", "financeiro_pj"] = Field(
        ...,
        description=(
            "Tipo canônico do informe. A17 L1 entregou ``previdencia_privada``; "
            "L2 adiciona ``financeiro_pj`` (Comprovante Lei 9.249/95); L3-L4 "
            "expandem com ``financeiro_pf`` e ``proventos_acoes``."
        ),
    )
    fonte_pagadora_cnpj: str = Field(
        ...,
        pattern=r"^\d{14}$",
        description="CNPJ do emissor do informe (14 dígitos sem máscara).",
    )
    fonte_pagadora_nome: str = Field(
        ...,
        min_length=2,
        description="Razão social do emissor (BrasilPrev, Itaú, XP, etc).",
    )
    titular_cpf_masked: Optional[str] = Field(
        None,
        pattern=r"^[\d\*]{3}\.[\d\*]{3}\.[\d\*]{3}-[\d\*]{2}$",
        description=(
            "CPF do titular com máscara parcial (ex.: ``***.456.789-**``). "
            "Usado para matching com ``family_members`` (ADR-127). Não persistir "
            "CPF completo no payload (LGPD)."
        ),
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Confiança da extração LLM. < 0.7 → ``needs_review=True`` automático "
            "no orquestrador. 1.0 = layout padrão sem ambiguidade."
        ),
    )
    source_artifact_id: Optional[str] = Field(
        None,
        description=(
            "FK do row em ``pipeline_artifacts`` do E0 (upload original). "
            "Permite rastrear informe → PDF original. None quando a extração "
            "vem de teste/golden sintético."
        ),
    )
    source_priority: int = Field(
        default=1,
        ge=1,
        le=3,
        description=(
            "Precedência D4: ``1`` (default) — informe é fonte primária "
            "(fail-safe: world sem E1.6 usa informe); ``2`` — orquestrador "
            "promoveu quando descobriu E1.6 do ano presente (declaração vence); "
            "``3`` reservado para override manual do usuário pós-divergência. "
            "Default falha aberta, não silenciosa."
        ),
    )
    prompt_version: str = Field(
        ...,
        min_length=1,
        description=(
            "Versão do prompt LLM que produziu o output (ex.: ``informe-prev-v1.0.0``). "
            "Usado para invalidação de cache idempotente (ADR-144)."
        ),
    )
    needs_review: bool = Field(
        default=False,
        description=(
            "True quando ``confidence < 0.7``, conflito de dedupe, ou campo obrigatório "
            "ausente. UI badge ``Revisar`` aparece em S8 ou no upload."
        ),
    )

    # Polimorfismo: exatamente um dos sub-payloads abaixo populado conforme
    # ``tipo_informe``. P1 só carrega ``previdencia``; L2-L4 adicionam campos
    # ``financeiro_pj``, ``financeiro_pf``, ``proventos``, ``aluguel``.
    previdencia: Optional[InformePrevidenciaPayload] = Field(
        None,
        description="Payload populado quando ``tipo_informe='previdencia_privada'``.",
    )
    financeiro_pj: Optional[InformeFinanceiroPJPayload] = Field(
        None,
        description="Payload populado quando ``tipo_informe='financeiro_pj'`` (L2).",
    )
