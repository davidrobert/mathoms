"""Política única de aceite de conta sugerida pelo IRPF ([[ADR-229]] §2-§3 · [[ADR-430]] §2)."""

# A A40.l96 existe porque `banco_membro` tinha DOIS produtores lendo fontes
# diferentes. Escrever uma segunda cópia desta precedência — uma para os cards da
# UI, outra para o merge do pipeline — repetiria o defeito uma camada acima, e o
# segundo produtor divergiria em silêncio. Invariante que este módulo compra:
# o pipeline funde exatamente os hints que a UI ofereceria ao usuário.

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Literal, Optional

DecisaoHint = Literal["emit", "exact", "dismissed", "skip"]
"""`emit` entra; `exact` já existe curada; `dismissed` o usuário recusou; `skip` sem dados."""

_DIGITS_RE = re.compile(r"\D")


def normalize_account_digits(raw: Optional[str] = None) -> Optional[str]:
    """Digits-only do `account_number` ([[ADR-226]] §1)."""
    if raw is None:
        return None
    digits = _DIGITS_RE.sub("", raw)
    return digits or None


def build_existing_indexes(
    members: list[Any],
) -> tuple[dict[tuple[str, str], Any], dict[tuple[str, str], list[Any]]]:
    """Índices das contas JÁ CURADAS: `(banco, numero)` e `(banco, membro)`."""
    by_bank_num: dict[tuple[str, str], Any] = {}
    by_bank_member: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for m in members:
        for acc in m.accounts:
            by_bank_member[(acc.institution_code, m.key)].append(acc)
            norm = normalize_account_digits(acc.account_number)
            if norm is not None:
                by_bank_num[(acc.institution_code, norm)] = acc
    return by_bank_num, by_bank_member


def dismissed_keys_for_year(
    dismissals: list[Any], irpf_year: int
) -> set[tuple[int, str, Optional[str]]]:
    """Chaves recusadas pelo usuário no ano — o "não" dele é registro, não ruído."""
    return {
        (d.irpf_year, d.institution_code, d.account_number_norm)
        for d in dismissals
        if d.irpf_year == irpf_year
    }


def conta_normalizada(conta: dict[str, Any]) -> Optional[str]:
    return conta.get("account_number_norm") or normalize_account_digits(
        conta.get("account_number_raw")
    )


def classificar_hint(
    conta: dict[str, Any],
    *,
    irpf_year: int,
    by_bank_num: dict[tuple[str, str], Any],
    dismissed_keys: set[tuple[int, str, Optional[str]]],
) -> DecisaoHint:
    """Decide o destino de UMA conta do artefato E1. Puro."""
    inst = conta.get("institution_code")
    if not inst or not conta.get("member_key"):
        return "skip"
    norm = conta_normalizada(conta)
    if norm is not None and (inst, norm) in by_bank_num:
        return "exact"
    if (irpf_year, inst, norm) in dismissed_keys:
        return "dismissed"
    return "emit"
