"""Parsers compartilhados pelos adapters do ``ConfigStore`` (ADR-134)."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from pipeline.domain.services.account_normalization import normalize_account_number
from pipeline.domain.types.config import (
    BankAccountRecord,
    CategorizationConfig,
    CategoryDef,
    FamilyMemberRecord,
    FamilyMembersConfig,
    InstitutionDef,
    InstitutionsCatalog,
    ReportLayout,
    TransferInternalConfig,
)


def parse_categorization(data: Mapping[str, Any]) -> CategorizationConfig:
    """Converte ``{expense_keywords: {code: [words]}, ...}`` em ``CategorizationConfig``."""
    keywords = data.get("expense_keywords") or {}
    categories: dict[str, CategoryDef] = {}
    for code, words in keywords.items():
        if isinstance(words, list):
            categories[str(code)] = CategoryDef(
                code=str(code),
                name=str(code).replace("_", " ").title(),
                keywords=tuple(str(w) for w in words),
            )
    metadata = {k: v for k, v in data.items() if k.startswith("_")}
    return CategorizationConfig(categories=categories, metadata=metadata)


def parse_family_members(data: Mapping[str, Any]) -> FamilyMembersConfig:
    """Constrói ``FamilyMembersConfig`` a partir do dict ``family_members.json``."""
    family = data.get("familia") or {}
    surname = family.get("sobrenome") if isinstance(family, dict) else None
    members = _build_members(data.get("membros"))
    bank_to_member = _build_bank_to_member(data.get("banco_membro"))
    accounts = _build_accounts(data.get("contas"))
    transfers_block = data.get("transferencias_internas")
    transfers = parse_transfers(transfers_block) if isinstance(transfers_block, dict) else None
    return FamilyMembersConfig(
        members=members,
        bank_to_member=bank_to_member,
        accounts=accounts,
        family_surname=str(surname) if surname else None,
        transfers=transfers,
    )


def _build_accounts(raw: Any) -> tuple[BankAccountRecord, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(_make_account(c) for c in raw if isinstance(c, dict))


def _make_account(raw: Mapping[str, Any]) -> BankAccountRecord:
    raw_num = raw.get("account_number_raw") or raw.get("account_number")
    norm = raw.get("account_number_norm") or normalize_account_number(
        str(raw_num) if raw_num is not None else None
    )
    co = raw.get("co_titulares") or ()
    return BankAccountRecord(
        member_key=str(raw.get("member_key") or ""),
        institution_code=str(raw.get("institution_code") or ""),
        account_type=str(raw.get("account_type") or ""),
        account_number_norm=norm,
        account_number_raw=str(raw_num) if raw_num else None,
        agency=str(raw["agency"]) if raw.get("agency") else None,
        is_joint=bool(raw.get("is_joint", False)),
        co_titulares=tuple(str(c) for c in co) if isinstance(co, list) else (),
    )


def _build_members(raw_members: Any) -> tuple[FamilyMemberRecord, ...]:
    if not isinstance(raw_members, dict):
        return ()
    return tuple(
        _make_member(str(key), value)
        for key, value in raw_members.items()
        if isinstance(value, dict)
    )


def _make_member(key: str, raw: Mapping[str, Any]) -> FamilyMemberRecord:
    return FamilyMemberRecord(
        key=key,
        full_name=str(raw.get("nome_completo") or ""),
        short_name=str(raw.get("nome_curto") or ""),
        role=str(raw.get("papel") or "titular"),
        cpf=str(raw["cpf"]) if raw.get("cpf") else None,
        birth_date=str(raw["data_nascimento"]) if raw.get("data_nascimento") else None,
        extra=_filter_known_fields(raw),
    )


def _build_bank_to_member(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {str(code): owner for code, owner in raw.items() if isinstance(owner, str)}


def _filter_known_fields(raw: Mapping[str, Any]) -> Mapping[str, object]:
    drop = {"nome_completo", "nome_curto", "papel", "cpf", "data_nascimento"}
    return {k: v for k, v in raw.items() if k not in drop}


def parse_transfers(block: Mapping[str, Any]) -> TransferInternalConfig:
    """Constrói ``TransferInternalConfig`` a partir do bloco ``transferencias_internas``."""
    pix = block.get("patterns_pix") or []
    glob = block.get("patterns_global") or []
    recipients = block.get("recipients") or []
    return TransferInternalConfig(
        recipients=tuple(str(r) for r in recipients) if isinstance(recipients, list) else (),
        patterns_pix=tuple(str(p) for p in pix) if isinstance(pix, list) else (),
        patterns_global=tuple(str(p) for p in glob) if isinstance(glob, list) else (),
        patterns_bank_specific=_build_bank_specific_patterns(block.get("patterns_bank_specific")),
    )


def _build_bank_specific_patterns(raw: Any) -> dict[str, tuple[str, ...]]:
    if not isinstance(raw, dict):
        return {}
    return {
        str(code): tuple(str(p) for p in patterns)
        for code, patterns in raw.items()
        if isinstance(patterns, list)
    }


def parse_institutions(data: Mapping[str, Any]) -> InstitutionsCatalog:
    """Constrói ``InstitutionsCatalog`` a partir do dict ``institutions.json``."""
    canonical = data.get("banco_canonical") or {}
    layouts = data.get("layouts") or {}
    if not isinstance(canonical, dict):
        return InstitutionsCatalog(institutions={})
    institutions = {
        str(code): InstitutionDef(
            code=str(code),
            name=str(name),
            parser=_layout_parser(layouts, code),
        )
        for code, name in canonical.items()
    }
    return InstitutionsCatalog(institutions=institutions)


def _layout_parser(layouts: Any, code: Any) -> Optional[str]:
    if not isinstance(layouts, dict):
        return None
    layout_meta = layouts.get(code)
    if not isinstance(layout_meta, dict):
        return None
    parser_value = layout_meta.get("parser")
    return parser_value if isinstance(parser_value, str) else None


def parse_report_layout(data: Mapping[str, Any]) -> ReportLayout:
    """Constrói ``ReportLayout`` a partir do dict YAML/JSON."""
    sections_raw = data.get("sections") or ()
    sections = (
        tuple(dict(s) for s in sections_raw if isinstance(s, dict))
        if isinstance(sections_raw, list)
        else ()
    )
    metadata = {k: v for k, v in data.items() if k != "sections"}
    return ReportLayout(sections=sections, metadata=metadata)
