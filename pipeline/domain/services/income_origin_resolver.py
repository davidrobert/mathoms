"""IncomeOriginResolver — resolve "origem" para receitas (Sessão A3a · Fase 7 foundation).

Extrai ``get_pj_origin`` (e4_categorize.py:196), ``get_clt_origin``
(e4_categorize.py:207) e o ``if/elif`` de classificação de origem em
``process_transactions`` (e4_categorize.py:660-679) num domain service puro.

Recebe :class:`IncomeOriginConfig` (R9/ISP) — não acessa configs globais.

Cobertura **mínima**: PJ + CLT + categorias com mapeamento estático
(`receita_aluguel → "Aluguéis"`, etc.). A integração no `main()` do E4 fica
para sessão dedicada quando o Caminho B do E4 entrar em jogo.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

# =============================================================================
# Helper de normalização (paridade com `normalize_text` de e4_categorize)
# =============================================================================


def _normalize_text(text: str) -> str:
    """Uppercase + strip de acentos + colapsa whitespace (paridade com
    ``e4_categorize.normalize_text``).
    """
    if not text:
        return ""
    text = str(text).upper().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


# =============================================================================
# Config
# =============================================================================


# Mapeamento estático categoria → origem (paridade com `process_transactions`
# linhas 660-679; `receita_pj`/`receita_clt` são resolvidos dinamicamente via
# os mappings PJ/CLT abaixo, todos os demais usam a tabela estática).
_DEFAULT_STATIC_ORIGINS: dict[str, str] = {
    "receita_aluguel": "Aluguéis",
    "receita_investimento": "Rendimentos Financeiros",
    "receita_resgate": "Resgates",
    "receita_venda_ativo": "Venda de Ativo",
    "receita_restituicao": "Restituições",
    "receita_fgts": "FGTS",
    "outras_receitas": "Outras Receitas",
}


@dataclass(frozen=True)
class IncomeOriginConfig:
    """Mapeamentos para resolver origem de receitas.

    - ``pj_source_mapping``: ``{keyword: origem}`` para PJ
      (em ``categorization.json::pj_source_mapping.receita_pj``).
    - ``clt_source_mapping``: ``{keyword: origem}`` para CLT
      (em ``categorization.json::clt_source_mapping``).
    - ``static_origins``: categoria → origem fixa (defaults cobrem
      ``receita_aluguel``, ``receita_fgts``, etc.).
    - ``default_pj_origin``: fallback PJ quando nenhuma keyword bate.
    - ``default_clt_origin``: fallback CLT quando nenhuma keyword bate; se
      ``None``, usa o primeiro valor do ``clt_source_mapping`` (paridade
      com ``get_clt_origin`` v5.3.1).
    """

    pj_source_mapping: dict[str, str] = field(default_factory=dict)
    clt_source_mapping: dict[str, str] = field(default_factory=dict)
    static_origins: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_STATIC_ORIGINS))
    default_pj_origin: str = "Outras Receitas PJ"
    default_clt_origin: str | None = None  # None = fallback ao primeiro do mapping

    @classmethod
    def from_categorization(cls, categorization: dict | None = None) -> "IncomeOriginConfig":
        """Constrói a partir do dict ``categorization.json`` completo.

        Aceita ambos os layouts:
        - ``pj_source_mapping.receita_pj: {kw: origem}`` (formato atual)
        - ``pj_source_mapping: {kw: origem}`` (formato legacy plano)
        """
        cat = categorization or {}
        pj_raw = cat.get("pj_source_mapping") or {}
        if isinstance(pj_raw, dict) and "receita_pj" in pj_raw:
            pj_map = pj_raw["receita_pj"] or {}
        else:
            pj_map = pj_raw or {}
        clt_map = cat.get("clt_source_mapping") or {}
        return cls(
            pj_source_mapping={str(k): str(v) for k, v in pj_map.items()},
            clt_source_mapping={str(k): str(v) for k, v in clt_map.items()},
        )


# =============================================================================
# Service
# =============================================================================


class IncomeOriginResolver:
    """Resolve a origem (string humana) de uma receita classificada.

    Função pura — não depende de I/O nem de globals. Use
    :meth:`resolve_pj` / :meth:`resolve_clt` para os dois casos especiais
    e :meth:`resolve_for_category` quando já tiver a categoria mas precisa
    do label visível.
    """

    def __init__(self, config: IncomeOriginConfig | None = None) -> None:
        self._config = config or IncomeOriginConfig()

    # -- API direta --

    def resolve_pj(self, description: str) -> str:
        """Maps PJ income description → origem. Fallback: ``default_pj_origin``.
        Paridade com ``get_pj_origin`` (e4_categorize.py:196).
        """
        norm = _normalize_text(description)
        for keyword, origin in self._config.pj_source_mapping.items():
            if _normalize_text(keyword) in norm:
                return origin
        return self._config.default_pj_origin

    def resolve_clt(self, description: str) -> str:
        """Maps CLT income description → origem. Fallback: primeiro valor do
        mapping (paridade com ``get_clt_origin`` v5.3.1) ou ``default_clt_origin``
        se configurado, ou string genérica.
        """
        norm = _normalize_text(description)
        for keyword, origin in self._config.clt_source_mapping.items():
            if _normalize_text(keyword) in norm:
                return origin
        if self._config.default_clt_origin is not None:
            return self._config.default_clt_origin
        if self._config.clt_source_mapping:
            return next(iter(self._config.clt_source_mapping.values()))
        return "Receita CLT"

    def resolve_for_category(self, category: str, description: str) -> str:
        """Resolve origem dado (category, description). Roteia:

        - ``"receita_pj"`` → :meth:`resolve_pj`
        - ``"receita_clt"`` → :meth:`resolve_clt`
        - Demais categorias → ``static_origins.get(category, "Outras Receitas")``
          (paridade com `process_transactions` linhas 660-679).
        """
        if category == "receita_pj":
            return self.resolve_pj(description)
        if category == "receita_clt":
            return self.resolve_clt(description)
        return self._config.static_origins.get(category, "Outras Receitas")

    # -- Helpers --

    @staticmethod
    def known_categories(extra: Iterable[str] = ()) -> tuple[str, ...]:
        """Lista de categorias com mapeamento conhecido (PJ + CLT + estáticas).

        Útil para validar config (todo `receita_*` deveria ter uma origem
        estática ou cair em PJ/CLT).
        """
        return ("receita_pj", "receita_clt", *_DEFAULT_STATIC_ORIGINS.keys(), *extra)
