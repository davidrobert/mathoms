"""InvestimentosClassesAnalyzer — classificação por classe de ativo (Sessão A5b).

Extrai ``analyze_investimentos_classes`` (e5_analyze.py:1516) em domain
service puro. Classifica investimentos do baseline em 6 classes (Ações,
Renda Fixa, Cripto, Contas Bancárias, Imóveis Investimento, Outros) usando
keywords configuráveis.

Composição puramente sobre ``MemberPatrimonio`` (A3c) não é suficiente aqui
— o legado precisa da lista bruta ``investimentos[].tipo`` + campos
top-level (``criptos``, ``contas_bancarias`` numérico, ``imoveis``) para
fazer a classificação. Por isso, este service recebe os dicts "bens" dos
membros já resolvidos.

Função pura. Recebe :class:`InvestimentosClassesConfig` tipada com:
- ``keywords_por_classe``: dict ``{classe: [keyword, ...]}``
- ``residencia_keyword``: para excluir a residência principal dos imóveis
  (alinhado com :class:`MemberAnalyzer`)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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


_DEFAULT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Ações": ("acoes", "ações", "itsa", "brkm", "petr", "etf", "ivvb"),
    "Renda Fixa": (
        "renda fixa", "cdb", "rdb", "lci", "lca", "tesouro",
        "debenture", "certificado de deposito",
    ),
    "Cripto": ("cripto", "bitcoin", "ethereum", "binance"),
    "Contas Bancárias": ("banco", "picpay", "nubank", "saldo", "conta"),
}


@dataclass(frozen=True)
class InvestimentosClassesConfig:
    """Keywords por classe de ativo + keyword de residência principal.

    Fonte no legado:
    - ``asset_class_keywords`` ← ``scoring.json::asset_class_keywords``
    - ``residencia_keyword`` ← ``family_members.json::membros[titular].residencia_principal_keyword``
    """

    keywords_por_classe: dict[str, tuple[str, ...]] = field(default_factory=dict)
    residencia_keyword: str = ""

    @classmethod
    def from_configs(
        cls,
        *,
        scoring: dict | None = None,
        residencia_keyword: str = "",
    ) -> "InvestimentosClassesConfig":
        acl = (scoring or {}).get("asset_class_keywords") or {}
        merged: dict[str, tuple[str, ...]] = {}
        for classe, defaults in _DEFAULT_KEYWORDS.items():
            override = acl.get(classe)
            if override:
                merged[classe] = tuple(str(k).lower() for k in override)
            else:
                merged[classe] = defaults
        return cls(
            keywords_por_classe=merged,
            residencia_keyword=(residencia_keyword or "").lower().strip(),
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

    def to_legacy_dict(self) -> dict:
        return {
            "tabela_classes": [c.to_dict() for c in self.tabela_classes],
            "total": round(self.total, 2),
        }


# =============================================================================
# Service
# =============================================================================


class InvestimentosClassesAnalyzer:
    """Classifica investimentos da família em 6 classes de ativo.

    Recebe lista de dicts ``bens`` por membro (após resolver via
    ``_resolve_members`` + ``_get_bens`` no call-site). Retorna distribuição
    por classe, já agrupada e com % calculado.
    """

    # Classes são as chaves de ``_DEFAULT_KEYWORDS`` + "Imóveis Investimento" +
    # "Outros" (fallback).
    CATEGORIES = (
        "Renda Fixa",
        "Ações",
        "Imóveis Investimento",
        "Cripto",
        "Contas Bancárias",
        "Outros",
    )

    def __init__(self, config: InvestimentosClassesConfig | None = None) -> None:
        self._config = config or InvestimentosClassesConfig.from_configs()

    def analyze(
        self, bens_por_membro: list[dict[str, Any]]
    ) -> InvestimentosClassesAnalysis:
        classes = {cat: 0.0 for cat in self.CATEGORIES}

        for bens in bens_por_membro or []:
            if not isinstance(bens, dict):
                continue
            self._classify_investments(bens, classes)
            self._add_top_level_cripto(bens, classes)
            self._add_contas_bancarias_scalar(bens, classes)
            self._add_imoveis_investimento(bens, classes)

        total = sum(classes.values())
        tabela: list[ClasseAtivo] = []
        for cat, valor in sorted(classes.items(), key=lambda x: x[1], reverse=True):
            if valor > 0:
                pct = (valor / total) * 100 if total > 0 else 0.0
                tabela.append(ClasseAtivo(categoria=cat, valor=valor, pct=pct))

        return InvestimentosClassesAnalysis(
            tabela_classes=tuple(tabela),
            total=total,
        )

    # -- Helpers internos --

    def _classify_investments(
        self, bens: dict[str, Any], classes: dict[str, float]
    ) -> None:
        for inv in bens.get("investimentos", []) or []:
            if not isinstance(inv, dict):
                continue
            tipo = str(inv.get("tipo") or "")
            valor = _safe_float(
                inv.get("valor", inv.get("valor_31_12_ano_base", 0))
            )
            if valor <= 0:
                continue
            self._assign_to_class(tipo, valor, classes)

    def _assign_to_class(
        self, tipo: str, valor: float, classes: dict[str, float]
    ) -> None:
        tipo_lower = tipo.lower()
        for classe in ("Ações", "Renda Fixa", "Cripto", "Contas Bancárias"):
            keywords = self._config.keywords_por_classe.get(classe, ())
            if any(kw in tipo_lower for kw in keywords):
                classes[classe] += valor
                return
        classes["Outros"] += valor

    def _add_top_level_cripto(
        self, bens: dict[str, Any], classes: dict[str, float]
    ) -> None:
        classes["Cripto"] += _safe_float(bens.get("criptos", 0))

    def _add_contas_bancarias_scalar(
        self, bens: dict[str, Any], classes: dict[str, float]
    ) -> None:
        """Legado aceita ``contas_bancarias`` como escalar (soma direta) ou
        lista (ignora aqui — tratado como investimento). Paridade exata."""
        contas = bens.get("contas_bancarias")
        if isinstance(contas, (int, float)):
            classes["Contas Bancárias"] += _safe_float(contas)

    def _add_imoveis_investimento(
        self, bens: dict[str, Any], classes: dict[str, float]
    ) -> None:
        """Imóveis não-residência entram em ``Imóveis Investimento``."""
        kw = self._config.residencia_keyword
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
            desc = self._imovel_desc(imovel)
            if kw and kw in desc:
                continue  # Residência — não é investimento.
            classes["Imóveis Investimento"] += valor

    @staticmethod
    def _imovel_desc(imovel: dict) -> str:
        desc = imovel.get("description") or imovel.get("descricao") or ""
        if not desc:
            desc = imovel.get("endereco") or ""
        if not desc:
            dc = imovel.get("dados_completos")
            if isinstance(dc, dict):
                desc = dc.get("imovel", "") or ""
        return str(desc).lower()
