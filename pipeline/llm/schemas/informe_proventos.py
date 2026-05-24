"""Sub-schema Pydantic do Informe de Proventos (Ações + FII + JCP) — A17 L4 (ADR-238 D1/D2)."""

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
    raise TypeError(f"informe_proventos: não consigo coerce {type(v).__name__}={v!r} para Decimal")


class TipoProvento(str, Enum):
    """Tipo de provento — tratamento fiscal distinto por categoria."""

    dividendo = "dividendo"  # Isento PF (até reforma tributária)
    jcp = "jcp"  # Juros sobre Capital Próprio — tributação exclusiva 15%
    rend_fii = "rend_fii"  # Rendimento de FII — isento PF se requisitos
    bonificacao = "bonificacao"  # NÃO é renda — ajuste de custo médio


class Provento(BaseModel):
    """Evento de provento por ativo — Perini yield-on-cost (ADR-238 D1 §L4)."""

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(
        ...,
        min_length=4,
        max_length=10,
        pattern=r"^[A-Z0-9]{4,10}$",
        description=(
            "Ticker B3 (ex.: WEGE3, ITSA4, MXRF11). Letras maiúsculas + dígitos, "
            "sem ponto. FII tem sufixo numérico (`11`); ações `3`/`4`."
        ),
    )
    cnpj_pagador: str = Field(
        ...,
        pattern=r"^\d{14}$",
        description=(
            "CNPJ que efetuou o pagamento (geralmente corretora ou custodiante — "
            "XP, BTG, Rico). Pode diferir de `cnpj_fonte` (a companhia emissora)."
        ),
    )
    cnpj_fonte: Optional[str] = Field(
        None,
        pattern=r"^\d{14}$",
        description=(
            "CNPJ da companhia emissora do provento (ex.: WEGE3 = 84.429.695/0001-11). "
            "Distinto de `cnpj_pagador` quando há intermediário (corretora). "
            "Para conferência RFB usa-se o pagador; para análise patrimonial, a fonte."
        ),
    )
    tipo: TipoProvento = Field(
        ...,
        description=(
            "Categoria fiscal: `dividendo` (isento PF), `jcp` (exclusiva 15%), "
            "`rend_fii` (isento PF se requisitos), `bonificacao` (ajuste de custo)."
        ),
    )
    valor_brl: Decimal = Field(
        ...,
        description=(
            "Valor bruto do provento em BRL. Para JCP é o valor bruto (antes do "
            "IR retido); para dividendo/rend_fii é o valor líquido = bruto (isentos)."
        ),
    )
    data_pagamento: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Data do crédito (YYYY-MM-DD). Usada para agrupar por mês/ano.",
    )
    ir_retido_brl: Decimal = Field(
        default=Decimal("0"),
        description=(
            "IR retido na fonte sobre este evento. Default `0`. Em JCP = 15% sobre "
            "valor bruto (definitivo, não compensa). Dividendo/rend_fii: 0 (isento). "
            "Bonificação: 0 (não é renda)."
        ),
    )
    notas: Optional[str] = Field(
        None, description="Observações (ex.: 'desdobramento 1:2', 'amortização parcial')."
    )

    @field_validator("valor_brl", "ir_retido_brl", mode="before")
    @classmethod
    def _decimal_money(cls, v):
        return _coerce_decimal(v)

    @model_validator(mode="after")
    def _bonificacao_zero_ir(self):
        # Bonificação é ajuste de custo médio — não há IR retido (não é evento de renda).
        if self.tipo == TipoProvento.bonificacao and self.ir_retido_brl > Decimal("0"):
            raise ValueError(
                f"bonificacao com ir_retido_brl={self.ir_retido_brl} > 0 — bonificação "
                f"não é renda; IR retido indica erro de extração."
            )
        return self

    @model_validator(mode="after")
    def _dividendo_isento_pf_zero_ir(self):
        # Dividendo PF é isento até reforma tributária (Lei 9.249/95 art. 10).
        # IR retido > 0 sinaliza extração ruim OU mudança regulatória — flag.
        if self.tipo == TipoProvento.dividendo and self.ir_retido_brl > Decimal("0"):
            if self.notas is None or "PEC" not in self.notas.upper():
                object.__setattr__(
                    self,
                    "notas",
                    (
                        f"Dividendo com IR retido={self.ir_retido_brl} — atípico (isento PF "
                        f"até reforma tributária); verificar PEC dividendos ou extração."
                    ),
                )
        return self


class PosicaoCustodia(BaseModel):
    """Posição em 31/12 (opcional — algumas corretoras informam para yield-on-cost)."""

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., pattern=r"^[A-Z0-9]{4,10}$")
    quantidade: Decimal = Field(..., description="Quantidade total em 31/12 do ano-base.")
    custo_medio_brl: Optional[Decimal] = Field(
        None,
        description=(
            "Custo médio unitário (preço médio de aquisição). Permite calcular "
            "yield-on-cost. None quando corretora não informa."
        ),
    )
    valor_mercado_31_12: Optional[Decimal] = Field(
        None,
        description="Valor de mercado em 31/12 (preço de fechamento × quantidade).",
    )

    @field_validator("quantidade", "custo_medio_brl", "valor_mercado_31_12", mode="before")
    @classmethod
    def _decimal_money(cls, v):
        return _coerce_decimal(v)


class InformeProventosPayload(BaseModel):
    """Payload strict de informe anual de proventos — 1 corretora = 1 payload (ADR-238 D2)."""

    model_config = ConfigDict(extra="forbid")

    cnpj_emissor: str = Field(
        ...,
        pattern=r"^\d{14}$",
        description="CNPJ da corretora/holding emissora (XP, BTG, Rico, Itaúsa).",
    )
    nome_emissor: str = Field(..., min_length=2, description="Razão social literal do emissor.")
    proventos: list[Provento] = Field(
        default_factory=list,
        description=(
            "Eventos por ativo no ano-base. Pode ser empty quando corretora emite "
            "informe agregado sem detalhar eventos (raro)."
        ),
    )
    posicao_31_12: list[PosicaoCustodia] = Field(
        default_factory=list,
        description=(
            "Snapshot de custódia em 31/12 (opcional). Algumas corretoras informam "
            "quantidade + custo médio — útil para Perini yield-on-cost por ativo."
        ),
    )
    notas: Optional[str] = Field(None, description="Observações gerais do informe.")

    @model_validator(mode="after")
    def _ao_menos_um_provento_ou_posicao(self):
        # Informe vazio é extração ruim — pelo menos 1 dos dois deve estar populado.
        if not self.proventos and not self.posicao_31_12:
            raise ValueError(
                "informe_proventos vazio — ao menos 1 provento ou 1 posicao_31_12 "
                "deve ser populado. Re-tentar com `needs_review=true` upstream."
            )
        return self


# ─────────────────────── Helpers para downstream (yield-on-cost) ────────────


def total_proventos_por_ticker(payload: InformeProventosPayload) -> dict[str, Decimal]:
    """Soma valor_brl por ticker (excluindo bonificação — não é fluxo de renda)."""
    out: dict[str, Decimal] = {}
    for p in payload.proventos:
        if p.tipo == TipoProvento.bonificacao:
            continue  # bonificação é ajuste de custo, não renda
        out[p.ticker] = out.get(p.ticker, Decimal("0")) + p.valor_brl
    return out
