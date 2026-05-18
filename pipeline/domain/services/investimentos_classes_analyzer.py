"""InvestimentosClassesAnalyzer — distribuição da carteira pelas 10 classes canônicas (ADR-193)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pipeline.domain.services.asset_classifier import (
    BUCKETS,
    OUTROS_EXCESSIVO_THRESHOLD_PCT,
    OutrosExcessivoWarning,
    classify_asset,
    default_keywords,
)


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.replace(",", "."))
        except ValueError:
            return 0.0
    return 0.0


# =============================================================================
# Config
# =============================================================================


def _build_tabela(classes: dict[str, float], total: float) -> tuple["ClasseAtivo", ...]:
    out: list[ClasseAtivo] = []
    for cat, valor in sorted(classes.items(), key=lambda x: x[1], reverse=True):
        if valor > 0:
            pct = (valor / total) * 100 if total > 0 else 0.0
            out.append(ClasseAtivo(categoria=cat, valor=valor, pct=pct))
    return tuple(out)


def _merge_keywords(scoring: dict | None) -> dict[str, tuple[str, ...]]:
    acl = (scoring or {}).get("asset_class_keywords") or {}
    merged: dict[str, tuple[str, ...]] = {}
    for classe, ks in default_keywords().items():
        override = acl.get(classe)
        merged[classe] = tuple(str(k).lower() for k in override) if override else ks
    # Forward-compat: classe nova em scoring.json não precisa estar em defaults.
    for classe, override in acl.items():
        if classe == "_comment" or classe in merged:
            continue
        if isinstance(override, list):
            merged[classe] = tuple(str(k).lower() for k in override)
    return merged


@dataclass(frozen=True)
class InvestimentosClassesConfig:
    """Keywords por classe + set de property_ids classificados como residência (ADR-215 §1)."""

    keywords_por_classe: dict[str, tuple[str, ...]] = field(default_factory=dict)
    residencia_property_ids: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_configs(
        cls,
        *,
        scoring: dict | None = None,
        residencia_property_ids: frozenset[str] = frozenset(),
    ) -> "InvestimentosClassesConfig":
        return cls(
            keywords_por_classe=_merge_keywords(scoring),
            residencia_property_ids=residencia_property_ids,
        )


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class ClasseAtivo:
    categoria: str
    valor: float
    pct: float

    def to_dict(self) -> dict:
        return {
            "categoria": self.categoria,
            "valor": round(self.valor, 2),
            "pct": round(self.pct, 2),
        }


@dataclass(frozen=True)
class InvestimentosClassesAnalysis:
    tabela_classes: tuple[ClasseAtivo, ...]
    total: float
    warnings: tuple[OutrosExcessivoWarning, ...] = ()

    def to_legacy_dict(self) -> dict:
        return {
            "tabela_classes": [c.to_dict() for c in self.tabela_classes],
            "total": round(self.total, 2),
        }


# =============================================================================
# Service
# =============================================================================


class InvestimentosClassesAnalyzer:
    """Classifica investimentos da família nas 10 classes canônicas (ADR-193)."""

    CATEGORIES = BUCKETS

    def __init__(self, config: InvestimentosClassesConfig | None = None) -> None:
        self._config = config or InvestimentosClassesConfig.from_configs()

    def analyze(self, bens_por_membro: list[dict[str, Any]]) -> InvestimentosClassesAnalysis:
        classes = {cat: 0.0 for cat in self.CATEGORIES}
        for bens in bens_por_membro or []:
            if not isinstance(bens, dict):
                continue
            self._classify_investments(bens, classes)
            self._add_top_level_cripto(bens, classes)
            self._add_contas_bancarias_scalar(bens, classes)
            self._add_imoveis_investimento(bens, classes)
        total = sum(classes.values())
        return InvestimentosClassesAnalysis(
            tabela_classes=_build_tabela(classes, total),
            total=total,
            warnings=self._build_warnings(classes, total),
        )

    # -- Helpers internos --

    def _classify_investments(self, bens: dict[str, Any], classes: dict[str, float]) -> None:
        for inv in bens.get("investimentos", []) or []:
            if not isinstance(inv, dict):
                continue
            tipo = str(inv.get("tipo") or "")
            descricao = str(inv.get("descricao") or inv.get("description") or "")
            instituicao = str(inv.get("instituicao") or "")
            valor = _safe_float(inv.get("valor", inv.get("valor_31_12_ano_base", 0)))
            if valor <= 0:
                continue
            bucket = classify_asset(
                tipo, descricao, instituicao, keywords=self._config.keywords_por_classe
            )
            classes[bucket] = classes.get(bucket, 0.0) + valor

    def _add_top_level_cripto(self, bens: dict[str, Any], classes: dict[str, float]) -> None:
        classes["Cripto"] += _safe_float(bens.get("criptos", 0))

    def _add_contas_bancarias_scalar(self, bens: dict[str, Any], classes: dict[str, float]) -> None:
        # `Contas Bancárias` (legado) → `Caixa` (ADR-193). Lista de contas é tratada como investimento.
        contas = bens.get("contas_bancarias")
        if isinstance(contas, (int, float)):
            classes["Caixa"] += _safe_float(contas)

    def _add_imoveis_investimento(self, bens: dict[str, Any], classes: dict[str, float]) -> None:
        residencia_ids = self._config.residencia_property_ids
        for imovel in bens.get("imoveis", []) or []:
            if not isinstance(imovel, dict):
                continue
            valor = _safe_float(
                imovel.get("valor_31_12_ano_base")
                or imovel.get("valor_irpf")
                or imovel.get("valor", 0)
            )
            if valor <= 0:
                continue
            pid = imovel.get("property_id")
            if isinstance(pid, str) and pid in residencia_ids:
                continue
            classes["Imóveis Investimento"] += valor

    def _build_warnings(
        self, classes: dict[str, float], total: float
    ) -> tuple[OutrosExcessivoWarning, ...]:
        if total <= 0:
            return ()
        outros = classes.get("Outros", 0.0)
        pct = (outros / total) * 100
        if pct > OUTROS_EXCESSIVO_THRESHOLD_PCT:
            return (
                OutrosExcessivoWarning(
                    pct_outros=pct, threshold_pct=OUTROS_EXCESSIVO_THRESHOLD_PCT
                ),
            )
        return ()
