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
from pipeline.adapters.fiscal_parsers import legacy_json_to_fiscal
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

_LEGACY_PAIR_KEYS = {
    "USD/BRL": "cambio_usd_brl",
    "EUR/BRL": "cambio_eur_brl",
}


def _legacy_pair_key(pair: str) -> str:
    """Mapeia ``"USD/BRL"`` → ``"cambio_usd_brl"`` (chaves do JSON legado)."""
    return _LEGACY_PAIR_KEYS.get(pair, pair.lower().replace("/", "_"))


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
        """Bridge legado: lê ``parametros_fiscais.json`` ignorando vigência fina (A7.2b)."""
        del period_end  # FileConfigStore não suporta vigência mid-year — usa year do start
        data = self._load_json("parametros_fiscais.json") or {}
        if not data:
            raise FileNotFoundError(
                "config/parametros_fiscais.json missing — FileConfigStore bridge "
                "for fiscal data requires the file. Migrate to DBConfigStore (A7.2b)."
            )
        return legacy_json_to_fiscal(data, year=period_start.year)

    def get_market_rate(self, pair: str, observed_at: date) -> Decimal:
        """Bridge legado: lê ``taxas.json`` ignorando ``observed_at`` (cotação corrente única)."""
        del observed_at  # JSON tem só uma cotação corrente — sem histórico
        data = self._load_json("taxas.json") or {}
        if not data:
            raise FileNotFoundError(
                "config/taxas.json missing — FileConfigStore bridge for market data "
                "requires the file. Migrate to DBConfigStore (A7.2b)."
            )
        key = _legacy_pair_key(pair)
        if key not in data:
            raise KeyError(
                f"Pair {pair!r} not in legacy taxas.json (key={key!r}). "
                "Add via DBConfigStore + market_rates table (A7.2b)."
            )
        return Decimal(str(data[key]))

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
