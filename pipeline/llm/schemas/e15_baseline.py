"""E1.5 output schema — baseline patrimonial extracted from IRPF and property documents."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator

_NON_DIGITS = re.compile(r"\D")


# Pino NORMALIZADOR, não de vacuidade: aqui há o que normalizar, e degradar para `None`
# mantém o sinal item-level em vez de queimar reask do Instructor (ADR-292). 2º uso da
# receita de `informe_aluguel._normalize_pii_digits` (ADR-288); o 3º extrai módulo.
def _cnpj_digits(v):
    """Máscara do documento → 14 dígitos; ilegível/sentinel → ``None``."""
    if v is None:
        return None
    digits = _NON_DIGITS.sub("", v if isinstance(v, str) else str(v))
    return digits if len(digits) == 14 else None


def _coerce_decimal(v):
    """Boundary LLM monetário = ``Decimal`` (ADR-090/ADR-259 §1): aceita ``int|str|float``
    via ``Decimal(str(v))`` — o prompt v1.2.0 pede string decimal, mas number JSON de
    respostas antigas/reask não pode brickar a extração."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float, str)):
        try:
            return Decimal(str(v))
        except InvalidOperation as exc:
            raise ValueError(
                f"E1.5: valor monetário inválido — esperado string decimal "
                f"'150000.00', recebido {type(v).__name__}={v!r}"
            ) from exc
    raise TypeError(f"E1.5: não consigo coerce {type(v).__name__}={v!r} para Decimal")


class PatrimonialItem(BaseModel):
    """A single asset or liability item from the IRPF declaration."""

    code: str = Field(..., description="IRPF item code (e.g. '01' for imóveis, '41' for poupança)")
    description: str = Field(..., description="Item description as in the declaration")
    # ADR-394 D1: a ficha de onde o item veio é a autoridade do eixo ativo×passivo.
    # Opcional na etapa 1 — só documento re-extraído a emite (D7).
    secao: Optional[str] = Field(
        None, description="Ficha da declaração: bens_direitos | dividas_onus"
    )
    # ADR-394 D1/D7: o rótulo do LLM é HINT, nunca decide o eixo. `category` é
    # aceito como alias para não brickar resposta de prompt anterior.
    category_hint: str = Field(
        ...,
        validation_alias=AliasChoices("category_hint", "category"),
        description="Hint: imovel, veiculo, investimento, conta_corrente, poupanca, previdencia, outros",
    )
    institution: Optional[str] = Field(None, description="Financial institution name or code")
    value_brl: Decimal = Field(..., description="Value in BRL as decimal string (e.g. '150000.00')")
    member_key: str = Field(..., description="Key of the family member who owns this item")
    year: int = Field(..., description="Reference tax year")
    # ADR-267: CPF do contribuinte (do campo 'CPF do Contribuinte' da declaração).
    # Identidade canônica primária — sobrevive a casamento/divórcio/abreviação de nome.
    cpf: Optional[str] = Field(
        None,
        description="CPF do contribuinte da declaração (11 dígitos, com ou sem máscara) — ADR-267",
    )

    # [[ADR-271]] §147 / [[A42.l15]]: a âncora que sobrevive a rename de descrição. A chave
    # de identidade usa a RAIZ (8 primeiros dígitos) lida do DOCUMENTO — nunca o code do
    # `institution_catalog`, senão um renome lá moveria o hash ([[ADR-400]] §1).
    cnpj_emissor: Optional[str] = Field(
        None,
        pattern=r"^\d{14}$",
        description=(
            "CNPJ da instituição emissora do ativo (somente dígitos, 14 chars), quando "
            "consta no documento; None quando ausente ou ilegível. Máscara é normalizada "
            "no validator."
        ),
    )

    _coerce_value = field_validator("value_brl", mode="before")(_coerce_decimal)
    _normalize_cnpj = field_validator("cnpj_emissor", mode="before")(_cnpj_digits)


class BaselinePatrimonialOutput(BaseModel):
    """Structured output for E1.5 — patrimonial baseline from IRPF declarations."""

    items: list[PatrimonialItem] = Field(
        default_factory=list, description="All patrimonial items extracted"
    )
    total_assets_brl: Decimal = Field(
        Decimal("0"), description="Sum of all asset values as decimal string"
    )
    total_liabilities_brl: Decimal = Field(
        Decimal("0"), description="Sum of all liability values as decimal string"
    )
    net_worth_brl: Decimal = Field(
        Decimal("0"), description="Total assets - total liabilities as decimal string"
    )
    reference_year: int = Field(..., description="Tax year of the declaration")
    members_found: list[str] = Field(
        default_factory=list, description="Member keys found in declarations"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: Optional[str] = None

    _coerce_totals = field_validator(
        "total_assets_brl", "total_liabilities_brl", "net_worth_brl", mode="before"
    )(_coerce_decimal)
