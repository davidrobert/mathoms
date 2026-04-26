"""``FileConfigStore`` — adapter legado lê ``PROJECT_DIR / config`` (deprecated, A7.5)."""

from __future__ import annotations

import json
import warnings
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

import yaml

from pipeline.adapters.config_parsers import (
    parse_categorization,
    parse_family_members,
    parse_institutions,
    parse_report_layout,
    parse_transfers,
)
from pipeline.domain.types.config import (
    CategorizationConfig,
    FamilyMembersConfig,
    FiscalParameters,
    InstitutionsCatalog,
    ReportLayout,
    TransferConfig,
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
        return parse_categorization(data)

    def get_family_members(self, workspace_id: str) -> Optional[FamilyMembersConfig]:
        """Lê ``family_members.json`` — workspace_id ignorado."""
        del workspace_id
        data = self._load_json("family_members.json")
        if not data:
            return None
        return parse_family_members(data)

    def get_institutions(self) -> InstitutionsCatalog:
        """Lê ``institutions.json`` — sempre global."""
        data = self._load_json("institutions.json") or {}
        return parse_institutions(data)

    def get_report_layout(self, workspace_id: str) -> Optional[ReportLayout]:
        """Lê ``report_layout.yaml`` — workspace_id ignorado."""
        del workspace_id
        data = self._load_yaml("report_layout.yaml")
        if not data:
            return None
        return parse_report_layout(data)

    def get_transfer_config(self, workspace_id: str) -> Optional[TransferConfig]:
        """Lê o bloco ``transferencias_internas`` de ``family_members.json``."""
        del workspace_id
        data = self._load_json("family_members.json")
        if not data:
            return None
        block = data.get("transferencias_internas")
        if not isinstance(block, dict):
            return None
        return TransferConfig(config=parse_transfers(block))

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
