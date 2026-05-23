"""Sub-schema Pydantic do Informe Financeiro PF (4 quadros RFB + Wise multi-moeda) — A17 L3 (ADR-238 D1/D2)."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _coerce_decimal(v):
    """Coerção monetária no boundary do LLM (ADR-090)."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, str, float)):
        return Decimal(str(v))
    raise TypeError(f"informe_pf: não consigo coerce {type(v).__name__}={v!r} para Decimal")


class TipoProduto(str, Enum):
    """Classificação interna de produto bancário PF (downstream consumer)."""

    poupanca = "poupanca"
    cdb = "cdb"
    lci = "lci"
    lca = "lca"
    fundo_rf = "fundo_rf"
    fundo_acoes = "fundo_acoes"
    fii = "fii"
    conta_corrente = "conta_corrente"
    conta_pagamento = "conta_pagamento"
    conta_exterior = "conta_exterior"  # Wise, Avenue, Nomad, Stake
    outros = "outros"


class QuadroEntry(BaseModel):
    """Linha genérica em um dos 4 quadros RFB — rendimentos ou bens/direitos."""

    model_config = ConfigDict(extra="forbid")

    codigo_rfb: str = Field(
        ...,
        min_length=2,
        max_length=4,
        description=(
            "Código RFB literal do quadro. Rendimentos tributáveis: 10/11/12/13/03. "
            "Isentos: 01/02/09/19/24. Exclusiva: 06/10. Bens/Direitos: 41 (doméstico), "
            "62 (conta exterior), 70 (CDB), 71 (FII), 31 (ações). String para preservar "
            "zero-padding e códigos compostos."
        ),
    )
    fonte_pagadora_cnpj: str = Field(
        ...,
        pattern=r"^\d{14}$",
        description="CNPJ da fonte pagadora literal (14 dígitos sem máscara).",
    )
    fonte_pagadora_nome: str = Field(..., min_length=2, description="Razão social literal.")
    descricao: str = Field(
        ...,
        min_length=2,
        description="Descrição literal do informe (ex.: 'CDB DI 100% Itaú 90 dias').",
    )
    valor: Decimal = Field(
        ...,
        description=(
            "Valor literal do informe na moeda original. Para rendimentos = "
            "somatório anual; para bens/direitos = saldo em 31/12 do ano-base. "
            "Conversão PTAX para BRL ocorre downstream (consolidate_baseline)."
        ),
    )
    moeda: str = Field(
        default="BRL",
        pattern=r"^[A-Z]{3}$",
        description=(
            "ISO 4217 (BRL default). Wise/Avenue/Nomad usam USD/EUR/GBP — o "
            "downstream consumer converte via market_rates (PTAX 31/12)."
        ),
    )
    ir_retido: Decimal = Field(
        default=Decimal("0"),
        description=(
            "IR retido na fonte sobre este item (somatório anual). Default 0. "
            "Em quadro exclusiva (cód. 06/10), IR é definitivo (não compensa). "
            "Em quadro tributáveis (cód. 10-13), IR compensa na declaração."
        ),
    )
    notas: Optional[str] = Field(
        None,
        description="Observações relevantes (ex.: 'rendimento líquido informado').",
    )

    @field_validator("valor", "ir_retido", mode="before")
    @classmethod
    def _decimal_money(cls, v):
        return _coerce_decimal(v)


class SaldoProduto(BaseModel):
    """Saldo 31/12 por produto — sub-bucket para consolidate_baseline merger (ADR-238 D5)."""

    model_config = ConfigDict(extra="forbid")

    tipo: TipoProduto = Field(
        ...,
        description=(
            "Classificação interna (downstream — não vem do informe). LLM infere a "
            "partir da descrição literal. Default `outros` quando ambíguo."
        ),
    )
    descricao: str = Field(..., min_length=2)
    codigo_rfb: str = Field(
        ...,
        min_length=2,
        max_length=4,
        description=(
            "Mesmo código do `bens_direitos[]`. 41 doméstico, 62 conta exterior, "
            "70 CDB, 71 FII, 31 ações. String para preservar zero-padding."
        ),
    )
    saldo: Decimal = Field(..., description="Saldo literal em 31/12 do ano-base na moeda original.")
    moeda: str = Field(
        default="BRL",
        pattern=r"^[A-Z]{3}$",
        description="ISO 4217. Wise/Avenue → USD/EUR/GBP; doméstico → BRL.",
    )
    fonte_pagadora_cnpj: str = Field(..., pattern=r"^\d{14}$")

    @field_validator("saldo", mode="before")
    @classmethod
    def _decimal_money(cls, v):
        return _coerce_decimal(v)

    @model_validator(mode="after")
    def _codigo_62_implies_conta_exterior(self):
        # ADR-238 §D1 Wise: código RFB 62 é exclusivo para conta-corrente no exterior
        # em moeda estrangeira. Se LLM extraiu 62 + tipo doméstico, é inconsistência.
        if self.codigo_rfb == "62" and self.tipo != TipoProduto.conta_exterior:
            raise ValueError(
                f"codigo_rfb=62 (conta exterior ME) exige tipo=conta_exterior, "
                f"recebeu tipo={self.tipo.value}"
            )
        return self

    @model_validator(mode="after")
    def _conta_exterior_exige_moeda_nao_brl(self):
        # Inverso: conta_exterior sem moeda estrangeira é flag de extração ruim.
        if self.tipo == TipoProduto.conta_exterior and self.moeda == "BRL":
            raise ValueError(
                "tipo=conta_exterior exige moeda != 'BRL' (recebeu BRL). "
                "Wise/Avenue/Nomad declaram saldo em USD/EUR/GBP."
            )
        return self


class InformeFinanceiroPFPayload(BaseModel):
    """Payload strict de informe anual financeiro PF — 1 emissor = 1 payload (ADR-238 D2)."""

    model_config = ConfigDict(extra="forbid")

    cnpj_emissor: str = Field(
        ...,
        pattern=r"^\d{14}$",
        description=(
            "CNPJ do banco/corretora emissor. Usado para matching com institution_catalog."
        ),
    )
    nome_emissor: str = Field(..., min_length=2, description="Razão social literal do emissor.")
    # Quadros RFB — empty list permitido (nem todo banco emite todos quadros).
    rendimentos_tributaveis: list[QuadroEntry] = Field(
        default_factory=list,
        description=(
            "Quadro 1 — códigos 10 (salário PJ), 11 (aposentadoria), 12 (pensão), "
            "13 (rendimentos no exterior), 03 (aluguel PF→PF). IR retido compensa "
            "na declaração."
        ),
    )
    rendimentos_isentos: list[QuadroEntry] = Field(
        default_factory=list,
        description=(
            "Quadro 2 — códigos 01 (FII), 02 (dividendos), 03 (poupança), 09 "
            "(LCI/LCA), 19 (rendimentos PF→PF outros), 24 (transferência patrimonial). "
            "**Variação cambial NÃO entra aqui** — é GCAP (warning E5)."
        ),
    )
    rendimentos_exclusiva: list[QuadroEntry] = Field(
        default_factory=list,
        description=(
            "Quadro 3 — códigos 06 (CDB/RF), 10 (fundos), 26 (13º). IR já retido "
            "definitivo — não gera 'IR a recuperar'."
        ),
    )
    bens_direitos: list[QuadroEntry] = Field(
        default_factory=list,
        description=(
            "Quadro 4 — saldo em 31/12. Códigos 41 (depósito doméstico), 62 "
            "(conta exterior ME — Wise/Avenue/Nomad), 70 (CDB), 71 (FII), 31 "
            "(ações). Espelha `saldos_31_12[]` em forma fiscal."
        ),
    )
    saldos_31_12: list[SaldoProduto] = Field(
        default_factory=list,
        description=(
            "Vista consolidada dos saldos em 31/12 (para consolidate_baseline). "
            "Pode divergir de `bens_direitos[]` quando informe agrega ou separa "
            "diferentemente. Default `[]` quando informe só traz quadros RFB."
        ),
    )
    notas: Optional[str] = Field(None, description="Observações gerais do informe.")

    @model_validator(mode="after")
    def _ao_menos_um_quadro_nao_vazio(self):
        # Informe PF sem nenhum quadro é extração ruim (ou layout não-RFB).
        if (
            not self.rendimentos_tributaveis
            and not self.rendimentos_isentos
            and not self.rendimentos_exclusiva
            and not self.bens_direitos
            and not self.saldos_31_12
        ):
            raise ValueError(
                "informe_pf vazio — ao menos 1 dos 4 quadros RFB ou saldos_31_12 "
                "deve ser populado. Re-tentar com `needs_review=true` upstream."
            )
        return self


# ─────────────────────── Helpers para downstream ────────────────────────────


def has_conta_exterior(payload: InformeFinanceiroPFPayload) -> bool:
    """True se algum saldo está em conta no exterior (Wise/Avenue/Nomad). Triggers PTAX + CBE check."""
    return any(s.tipo == TipoProduto.conta_exterior for s in payload.saldos_31_12) or any(
        q.codigo_rfb == "62" for q in payload.bens_direitos
    )
