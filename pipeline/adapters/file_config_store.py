"""``FileConfigStore`` — adapter legado lê ``PROJECT_DIR / config`` (deprecated, A7.5)."""

from __future__ import annotations

import json
import warnings
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml

from pipeline.domain.types.config import (
    CategorizationConfig,
    CategoryDef,
    FamilyMemberRecord,
    FamilyMembersConfig,
    FiscalParameters,
    InstitutionDef,
    InstitutionsCatalog,
    ReportLayout,
    TransferConfig,
    TransferInternalConfig,
)

_DEPRECATION_NOTICE = (
    "FileConfigStore reads from disk and is deprecated. It will be removed in "
    "Sprint A7.5 (CONFIG_CUTOVER_PLAN.md §5.5). Use DBConfigStore in production."
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class FileConfigStore:
    """Lê config/*.json + config/*.yaml — adapter legado (singleton lazy idempotente)."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        warnings.warn(_DEPRECATION_NOTICE, DeprecationWarning, stacklevel=2)
        self._config_dir = config_dir or (_PROJECT_ROOT / "config")
        self._cache: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Per-workspace methods — workspace_id é ignorado: arquivo global é único
    # ------------------------------------------------------------------

    def get_categorization(self, workspace_id: str) -> Optional[CategorizationConfig]:
        """Lê ``categorization.json`` — workspace_id ignorado (arquivo global)."""
        del workspace_id
        data = self._load_json("categorization.json")
        if not data:
            return None
        return _parse_categorization(data)

    def get_family_members(self, workspace_id: str) -> Optional[FamilyMembersConfig]:
        """Lê ``family_members.json`` — workspace_id ignorado."""
        del workspace_id
        data = self._load_json("family_members.json")
        if not data:
            return None
        return _parse_family_members(data)

    def get_institutions(self) -> InstitutionsCatalog:
        """Lê ``institutions.json`` — sempre global."""
        data = self._load_json("institutions.json") or {}
        return _parse_institutions(data)

    def get_report_layout(self, workspace_id: str) -> Optional[ReportLayout]:
        """Lê ``report_layout.yaml`` — workspace_id ignorado."""
        del workspace_id
        data = self._load_yaml("report_layout.yaml")
        if not data:
            return None
        return _parse_report_layout(data)

    def get_transfer_config(self, workspace_id: str) -> Optional[TransferConfig]:
        """Lê o bloco ``transferencias_internas`` de ``family_members.json``."""
        del workspace_id
        data = self._load_json("family_members.json")
        if not data:
            return None
        block = data.get("transferencias_internas")
        if not isinstance(block, dict):
            return None
        return TransferConfig(config=_parse_transfers(block))

    # ------------------------------------------------------------------
    # Stubs — ADR-135 / Sprint A7.2b implementa
    # ------------------------------------------------------------------

    def get_fiscal_for_period(self, period_start: date, period_end: date) -> FiscalParameters:
        """Stub A7.2b — FileConfigStore não suporta vigência (ADR-135)."""
        del period_start, period_end
        raise NotImplementedError(
            "get_fiscal_for_period is populated in Sprint A7.2b (ADR-135). "
            "Use DBConfigStore once fiscal_parameters table is seeded."
        )

    def get_market_rate(self, pair: str, observed_at: date) -> Decimal:
        """Stub A7.2b — FileConfigStore não suporta vigência de câmbio (ADR-135)."""
        del pair, observed_at
        raise NotImplementedError(
            "get_market_rate is populated in Sprint A7.2b (ADR-135). "
            "Use DBConfigStore once market_rates table is seeded."
        )

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _load_json(self, name: str) -> dict[str, Any]:
        if name in self._cache:
            return self._cache[name]
        path = self._config_dir / name
        if not path.exists():
            self._cache[name] = {}
            return {}
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        self._cache[name] = data
        return data

    def _load_yaml(self, name: str) -> dict[str, Any]:
        if name in self._cache:
            return self._cache[name]
        path = self._config_dir / name
        if not path.exists():
            self._cache[name] = {}
            return {}
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        self._cache[name] = data
        return data


# ----------------------------------------------------------------------
# Parsers — JSON/YAML dict → dataclass tipada
# ----------------------------------------------------------------------


def _parse_categorization(data: Mapping[str, Any]) -> CategorizationConfig:
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


def _parse_family_members(data: Mapping[str, Any]) -> FamilyMembersConfig:
    family = data.get("familia") or {}
    surname = family.get("sobrenome") if isinstance(family, dict) else None
    members = _build_members(data.get("membros"))
    bank_to_member = _build_bank_to_member(data.get("banco_membro"))
    transfers_block = data.get("transferencias_internas")
    transfers = _parse_transfers(transfers_block) if isinstance(transfers_block, dict) else None
    return FamilyMembersConfig(
        members=members,
        bank_to_member=bank_to_member,
        family_surname=str(surname) if surname else None,
        transfers=transfers,
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
    """Mantém em ``extra`` os campos não absorvidos pelos campos tipados de ``FamilyMemberRecord``."""
    drop = {"nome_completo", "nome_curto", "papel", "cpf", "data_nascimento"}
    return {k: v for k, v in raw.items() if k not in drop}


def _parse_transfers(block: Mapping[str, Any]) -> TransferInternalConfig:
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


def _parse_institutions(data: Mapping[str, Any]) -> InstitutionsCatalog:
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


def _parse_report_layout(data: Mapping[str, Any]) -> ReportLayout:
    sections_raw = data.get("sections") or ()
    sections = (
        tuple(dict(s) for s in sections_raw if isinstance(s, dict))
        if isinstance(sections_raw, list)
        else ()
    )
    metadata = {k: v for k, v in data.items() if k != "sections"}
    return ReportLayout(sections=sections, metadata=metadata)
