"""Resolve `(banco, account_number) → member_key` puro (ADR-226 §3)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Literal, Optional

from pipeline.domain.services.account_normalization import normalize_account_number
from pipeline.domain.types.config import BankAccountRecord

Confidence = Literal["strict", "fallback_bank", "ambiguous", "unknown"]


@dataclass(frozen=True)
class AccountResolution:
    """Resultado de `AccountResolver.resolve`."""

    member_key: Optional[str]
    confidence: Confidence
    matched_account: Optional[BankAccountRecord] = None


class AccountResolver:
    """Resolve member_key dado (institution_code, account_number_raw)."""

    def __init__(
        self,
        contas: Iterable[BankAccountRecord],
        banco_membro_legacy: Optional[dict[str, str]] = None,
    ) -> None:
        self._contas = list(contas)
        self._banco_membro_legacy = banco_membro_legacy or {}
        self._by_bank_and_num: dict[tuple[str, str], BankAccountRecord] = {
            (c.institution_code, c.account_number_norm): c
            for c in self._contas
            if c.account_number_norm is not None
        }
        self._by_bank: dict[str, list[BankAccountRecord]] = defaultdict(list)
        for c in self._contas:
            self._by_bank[c.institution_code].append(c)

    def resolve(
        self, institution_code: str, account_number_raw: Optional[str] = None
    ) -> AccountResolution:
        norm = normalize_account_number(account_number_raw)
        if norm is not None:
            hit = self._by_bank_and_num.get((institution_code, norm))
            if hit is not None:
                return AccountResolution(hit.member_key, "strict", hit)
        contas_bank = self._by_bank.get(institution_code, [])
        if len(contas_bank) == 1:
            return AccountResolution(contas_bank[0].member_key, "fallback_bank", contas_bank[0])
        if len(contas_bank) > 1:
            return AccountResolution(None, "ambiguous", None)
        legacy_member = self._banco_membro_legacy.get(institution_code)
        if legacy_member:
            return AccountResolution(legacy_member, "fallback_bank", None)
        return AccountResolution(None, "unknown", None)
