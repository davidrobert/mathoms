"""Testes — ADR-146 source-tier tie-breaking (E3 reconciliation, A7.6).

Specs obrigatórias por ADR-146 §Consequências:
  (a) tier mais alto (numericamente menor) vence ainda que extração
      mais antiga.
  (b) mesmo tier → timestamp de extração mais recente vence.

Plus: idempotência (same input → same output) e fallback para
``TIER_EDITORIAL`` quando ``source_kind`` é desconhecido.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pipeline.domain.services.source_tier import (
    TIER_APP_SCREENSHOT,
    TIER_CARD_INVOICE,
    TIER_EDITORIAL,
    TIER_LLM_STATEMENT,
    TIER_REGEX_STATEMENT,
    SourcedTransaction,
    default_tier_for_source,
    pick_winner,
    resolve_account_tier,
)

# =============================================================================
# Spec (a) — tier mais alto vence ainda que extração mais antiga
# =============================================================================


def test_higher_tier_wins_over_older_extraction() -> None:
    """LLM extraction de 30 dias atrás vence fatura de cartão extraída
    agora — tier 1 < tier 3 mesmo com timestamp pior."""
    now = datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc)
    older = now - timedelta(days=30)

    llm_old = SourcedTransaction(tier=TIER_LLM_STATEMENT, extracted_at=older, identifier="LLM-old")
    invoice_new = SourcedTransaction(
        tier=TIER_CARD_INVOICE, extracted_at=now, identifier="Invoice-new"
    )

    winner = pick_winner(llm_old, invoice_new)
    assert winner.identifier == "LLM-old", "tier 1 (LLM) vence sobre tier 3 (fatura)"


def test_higher_tier_wins_irrespective_of_argument_order() -> None:
    """Ordem dos argumentos não muda o vencedor (operação comutativa)."""
    now = datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc)
    regex = SourcedTransaction(tier=TIER_REGEX_STATEMENT, extracted_at=now, identifier="regex")
    editorial = SourcedTransaction(
        tier=TIER_EDITORIAL, extracted_at=now + timedelta(days=1), identifier="editorial"
    )

    assert pick_winner(regex, editorial).identifier == "regex"
    assert pick_winner(editorial, regex).identifier == "regex"


# =============================================================================
# Spec (b) — mesmo tier → timestamp mais recente vence
# =============================================================================


def test_same_tier_newer_extraction_wins() -> None:
    """Dois extratos parseados por regex, mesmo tier — quem extraiu por
    último vence (idempotência: o último rerun é a verdade vigente)."""
    older = datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc)
    newer = older + timedelta(hours=2)

    a = SourcedTransaction(tier=TIER_REGEX_STATEMENT, extracted_at=older, identifier="run-1")
    b = SourcedTransaction(tier=TIER_REGEX_STATEMENT, extracted_at=newer, identifier="run-2")

    assert pick_winner(a, b).identifier == "run-2"
    assert pick_winner(b, a).identifier == "run-2"


def test_same_tier_same_timestamp_returns_first_arg() -> None:
    """Empate total → retorna o primeiro argumento (estável + idempotente)."""
    ts = datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc)
    a = SourcedTransaction(tier=TIER_LLM_STATEMENT, extracted_at=ts, identifier="A")
    b = SourcedTransaction(tier=TIER_LLM_STATEMENT, extracted_at=ts, identifier="B")
    assert pick_winner(a, b).identifier == "A"


# =============================================================================
# Default tier resolution + workspace override
# =============================================================================


def test_default_tier_for_known_source_kinds() -> None:
    assert default_tier_for_source("llm_statement") == TIER_LLM_STATEMENT
    assert default_tier_for_source("regex_statement") == TIER_REGEX_STATEMENT
    assert default_tier_for_source("card_invoice") == TIER_CARD_INVOICE
    assert default_tier_for_source("app_screenshot") == TIER_APP_SCREENSHOT
    assert default_tier_for_source("editorial") == TIER_EDITORIAL
    assert default_tier_for_source("irpf") == TIER_EDITORIAL


def test_default_tier_unknown_falls_back_to_editorial() -> None:
    """Source kind desconhecido → fallback conservador (TIER_EDITORIAL)."""
    assert default_tier_for_source("formato_novo_xyz") == TIER_EDITORIAL


def test_workspace_override_takes_precedence() -> None:
    """``BankAccount.source_tier`` populado override default Mathoms.
    Cliente pode tratar fatura como tier 1 se confia mais nela que no
    extrato (ex.: parser do extrato falha mas fatura sempre OK)."""
    assert resolve_account_tier(workspace_override=1, source_kind="card_invoice") == 1
    assert resolve_account_tier(workspace_override=5, source_kind="llm_statement") == 5


def test_workspace_override_none_uses_default() -> None:
    assert (
        resolve_account_tier(workspace_override=None, source_kind="llm_statement")
        == TIER_LLM_STATEMENT
    )
    assert (
        resolve_account_tier(workspace_override=None, source_kind="card_invoice")
        == TIER_CARD_INVOICE
    )
