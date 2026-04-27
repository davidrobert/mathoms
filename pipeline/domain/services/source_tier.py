"""SourceTier — hierarquia universal de fontes para reconciliação E3 (ADR-146).

Sprint A7.6 (rules-as-code) consolida a documentação da hierarquia de
fontes e a regra de tie-breaking neste módulo. Para o "porquê":
ver ADR-146 em ``docs/DECISIONS.md``.

Hierarquia universal (tier ascendente — 1 = mais confiável)
============================================================

1. **TIER_LLM_STATEMENT** — Extração LLM de extrato OFX/PDF estruturado.
   Alta confiança: dados estruturados, datas precisas, descrições
   completas pelo LLM.
2. **TIER_REGEX_STATEMENT** — Extrato bancário parseado por regex
   (parsers em ``scripts/e2/banks/``). Alta confiança quando o parser
   cobre o formato; pode perder transações em formatos não cobertos.
3. **TIER_CARD_INVOICE** — Fatura de cartão de crédito. Cobertura
   parcial: só transações no cartão; pode duplicar com extrato quando
   há pagamento intermediado.
4. **TIER_APP_SCREENSHOT** — Screenshot de app extraído por LLM. Média
   confiança: dependente da qualidade da imagem; bom para contas de
   investimento sem extrato.
5. **TIER_EDITORIAL** — Declaração editorial / dedução IRPF / planilha
   manual do cliente. Baixa confiança automatizada, mas alta confiança
   humana — usado como ground truth para reconciliar discrepâncias
   finais.

Regra de reconciliação (E3)
===========================

Quando duas fontes reportam a **mesma transação** (matched por valor +
data ± ``tolerance_days`` + descrição similar), a fonte de **tier menor
(mais alto na hierarquia)** vence. Ties dentro do mesmo tier resolvem
via timestamp da extração — mais recente vence (evita instabilidade
quando o pipeline reroda; o último run é a "verdade" mais atualizada).

Override workspace-específico
=============================

Cada workspace pode override o tier por bank account via
``BankAccount.source_tier`` (NULL = usar default Mathoms). Resolução
runtime: ``resolve_account_tier(account, institution)`` consulta o
override e fallback para :func:`default_tier_for_source`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

# =============================================================================
# Tier constants
# =============================================================================


TIER_LLM_STATEMENT: Final[int] = 1
"""Extração LLM estruturada — fonte de máxima confiança."""

TIER_REGEX_STATEMENT: Final[int] = 2
"""Extrato bancário parseado por regex (e2/banks/*)."""

TIER_CARD_INVOICE: Final[int] = 3
"""Fatura de cartão (cobertura parcial)."""

TIER_APP_SCREENSHOT: Final[int] = 4
"""Screenshot de app extraído por LLM."""

TIER_EDITORIAL: Final[int] = 5
"""Declaração editorial / IRPF / planilha manual — fonte de mínima
confiança automatizada."""


# Mapping default por categoria de fonte. Workspace override substitui.
_DEFAULT_TIER_BY_SOURCE: Final[dict[str, int]] = {
    "llm_statement": TIER_LLM_STATEMENT,
    "regex_statement": TIER_REGEX_STATEMENT,
    "card_invoice": TIER_CARD_INVOICE,
    "app_screenshot": TIER_APP_SCREENSHOT,
    "editorial": TIER_EDITORIAL,
    "irpf": TIER_EDITORIAL,
}


# =============================================================================
# Source descriptor (para tie-breaking)
# =============================================================================


@dataclass(frozen=True)
class SourcedTransaction:
    """Transação com metadata de fonte para regra de tie-breaking ADR-146.

    Não substitui :class:`pipeline.domain.models.transaction.Transaction` — é
    um descriptor leve focado em "qual fonte vence quando duas reportam a
    mesma transação?".

    Campos:
        tier: tier resolvido (ver constants TIER_*).
        extracted_at: timestamp da extração — mais recente vence empate.
        identifier: id/hash da transação (debugging only).
    """

    tier: int
    extracted_at: datetime
    identifier: str = ""


# =============================================================================
# API
# =============================================================================


def default_tier_for_source(source_kind: str) -> int:
    """Retorna o tier default Mathoms para uma categoria de fonte.

    ``source_kind`` é uma key de :data:`_DEFAULT_TIER_BY_SOURCE` (ex.:
    ``"llm_statement"``, ``"card_invoice"``). Categoria desconhecida cai
    em :data:`TIER_EDITORIAL` (mais conservador).
    """
    return _DEFAULT_TIER_BY_SOURCE.get(source_kind, TIER_EDITORIAL)


def resolve_account_tier(workspace_override: int | None, source_kind: str) -> int:
    """Resolve o tier efetivo para uma transação.

    Override workspace-específico (``BankAccount.source_tier``) tem
    prioridade. NULL → usa default Mathoms baseado em ``source_kind``.
    """
    if workspace_override is not None:
        return workspace_override
    return default_tier_for_source(source_kind)


def pick_winner(a: SourcedTransaction, b: SourcedTransaction) -> SourcedTransaction:
    """Escolhe a fonte vencedora entre duas reportando a mesma transação.

    Regra ADR-146:
      1. Tier menor vence (mais confiável).
      2. Mesmo tier → timestamp de extração mais recente vence.

    Se ambos os campos empatam, retorna ``a`` (estável, idempotente).
    """
    if a.tier < b.tier:
        return a
    if b.tier < a.tier:
        return b
    if a.extracted_at >= b.extracted_at:
        return a
    return b
