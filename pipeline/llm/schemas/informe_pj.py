"""Sub-schema Pydantic do Informe Financeiro PJ (Comprovante Lei 9.249/95) — A17 L2 (ADR-238 D2)."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _coerce_decimal(v):
    """Coerção monetária no boundary do LLM (ADR-090)."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, str, float)):
        return Decimal(str(v))
    raise TypeError(f"informe_pj: não consigo coerce {type(v).__name__}={v!r} para Decimal")


class RegimeTributarioPJ(str, Enum):
    """Regime do beneficiário (V1: SN ou LP; LR fora de escopo per ADR-238)."""

    simples_nacional = "simples_nacional"
    lucro_presumido = "lucro_presumido"


class InformeFinanceiroPJPayload(BaseModel):
    """Payload strict de comprovante de rendimentos PJ — 1 pagador = 1 payload (ADR-238 D2)."""

    model_config = ConfigDict(extra="forbid")

    regime_tributario: RegimeTributarioPJ = Field(
        ...,
        description=(
            "Regime do beneficiário. V1 aceita `simples_nacional` e "
            "`lucro_presumido` apenas — Lucro Real fora de escopo "
            "(ADR-238 §Não-objetivos). Em Simples Nacional, CSLL/PIS/COFINS "
            "raramente são retidos (DAS unificada cobre); em Lucro "
            "Presumido, retenção 1% CSLL + 0,65% PIS + 3% COFINS é "
            "comum sobre serviços."
        ),
    )
    cnpj_pagador: str = Field(
        ...,
        pattern=r"^\d{14}$",
        description=(
            "CNPJ da fonte pagadora (14 dígitos sem máscara). Para "
            "adquirentes (Stone, Cielo, Rede), é o CNPJ da adquirente; "
            "para contratantes, é o CNPJ do cliente final."
        ),
    )
    nome_pagador: str = Field(
        ...,
        min_length=2,
        description="Razão social da fonte pagadora conforme literal no informe.",
    )
    cnpj_beneficiario: str = Field(
        ...,
        pattern=r"^\d{14}$",
        description=(
            "CNPJ da empresa do usuário (14 dígitos). Usado pelo "
            "orquestrador para matching com `business_profile` "
            "(workspaces.business_profile_json)."
        ),
    )
    periodo_inicio: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}$",
        description="Mês inicial do período coberto (YYYY-MM). Default em janeiro do ano-base.",
    )
    periodo_fim: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}$",
        description="Mês final do período coberto (YYYY-MM). Default em dezembro do ano-base.",
    )
    receita_bruta_anual: Decimal = Field(
        ...,
        description=(
            "Receita bruta no período coberto (somatório). Para "
            "adquirentes, é o TPV processado menos estornos; para "
            "contratantes, é o faturamento bruto antes de qualquer "
            "retenção. Compõe a base do IRPJ no Lucro Presumido (base "
            "8% para comércio, 32% para serviços, etc. — orquestrador "
            "aplica)."
        ),
    )
    estornos_anuais: Decimal = Field(
        default=Decimal("0"),
        description=(
            "Estornos (chargebacks, cancelamentos) deduzidos da receita "
            "bruta no período. Default `0`. Adquirentes destacam este "
            "valor; contratantes raramente."
        ),
    )
    irrf_anual: Decimal = Field(
        default=Decimal("0"),
        description=(
            "IRRF retido na fonte (somatório anual). Default `0`. "
            "Compensável no IRPJ via DARF. Pega-rato: Simples "
            "Nacional NÃO retém IRRF na maioria dos casos (CSPJ "
            "anexo III); LP serviços tem retenção 1,5% por contrato."
        ),
    )
    csll_anual: Decimal = Field(
        default=Decimal("0"),
        description=(
            "CSLL retida (somatório). Default `0`. Tipicamente 1% "
            "sobre serviços em Lucro Presumido; **não há retenção "
            "em Simples Nacional** (DAS unificada cobre)."
        ),
    )
    pis_anual: Decimal = Field(
        default=Decimal("0"),
        description=(
            "PIS retido (somatório). Default `0`. 0,65% típico em LP sobre serviços; SN não retém."
        ),
    )
    cofins_anual: Decimal = Field(
        default=Decimal("0"),
        description=(
            "COFINS retido (somatório). Default `0`. 3% típico em LP sobre serviços; SN não retém."
        ),
    )
    inss_anual: Decimal = Field(
        default=Decimal("0"),
        description=(
            "INSS retido (somatório). Default `0`. 11% sobre serviços "
            "prestados quando exigido (cessão de mão de obra, "
            "construção civil) — independe do regime."
        ),
    )
    iss_anual: Decimal = Field(
        default=Decimal("0"),
        description=(
            "ISS retido (somatório). Default `0`. Alíquota varia por "
            "município (2-5%). Comum quando prestador serviço fora do "
            "município do tomador."
        ),
    )
    mdr_anual: Optional[Decimal] = Field(
        None,
        description=(
            "MDR/taxa de cartão/antecipação cobrada pelo adquirente "
            "(Stone, Cielo, Rede). **Não é retenção fiscal** — é "
            "despesa operacional. `None` quando pagador não é "
            "adquirente. Quando preenchido, orquestrador sinaliza "
            "como despesa em E5 (não compensa imposto)."
        ),
    )
    notas: Optional[str] = Field(
        None,
        description=(
            "Observações relevantes do informe (ex.: 'INSS recolhido "
            "pelo cliente', 'contrato sob CCT específica'). Max 500 chars."
        ),
    )

    @field_validator(
        "receita_bruta_anual",
        "estornos_anuais",
        "irrf_anual",
        "csll_anual",
        "pis_anual",
        "cofins_anual",
        "inss_anual",
        "iss_anual",
        "mdr_anual",
        mode="before",
    )
    @classmethod
    def _decimal_money(cls, v):
        return _coerce_decimal(v)

    @model_validator(mode="after")
    def _periodo_consistente(self):
        if self.periodo_fim < self.periodo_inicio:
            raise ValueError(
                f"periodo_fim={self.periodo_fim} antecede periodo_inicio={self.periodo_inicio}"
            )
        return self

    @model_validator(mode="after")
    def _simples_nacional_sem_retencoes_cssl_pis_cofins(self):
        # ADR-238 §Implementação: SN raramente sofre retenção CSLL/PIS/COFINS (LC 123 §6 IV-A); flag em notas.
        if self.regime_tributario != RegimeTributarioPJ.simples_nacional:
            return self
        soma = self.csll_anual + self.pis_anual + self.cofins_anual
        if soma > Decimal("0") and not self.notas:
            object.__setattr__(
                self, "notas", f"SN com retenção CSLL/PIS/COFINS={soma} (rever pagador)"
            )
        return self
