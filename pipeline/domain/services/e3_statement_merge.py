"""Merge cross-file dos statements de um mesmo ``output_key`` do E3.

O ``output_key`` é ``{banco}_{tipo_conta}_{MOEDA}_{YYYYMM}_{YYYYMM}``
(``generate_legacy_filename``) — sem eixo de membro nem de conta. Duas contas
distintas do mesmo banco/tipo/moeda/período caem no mesmo artefato, então o
número de conta do grupo só é afirmável quando há um único ``_norm`` distinto;
herdar o do primeiro afirmaria identidade que o grupo não tem. Mesmo predicado
set-based de ``continuity_chain._sole_number`` (emenda ADR-310).
"""

from __future__ import annotations

from dataclasses import replace

from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Transaction


def _sole_account_number(stmts: list[BankStatement]) -> tuple[str | None, str | None]:
    """``(raw, norm)`` do único ``_norm`` distinto do grupo; ``(None, None)`` se 0 ou ≥2."""
    norms = {s.account_number_norm for s in stmts if s.account_number_norm}
    if len(norms) != 1:
        return None, None
    norm = next(iter(norms))
    raws = {s.account_number_raw for s in stmts if s.account_number_norm == norm}
    return (next(iter(raws)) if len(raws) == 1 else None), norm


def merge_group_statements(
    stmts: list[BankStatement], transactions: list[Transaction]
) -> BankStatement:
    """Funde os statements de um ``output_key`` em um único ``BankStatement``."""
    # `replace`, não construtor campo-a-campo: a reconstrução explícita apagava
    # todo campo adicionado depois dela — foi assim que `account_number_*`
    # (ADR-226 PR2) chegava `None` no payload E3.
    raw, norm = _sole_account_number(stmts)
    return replace(
        stmts[0],
        period_start=min(s.period_start for s in stmts),
        period_end=max(s.period_end for s in stmts),
        transactions=transactions,
        opening_balance=stmts[0].opening_balance,
        closing_balance=stmts[-1].closing_balance,
        source_document=None,
        notes=[f"merged from {len(stmts)} source statements"],
        account_number_raw=raw,
        account_number_norm=norm,
    )
