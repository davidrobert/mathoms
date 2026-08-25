"""Token monetário digitado na PROSA do parecer — detecção e normalização em cents.

Separado de ``parecer_evidencia`` (A40.l83) porque responde a outra pergunta: aquele
verifica se a CITAÇÃO resolve; este mede se o modelo escreveu o número em vez de
ancorá-lo. Os dois se encontram só em ``number_in_prose``, que é telemetria e não
gate ([[ADR-304]] §Emenda 2026-08-03).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

# Ancorada em R$ — percentuais, anos, datas e multiplicadores sem R$ ficam fora.
_MONEY_RE = re.compile(
    r"R\$\s*(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?(?:\s*(milh(?:[õo]es|[ãa]o)|mil|mi)\b)?"
)

# Faixa monetária na prosa ("R$ 250-300 mil") — telemetria de number_in_prose
# (ADR-296: prosa não deve conter R$; deve ser 0).
_RANGE_RE = re.compile(r"R\$\s*[\d.,]+\s*(?:-|–|\ba\b|\baté\b)\s*(?:R\$\s*)?[\d.,]+")

# Valor monetário SEM prefixo R$ ("720 mil reais", "720.000 reais", "3 milhões de
# reais") — o LLM pode driblar o R$ (KR1, A27); mesmos grupos de _MONEY_RE para reuso
# de _token_from_match (integer, decimals, mult).
_REAIS_RE = re.compile(
    r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?"
    r"(?:\s*(milh(?:[õo]es|[ãa]o)|mil|mi))?\s*(?:de\s+)?reais\b",
    re.IGNORECASE,
)

# Moeda estrangeira na prosa (A40.l30 item 7 — defeito (c) da ADR-304 §"evidência
# inflada"). NÃO é detector de transcrição, é de FABRICAÇÃO: medido em 2026-08-07, o
# exec context não contém nenhum US$ (`FormatHint` não tem `usd`, `_format_brl` é a
# única saída monetária, e `$.narrativas` não é projetado no manifest). Logo US$ na
# prosa não foi copiado de lugar nenhum. Contador SEPARADO de money_tokens_total:
# folhar moedas num número só é o defeito de unidade da ADR-358 §3. Consequência
# assumida: o catálogo é BRL-only por construção (`_entry_for` → format_value(v,"brl")),
# então valor USD não tem rota de âncora — telemetria, nunca gate (ver §Handoff).
_USD_RE = re.compile(
    r"(?:US\$|USD)\s*(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?"
    r"(?:\s*(milh(?:[õo]es|[ãa]o)|mil|mi)\b)?"
)
_DOLARES_RE = re.compile(
    r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?"
    r"(?:\s*(milh(?:[õo]es|[ãa]o)|mil|mi))?\s*(?:de\s+)?d[óo]lares\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MoneyToken:
    """Token monetário extraído da prosa — sempre em cents int (ADR-090)."""

    # RESÍDUO SEM CONSUMIDOR (era `value_mismatch`, ADR-296): nenhum call-site lê `cents`
    # nem `half_step_cents` — `verify_evidencia` só usa `len(money_tokens)`. Não existe
    # comparador prosa ↔ `ancoras[].valor_renderizado` em lugar nenhum do repo; é por isso
    # que `number_in_prose` detecta PRESENÇA e não divergência, e é essa ausência que
    # sustenta a reversão da ADR-304 §Emenda 2026-08-03. Mantido (não deletado) porque a
    # lane do comparador real precisa dos dois campos.
    cents: int
    # Semântica PROJETADA (nunca exercida): 0 = valor exato na prosa; >0 = a prosa
    # arredondou ("3 milhões"), então o match seria o intervalo [cents-h, cents+h).
    half_step_cents: int


def extract_money_tokens(prose_fields: list[Optional[str]]) -> list[MoneyToken]:
    return _tokens_for(prose_fields, (_MONEY_RE, _REAIS_RE))


def extract_usd_tokens(prose_fields: list[Optional[str]]) -> list[MoneyToken]:
    return _tokens_for(prose_fields, (_USD_RE, _DOLARES_RE))


def _tokens_for(
    prose_fields: list[Optional[str]], patterns: tuple[re.Pattern, ...]
) -> list[MoneyToken]:
    tokens: list[MoneyToken] = []
    for text in prose_fields:
        if text:
            tokens.extend(_dedupe_by_span(text, patterns))
    return tokens


def _dedupe_by_span(text: str, patterns: tuple[re.Pattern, ...]) -> list[MoneyToken]:
    """Um valor monetário = UM token. "R$ 720 mil reais" casa `_MONEY_RE` (0,10) E
    `_REAIS_RE` (3,16) — spans sobrepostos, 2 tokens para 1 valor. É o defeito (a) da
    ADR-304 §"evidência inflada" ("conta matches, não valores distintos"), e sem o
    dedupe ampliar o inventário de 3→9 campos re-baselinaria um número simultaneamente
    piso (poucos campos) e inflado (match duplo) — ninguém poderia interpretá-lo.
    Vence o match que começa antes; empate no início, o mais longo (o com prefixo R$,
    cujo `_token_from_match` lê o multiplicador correto)."""
    matches = sorted(
        (m for pattern in patterns for m in pattern.finditer(text)),
        key=lambda m: (m.start(), -m.end()),
    )
    kept: list[re.Match] = []
    covered_end = -1
    for match in matches:
        if match.start() < covered_end:
            continue
        kept.append(match)
        covered_end = match.end()
    return [_token_from_match(m) for m in kept]


def count_ranges(prose_fields: list[Optional[str]]) -> int:
    """Faixas R$ X–Y na prosa de item cujo campo-fonte não é faixa legítima."""
    return sum(len(_RANGE_RE.findall(text)) for text in prose_fields if text)


def _token_from_match(m: re.Match) -> MoneyToken:
    integer, decimals, mult = m.group(1), m.group(2), m.group(3)
    base = Decimal(integer.replace(".", ""))
    if decimals:
        base += Decimal(decimals) / (Decimal(10) ** len(decimals))
    if not mult:
        return MoneyToken(cents=_to_cents(base), half_step_cents=0)
    factor = Decimal(1_000) if mult == "mil" else Decimal(1_000_000)
    half_step = factor / (Decimal(10) ** len(decimals or "")) / 2
    return MoneyToken(cents=_to_cents(base * factor), half_step_cents=_to_cents(half_step))


def _to_cents(value: Decimal) -> int:
    return int((value * 100).to_integral_value(rounding=ROUND_HALF_UP))


__all__ = [
    "MoneyToken",
    "count_ranges",
    "extract_money_tokens",
    "extract_usd_tokens",
]
