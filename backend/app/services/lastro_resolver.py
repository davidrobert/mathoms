"""`lastro_resolver` — resolução pura de ``lastro_moeda`` por ativo (ADR-224 §5; priority override > ticker > cnpj > keyword > fallback por asset_class)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CatalogEntry:
    """Snapshot imutável de uma row de ``asset_catalog``."""

    ticker: Optional[str]
    cnpj: Optional[str]
    match_keyword: Optional[str]
    asset_class: str
    lastro_moeda: str


@dataclass(frozen=True)
class OverrideEntry:
    """Snapshot imutável de ``workspace_asset_overrides``."""

    match_kind: str  # 'ticker' | 'cnpj' | 'description'
    asset_match_key: str
    lastro_moeda: str


@dataclass(frozen=True)
class AssetQuery:
    """Input para resolver: ativo a classificar (do payload E5)."""

    ticker: Optional[str] = None
    cnpj: Optional[str] = None
    descricao: Optional[str] = None
    asset_class_fallback: str = "Outros"


_DEFAULT_FALLBACK_BY_CLASS = {
    "Internacional": "USD",
    "Cripto": "USD",
    "Caixa": "BRL",
    "FIIs": "BRL",
    "Renda Fixa": "BRL",
    "Previdência": "BRL",
    "Ações BR": "BRL",
    "Fundos": "BRL",
    "Imóveis Investimento": "BRL",
}


def _norm(s: Optional[str] = None) -> str:
    return (s or "").strip().lower()


def _fallback_by_class(asset_class: str) -> str:
    return _DEFAULT_FALLBACK_BY_CLASS.get(asset_class, "BRL")


def _override_matches(query: AssetQuery, override: OverrideEntry) -> bool:
    key = _norm(override.asset_match_key)
    if override.match_kind == "ticker" and query.ticker:
        return key == _norm(query.ticker)
    if override.match_kind == "cnpj" and query.cnpj:
        return key == _norm(query.cnpj)
    if override.match_kind == "description" and query.descricao:
        return key in _norm(query.descricao)
    return False


def _match_override(query: AssetQuery, overrides: list[OverrideEntry]) -> Optional[OverrideEntry]:
    for override in overrides:
        if _override_matches(query, override):
            return override
    return None


def _match_catalog(query: AssetQuery, catalog: list[CatalogEntry]) -> Optional[CatalogEntry]:
    if query.ticker:
        ticker_n = _norm(query.ticker)
        for entry in catalog:
            if entry.ticker and _norm(entry.ticker) == ticker_n:
                return entry
    if query.cnpj:
        cnpj_n = _norm(query.cnpj)
        for entry in catalog:
            if entry.cnpj and _norm(entry.cnpj) == cnpj_n:
                return entry
    if query.descricao:
        desc_n = _norm(query.descricao)
        for entry in catalog:
            if entry.match_keyword and _norm(entry.match_keyword) in desc_n:
                return entry
    return None


def resolve_lastro_moeda(
    query: AssetQuery,
    *,
    catalog: list[CatalogEntry],
    overrides: list[OverrideEntry],
) -> str:
    """Resolve ``lastro_moeda`` segundo priority: override > catalog > fallback por classe."""
    moeda, _source = resolve_lastro_with_source(query, catalog=catalog, overrides=overrides)
    return moeda


def resolve_lastro_with_source(
    query: AssetQuery,
    *,
    catalog: list[CatalogEntry],
    overrides: list[OverrideEntry],
) -> tuple[str, str]:
    """Idem a ``resolve_lastro_moeda`` mas retorna `(moeda, source)`. source ∈ {'override','catalog','fallback_classe'}."""
    override = _match_override(query, overrides)
    if override is not None:
        return override.lastro_moeda, "override"
    entry = _match_catalog(query, catalog)
    if entry is not None:
        return entry.lastro_moeda, "catalog"
    return _fallback_by_class(query.asset_class_fallback), "fallback_classe"
