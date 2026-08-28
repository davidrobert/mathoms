"""Response DTOs do card Exposição Cambial V2 (ADR-224 §5; read-time service-layer; ADR-090: Decimal string no wire). `share_pct` e `pct_investivel_financeiro` são taxas em [0..100], não monetárias."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

LastroMoeda = Literal["BRL", "USD", "EUR", "MIXED", "OTHER"]
MatchKind = Literal["ticker", "cnpj", "description"]


class ExposicaoCambialPorMoedaDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    moeda: str
    valor_brl: Decimal
    # taxa em [0..100], não monetária — share dentro da exposição
    share_pct: float


class ExposicaoCambialAtivoDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str
    moeda: str
    valor_brl: Decimal
    tipo: str
    lastro_source: str = Field(
        ...,
        description="'override' | 'catalog' | 'fallback_classe' — auditável no card.",
    )


class ExposicaoCambialResponse(BaseModel):
    """Resposta do `GET /v1/workspaces/{ws}/cards/exposicao-cambial`."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    base_disponivel: bool = Field(
        ...,
        description=(
            "False = não houve base para calcular (artefato ausente, ou payload sem "
            "`patrimonio.caixa_detalhes`/denominador). Distingue 'não sei' de 'zero "
            "exposição': sem isto, ausência de dado vira afirmação de ausência de "
            "exposição na tela. Quando False, os campos de valor vêm `null` — o zero "
            "falso fica infabricável no consumidor."
        ),
    )
    total_brl: Optional[Decimal] = None
    # taxa em [0..100], não monetária — share do investível financeiro
    pct_investivel_financeiro: Optional[float] = None
    por_moeda: list[ExposicaoCambialPorMoedaDTO]
    # O vocabulário sai do comentário e vira contrato (A40.l80): `indeterminado`
    # é o estado que o E5 publica quando algum componente não é apurado, e o card
    # tem de poder dizê-lo em vez de julgar faixa por conta própria.
    tier: Optional[Literal["verde", "amarelo", "vermelho", "indeterminado", "empty"]] = Field(
        default=None, description="Faixa de proteção; `indeterminado` = veredito suprimido."
    )
    alvo_moeda_forte_brl: Optional[Decimal] = Field(
        None,
        description=(
            "Quanto o piso verde representa em reais para este patrimônio. Vem do "
            "backend para o threshold não passar a existir em dois lugares."
        ),
    )
    # A40.l80 ([[ADR-412]] §D7): com foto anual no numerador o ALVO some e o motivo ocupa o
    # lugar dele. A medida (`total_brl`, `pct`) nunca some — o que morre é o "compre R$ X",
    # única saída que autoriza gastar dinheiro sobre saldo que ninguém confirmou.
    alvo_suprimido_motivo: Optional[str] = Field(
        default=None,
        description="Por que o alvo dimensionado não foi emitido; `None` quando ele existe.",
    )
    ativos_contribuintes: list[ExposicaoCambialAtivoDTO]
    catalog_version: int = 1
    source_run_id: Optional[str] = None
    computed_at: datetime


class AssetOverrideCommand(BaseModel):
    """Body do `POST /v1/workspaces/{ws}/cards/exposicao-cambial/overrides`."""

    model_config = ConfigDict(extra="forbid")

    match_kind: MatchKind
    asset_match_key: str = Field(..., min_length=1, max_length=200)
    lastro_moeda: LastroMoeda


class AssetOverrideResponse(BaseModel):
    """Snapshot do override após upsert (ADR-224 §2; sticky per `(ws, match_kind, key)`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    workspace_id: str
    match_kind: MatchKind
    asset_match_key: str
    lastro_moeda: LastroMoeda
    override_source: str
    created_at: datetime
    updated_at: datetime
    created_by_user_id: Optional[str] = None


class AssetOverrideListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    overrides: list[AssetOverrideResponse]
