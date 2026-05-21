"""Sub-schema do informe anual de Previdência Privada (PGBL/VGBL) — A17 L1 (ADR-238 D2)."""

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
    raise TypeError(
        f"informe_previdencia: não consigo coerce {type(v).__name__}={v!r} para Decimal"
    )


class PlanoTipo(str, Enum):
    """PGBL deduz IRPF (12% renda) e tributa saldo; VGBL não deduz e tributa só rendimento (ADR-238 D8)."""

    pgbl = "pgbl"
    vgbl = "vgbl"


class RegimeTributacao(str, Enum):
    """Progressivo segue tabela IRPF; regressivo decresce com prazo (35% <2y → 10% >10y)."""

    progressivo = "progressivo"
    regressivo = "regressivo"


class InformePrevidenciaPayload(BaseModel):
    """Payload strict de informe anual PGBL/VGBL — 1 plano = 1 payload (ADR-238 D2)."""

    model_config = ConfigDict(extra="forbid")

    numero_certificado: Optional[str] = Field(
        None,
        min_length=1,
        description=(
            "Número do certificado do plano (identifica plano único quando "
            "participante tem múltiplos com a mesma seguradora). None quando "
            "o informe não destaca certificado."
        ),
    )
    plano_tipo: PlanoTipo = Field(
        ...,
        description="PGBL ou VGBL — invariante de cálculo PGBL capacity.",
    )
    regime_tributacao: RegimeTributacao = Field(
        ...,
        description="Progressivo (tabela IRPF) ou Regressivo (decresce com prazo).",
    )
    data_adesao: Optional[str] = Field(
        None,
        pattern=r"^\d{4}-\d{2}(-\d{2})?$",
        description=(
            "Data de adesão ao plano (YYYY-MM ou YYYY-MM-DD). Necessária para "
            "estimativa de alíquota efetiva no regime regressivo. None quando "
            "ausente no informe."
        ),
    )
    contribuicoes_anuais: Decimal = Field(
        ...,
        description=(
            "Total contribuído no ano-base (somatório). Em PGBL é o valor "
            "potencialmente dedutível (limite 12% da renda tributável). "
            "VGBL: somente registro, não deduz."
        ),
    )
    rendimentos_anuais: Decimal = Field(
        default=Decimal("0"),
        description=(
            "Variação positiva no ano (rendimento bruto antes do IR no resgate). "
            "Default 0 quando informe traz só contribuições. Para VGBL, é a "
            "base do IR no resgate."
        ),
    )
    saldo_01_01: Optional[Decimal] = Field(
        None,
        description=(
            "Saldo total acumulado em 01/01 do ano-base (snapshot inicial). "
            "Usado em audit ``saldo_01_01[ano] == saldo_31_12[ano-1]`` para "
            "detectar drift informe vs E1.6 do ano anterior. None quando o "
            "informe não destaca."
        ),
    )
    saldo_31_12: Decimal = Field(
        ...,
        description=(
            "Saldo total acumulado em 31/12 do ano-base. "
            "Compõe ``bens_direitos[]`` IRPF código 97 (Previdência Privada)."
        ),
    )
    resgates_anuais: Decimal = Field(
        default=Decimal("0"),
        description="Total de resgates no ano (parciais ou totais). Default 0.",
    )
    ir_retido_anual: Decimal = Field(
        default=Decimal("0"),
        description=(
            "IR retido na fonte sobre resgates no ano. Default 0 quando não "
            "houve resgate ou regime progressivo com retenção via DARF."
        ),
    )
    notas: Optional[str] = Field(
        None,
        description="Observações extraídas do informe (cláusulas, suspensões, portabilidades).",
    )

    @field_validator(
        "contribuicoes_anuais",
        "rendimentos_anuais",
        "saldo_01_01",
        "saldo_31_12",
        "resgates_anuais",
        "ir_retido_anual",
        mode="before",
    )
    @classmethod
    def _decimal_money(cls, v):
        return _coerce_decimal(v)

    @model_validator(mode="after")
    def _data_adesao_obrigatoria_para_regressivo(self):
        # Regime regressivo: alíquota efetiva depende de anos_desde_adesao
        # (35% <2y → 10% >10y, PEPS). Sem data_adesao, calculator IR não roda.
        if self.regime_tributacao == RegimeTributacao.regressivo and self.data_adesao is None:
            raise ValueError(
                "regime_tributacao=regressivo exige data_adesao "
                "(alíquota PEPS depende de anos_desde_adesao)"
            )
        return self
