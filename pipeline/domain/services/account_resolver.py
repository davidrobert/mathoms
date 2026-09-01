"""Resolve `(banco, account_number) → member_key` puro (ADR-226 §3 · §Emenda 2026-08-31)."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Literal, Optional

from pipeline.domain.services.account_normalization import normalize_account_number
from pipeline.domain.types.config import BankAccountRecord

MemberConfidence = Literal["strict", "fallback_bank", "ambiguous", "unknown"]
AccountConfidence = Literal["resolved", "undetermined"]

# ADR-226 §Emenda 2026-08-31 (A40.l96): o campo único `confidence` carregava
# DOIS vereditos. A ADR declarava a regra duas vezes — "2+ membros" na lista de
# casos, "múltiplas contas" na prosa — e as duas eram verdadeiras sobre eixos
# diferentes; o consumidor lia o veredito de CONTA para responder a pergunta de
# TITULARIDADE. No corpus de dogfood isso marcava 4 de 11 instituições como
# "não sei de quem é" tendo dono único.
_logger = logging.getLogger("mathoms.account_resolver")


@dataclass(frozen=True)
class AccountResolution:
    """Resultado de `AccountResolver.resolve` — dois eixos ortogonais."""

    member_key: Optional[str]
    member_confidence: MemberConfidence
    account_confidence: AccountConfidence
    matched_account: Optional[BankAccountRecord] = None


def titulares(conta: BankAccountRecord) -> frozenset[str]:
    """Quem é dono da conta — inclui co-titulares quando ela é conjunta."""
    # Escrito sobre a conta e não sobre `member_key` para sobreviver ao V2 do
    # `is_joint` (ADR-226 §4): hoje `is_joint` nunca é populado e isto degenera
    # para {member_key}, mas conta conjunta É ambiguidade de titularidade e o
    # predicado já está certo para o dia em que o campo existir.
    if conta.is_joint:
        return frozenset({conta.member_key, *conta.co_titulares})
    return frozenset({conta.member_key})


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
        result = self._resolve_inner(institution_code, account_number_raw)
        _logger.info(
            "account_resolver.resolve",
            extra={
                "event": "account_resolver.resolve",
                "member_confidence": result.member_confidence,
                "account_confidence": result.account_confidence,
                "institution_code": institution_code,
            },
        )
        return result

    def _resolve_inner(
        self, institution_code: str, account_number_raw: Optional[str] = None
    ) -> AccountResolution:
        norm = normalize_account_number(account_number_raw)
        if norm is not None:
            hit = self._by_bank_and_num.get((institution_code, norm))
            if hit is not None:
                return AccountResolution(hit.member_key, "strict", "resolved", hit)
        contas_bank = self._by_bank.get(institution_code, [])
        if contas_bank:
            return self._from_bank(contas_bank)
        legacy_member = self._banco_membro_legacy.get(institution_code)
        if legacy_member:
            return AccountResolution(legacy_member, "fallback_bank", "undetermined")
        return AccountResolution(None, "unknown", "undetermined")

    def _from_bank(self, contas_bank: list[BankAccountRecord]) -> AccountResolution:
        """Titularidade e conta são perguntas separadas — responda cada uma."""
        donos: set[str] = set()
        for c in contas_bank:
            donos |= titulares(c)
        conta_conf: AccountConfidence = "resolved" if len(contas_bank) == 1 else "undetermined"
        if len(donos) != 1:
            return AccountResolution(None, "ambiguous", "undetermined")
        matched = contas_bank[0] if len(contas_bank) == 1 else None
        return AccountResolution(next(iter(donos)), "fallback_bank", conta_conf, matched)
