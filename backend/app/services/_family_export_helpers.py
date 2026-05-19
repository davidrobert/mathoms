"""Helpers de serialização ``FamilyMember`` + ``BankAccount`` (ADR-226 PR1)."""

from __future__ import annotations

from typing import Any

from backend.app.models.family_member import BankAccount, FamilyMember
from backend.app.services.vault import get_vault
from pipeline.domain.services.account_normalization import normalize_account_number


def export_member_info(m: FamilyMember) -> dict[str, Any]:
    """Serializa atributos do membro (``cpf`` decriptado quando presente)."""
    vault = get_vault()
    cpf_plain = vault.decrypt(m.cpf_encrypted) if m.cpf_encrypted else None
    info: dict[str, Any] = {"nome_completo": m.full_name, "nome_curto": m.short_name}
    if cpf_plain:
        info["cpf"] = cpf_plain
    if m.birth_date:
        info["data_nascimento"] = m.birth_date.isoformat()
    info["papel"] = m.role
    if m.extra:
        info.update(m.extra)
    return info


def export_bank_account(acc: BankAccount, member_key: str) -> dict[str, Any]:
    """Serializa conta bancária para ``contas[]`` (ADR-226 §2)."""
    return {
        "member_key": member_key,
        "institution_code": acc.institution_code,
        "account_type": acc.account_type,
        "account_number_raw": acc.account_number,
        "account_number_norm": normalize_account_number(acc.account_number),
        "agency": acc.agency,
        "is_joint": bool(getattr(acc, "is_joint", False)),
        "co_titulares": getattr(acc, "co_titulares", None) or [],
    }
