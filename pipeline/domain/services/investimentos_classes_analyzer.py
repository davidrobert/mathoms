"""InvestimentosClassesAnalyzer — distribuição da carteira pelas 10 classes canônicas (ADR-193)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from pipeline.domain.services.asset_classifier import (
    BUCKETS,
    OUTROS_EXCESSIVO_THRESHOLD_PCT,
    OutrosExcessivoWarning,
    classify_asset_outcome,
    merge_asset_keywords,
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


# Classe de imóveis físicos (ADR-193) — fora da base "carteira financeira" (A37.l9).
_CLASSE_IMOVEIS_INVESTIMENTO = "Imóveis Investimento"


# =============================================================================
# Config
# =============================================================================


def _build_tabela(
    classes: dict[str, float], denominador_investido: float, denominador_financeiro: float
) -> tuple["ClasseAtivo", ...]:
    out: list[ClasseAtivo] = []
    for cat, v in sorted(classes.items(), key=lambda x: x[1], reverse=True):
        if v > 0:
            pct = (v / denominador_investido) * 100 if denominador_investido > 0 else 0.0
            out.append(
                ClasseAtivo(
                    categoria=cat,
                    valor=v,
                    pct=pct,
                    pct_carteira_financeira=_pct_carteira_financeira(
                        cat, v, denominador_financeiro
                    ),
                )
            )
    return tuple(out)


def _pct_carteira_financeira(
    categoria: str, numerador: float, denominador_financeiro: float
) -> float | None:
    """Peso da classe sobre a carteira financeira (A37.l9): denominador exclui
    imóveis físicos — peso de classe financeira nunca é medido sobre base que
    inclui imóvel (subestimaria toda classe financeira sistematicamente).
    ``None`` para a própria classe de imóveis (fora da base) e carteira vazia."""
    if categoria == _CLASSE_IMOVEIS_INVESTIMENTO or denominador_financeiro <= 0:
        return None
    return (numerador / denominador_financeiro) * 100


def _merge_keywords(scoring: dict | None) -> dict[str, tuple[str, ...]]:
    return merge_asset_keywords(scoring)


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
    # Base "total investido" (financeiro + imóveis de investimento) — ADR-209 absoluto.
    pct: float
    # Base "carteira financeira" (total - imóveis físicos); None fora da base (A37.l9).
    pct_carteira_financeira: float | None = None

    def to_dict(self) -> dict:
        return {
            "categoria": self.categoria,
            "valor": round(self.valor, 2),
            "pct": round(self.pct, 2),
            "pct_carteira_financeira": (
                round(self.pct_carteira_financeira, 2)
                if self.pct_carteira_financeira is not None
                else None
            ),
        }


@dataclass(frozen=True)
class InvestimentosClassesAnalysis:
    tabela_classes: tuple[ClasseAtivo, ...]
    total: float
    # Decomposição por construção (A37.l9): total = financeiro + imóveis físicos.
    # Decimal em memória (ADR-090); wire legado emite JSON number (float).
    total_financeiro: Decimal = Decimal("0")
    total_imoveis_investimento: Decimal = Decimal("0")
    warnings: tuple[OutrosExcessivoWarning, ...] = ()
    # Soma dos investimentos cuja classe NENHUM degrau decidiu ([[ADR-396]]).
    nao_classificado_brl: Decimal = Decimal("0")

    @property
    def nao_classificado_pct(self) -> float:
        """Fração não classificada da CARTEIRA FINANCEIRA (mesma base de
        ``pct_carteira_financeira``, A37.l9) — imóvel é classificado pela origem
        e nunca depende de keyword, então incluí-lo diluiria a incerteza."""
        if self.total_financeiro <= 0:
            return 0.0
        return float(self.nao_classificado_brl / self.total_financeiro) * 100

    def to_legacy_dict(self) -> dict:
        return {
            "tabela_classes": [c.to_dict() for c in self.tabela_classes],
            "total": round(self.total, 2),
            "total_financeiro": float(round(self.total_financeiro, 2)),
            "total_imoveis_investimento": float(round(self.total_imoveis_investimento, 2)),
            "nao_classificado_pct": round(self.nao_classificado_pct, 2),
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
        nao_classificado = self._acumular(bens_por_membro or [], classes)
        total = sum(classes.values())
        total_imoveis = classes.get(_CLASSE_IMOVEIS_INVESTIMENTO, 0.0)
        total_financeiro = total - total_imoveis
        return InvestimentosClassesAnalysis(
            tabela_classes=_build_tabela(classes, total, total_financeiro),
            total=total,
            total_financeiro=Decimal(str(total_financeiro)),
            total_imoveis_investimento=Decimal(str(total_imoveis)),
            warnings=self._build_warnings(classes, total),
            nao_classificado_brl=Decimal(str(nao_classificado)),
        )

    # -- Helpers internos --

    def _acumular(self, bens_por_membro: list, classes: dict[str, float]) -> float:
        """Soma todos os membros nos baldes; devolve o total não classificado."""
        nao_classificado = 0.0
        for bens in bens_por_membro:
            if not isinstance(bens, dict):
                continue
            nao_classificado += self._classify_investments(bens, classes)
            self._add_top_level_cripto(bens, classes)
            self._add_contas_bancarias_scalar(bens, classes)
            self._add_imoveis_investimento(bens, classes)
        return nao_classificado

    def _classify_investments(self, bens: dict[str, Any], classes: dict[str, float]) -> float:
        """Soma cada investimento no seu balde; devolve o total não classificado."""
        nao_classificado = 0.0
        for inv in bens.get("investimentos", []) or []:
            if not isinstance(inv, dict):
                continue
            tipo = str(inv.get("tipo") or "")
            descricao = str(inv.get("descricao") or inv.get("description") or "")
            valor = _safe_float(inv.get("valor", inv.get("valor_31_12_ano_base", 0)))
            if valor <= 0:
                continue
            resultado = classify_asset_outcome(
                tipo, descricao, keywords=self._config.keywords_por_classe
            )
            classes[resultado.classe] = classes.get(resultado.classe, 0.0) + valor
            if resultado.nao_classificado:
                nao_classificado += valor
        return nao_classificado

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
            classes[_CLASSE_IMOVEIS_INVESTIMENTO] += valor

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
