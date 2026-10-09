"""InvestimentosClassesAnalyzer — distribuição da carteira pelas 10 classes canônicas (ADR-193)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping

from pipeline.domain.services.asset_classifier import (
    BUCKETS,
    OUTROS_EXCESSIVO_THRESHOLD_PCT,
    OutrosExcessivoWarning,
    classify_asset_outcome,
    merge_asset_keywords,
)
from pipeline.domain.services.imovel_na_carteira import (
    CLASSES_IMOVEL_FISICO,
    classe_do_imovel_na_carteira,
)
from pipeline.domain.services.patrimonio_types import imovel_valor
from pipeline.domain.services.posicao_identity import (
    locator_da_posicao,
    safe_float,
    valor_da_posicao,
)

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
    if categoria in CLASSES_IMOVEL_FISICO or denominador_financeiro <= 0:
        return None
    return (numerador / denominador_financeiro) * 100


def _merge_keywords(scoring: dict | None) -> dict[str, tuple[str, ...]]:
    return merge_asset_keywords(scoring)


@dataclass(frozen=True)
class InvestimentosClassesConfig:
    """Keywords por classe + overrides de classificação de imóvel (ADR-215 §1)."""

    keywords_por_classe: dict[str, tuple[str, ...]] = field(default_factory=dict)
    property_classification_overrides: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_configs(
        cls,
        *,
        scoring: dict | None = None,
        property_classification_overrides: Mapping[str, str] | None = None,
    ) -> "InvestimentosClassesConfig":
        return cls(
            keywords_por_classe=_merge_keywords(scoring),
            property_classification_overrides=dict(property_classification_overrides or {}),
        )


# =============================================================================
# Result
# =============================================================================


# Item, não agregado: a migração entre baldes preserva Σ, então o percentual da
# catch-all é cego POR CONSTRUÇÃO ao caso do §r7 ([[ADR-406]]).
@dataclass(frozen=True)
class PosicaoNaoClassificada:
    """Posição cuja classe nenhum degrau decidiu — locator PII-free + valor."""

    locator: str
    valor: Decimal
    autoridade: str

    def to_dict(self, denominador: Decimal) -> dict:
        pct = float(self.valor / denominador) * 100 if denominador > 0 else 0.0
        return {
            "locator": self.locator,
            "pct_carteira_financeira": round(pct, 4),
            "autoridade": self.autoridade,
        }


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
    # Soma dos investimentos cuja classe NENHUM degrau decidiu ([[ADR-400]]).
    nao_classificado_brl: Decimal = Decimal("0")
    # As posições por trás dessa soma ([[ADR-406]]) — o agregado sozinho não
    # distingue um item grande migrado de mil cortes pequenos.
    nao_classificado_itens: tuple[PosicaoNaoClassificada, ...] = ()

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
            "nao_classificado_itens": [
                i.to_dict(self.total_financeiro) for i in self.nao_classificado_itens
            ],
        }


# =============================================================================
# Service
# =============================================================================


def _posicao_sem_classe(inv: dict, valor: Decimal, resultado) -> PosicaoNaoClassificada:
    return PosicaoNaoClassificada(
        locator=locator_da_posicao(inv),
        valor=valor,
        autoridade=resultado.autoridade.value,
    )


class InvestimentosClassesAnalyzer:
    """Classifica investimentos da família nas 10 classes canônicas (ADR-193)."""

    CATEGORIES = BUCKETS

    def __init__(self, config: InvestimentosClassesConfig | None = None) -> None:
        self._config = config or InvestimentosClassesConfig.from_configs()

    def analyze(self, bens_por_membro: list[dict[str, Any]]) -> InvestimentosClassesAnalysis:
        classes = {cat: 0.0 for cat in self.CATEGORIES}
        itens = self._acumular(bens_por_membro or [], classes)
        total = sum(classes.values())
        total_imoveis = sum(classes.get(c, 0.0) for c in CLASSES_IMOVEL_FISICO)
        total_financeiro = total - total_imoveis
        return InvestimentosClassesAnalysis(
            tabela_classes=_build_tabela(classes, total, total_financeiro),
            total=total,
            total_financeiro=Decimal(str(total_financeiro)),
            total_imoveis_investimento=Decimal(str(total_imoveis)),
            warnings=self._build_warnings(classes, total),
            nao_classificado_brl=sum((i.valor for i in itens), Decimal("0")),
            nao_classificado_itens=tuple(itens),
        )

    # -- Helpers internos --

    def _acumular(
        self, bens_por_membro: list, classes: dict[str, float]
    ) -> list[PosicaoNaoClassificada]:
        """Soma todos os membros nos baldes; devolve as posições sem classe."""
        itens: list[PosicaoNaoClassificada] = []
        for bens in bens_por_membro:
            if not isinstance(bens, dict):
                continue
            itens.extend(self._classify_investments(bens, classes))
            self._add_top_level_cripto(bens, classes)
            self._add_contas_bancarias_scalar(bens, classes)
            self._add_imoveis(bens, classes)
        return itens

    def _classify_investments(
        self, bens: dict[str, Any], classes: dict[str, float]
    ) -> list[PosicaoNaoClassificada]:
        """Soma cada investimento no seu balde; devolve as posições sem classe."""
        itens: list[PosicaoNaoClassificada] = []
        for inv in bens.get("investimentos", []) or []:
            if not isinstance(inv, dict):
                continue
            valor = valor_da_posicao(inv)
            if valor <= 0:
                continue
            resultado = classify_asset_outcome(
                str(inv.get("tipo") or ""),
                str(inv.get("descricao") or inv.get("description") or ""),
                keywords=self._config.keywords_por_classe,
            )
            classes[resultado.classe] = classes.get(resultado.classe, 0.0) + float(valor)
            if resultado.nao_classificado:
                itens.append(_posicao_sem_classe(inv, valor, resultado))
        return itens

    def _add_top_level_cripto(self, bens: dict[str, Any], classes: dict[str, float]) -> None:
        classes["Cripto"] += safe_float(bens.get("criptos", 0))

    def _add_contas_bancarias_scalar(self, bens: dict[str, Any], classes: dict[str, float]) -> None:
        # `Contas Bancárias` (legado) → `Caixa` (ADR-193). Lista de contas é tratada como investimento.
        contas = bens.get("contas_bancarias")
        if isinstance(contas, (int, float)):
            classes["Caixa"] += safe_float(contas)

    def _add_imoveis(self, bens: dict[str, Any], classes: dict[str, float]) -> None:
        overrides = self._config.property_classification_overrides
        for imovel in bens.get("imoveis", []) or []:
            if not isinstance(imovel, dict):
                continue
            # O mesmo valor que o patrimônio soma ([[ADR-431]]): não apurado fica de fora.
            valor = imovel_valor(imovel)
            classe = classe_do_imovel_na_carteira(imovel, overrides)
            if valor <= 0 or classe is None:
                continue
            classes[classe] = classes.get(classe, 0.0) + valor

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
