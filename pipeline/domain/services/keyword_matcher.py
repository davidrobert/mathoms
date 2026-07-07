"""KeywordMatcher — matching de keywords com wildcards e longest-match win
(Sessão A4a · Fase 7 foundation).

Extrai ``find_longest_matching_keyword`` (``e4_categorize.py:110``) em função
pura reutilizável. Suporta:

- Substring: ``"mercado"`` bate em ``"MERCADO PAO"``.
- Prefix wildcard: ``"PIX*"`` bate quando a descrição **começa** com ``"PIX "``.
- Suffix wildcard: ``"*BOLETO"`` bate quando a descrição **termina** com ``"BOLETO"``.
- Longest-match wins: se ``"MERCADO"`` e ``"MERCADO PAO"`` são keywords de
  categorias diferentes, a mais longa vence (reduz falsos positivos).

Normalização consistente com ``categorize_transactions.normalize_text`` (uppercase +
strip de acentos + colapsa whitespace).

``CategorizationService`` (extraído na A1) é mais simples — não faz wildcards
nem longest-match. Esta implementação é a usada pelo E4 Caminho B.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Mapping


def _normalize_text(text: str) -> str:
    """Paridade com ``categorize_transactions.normalize_text``."""
    if not text:
        return ""
    text = str(text).upper().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


def find_longest_matching_keyword(
    description: str,
    keywords_by_category: Mapping[str, list[str] | tuple[str, ...]],
) -> tuple[str | None, str | None]:
    """Encontra a keyword mais longa que bate na ``description``.

    Args:
        description: texto da transação (bruto, vai ser normalizado).
        keywords_by_category: ``{categoria: [kw1, kw2, ...]}``. Cada keyword
            pode ser substring ou usar ``*`` como prefix/suffix wildcard.

    Returns:
        ``(category, matched_keyword)`` com a keyword mais longa que bateu;
        ``(None, None)`` se nada bateu. A keyword retornada é a forma
        **normalizada** (uppercase sem acento) — não a original do config.
    """
    norm_desc = _normalize_text(description)
    if not norm_desc:
        return (None, None)

    longest_match: str | None = None
    longest_category: str | None = None

    for category, keywords in keywords_by_category.items():
        for keyword in keywords:
            norm_keyword = _normalize_text(keyword)
            matched = False

            if norm_keyword.endswith("*"):
                pattern = norm_keyword[:-1]
                if norm_desc.startswith(pattern):
                    matched = True
            elif norm_keyword.startswith("*"):
                pattern = norm_keyword[1:]
                if norm_desc.endswith(pattern):
                    matched = True
            else:
                if norm_keyword in norm_desc:
                    matched = True

            if matched and (longest_match is None or len(norm_keyword) > len(longest_match)):
                longest_match = norm_keyword
                longest_category = category

    return longest_category, longest_match


class KeywordMatcher:
    """Wrapper OO sobre :func:`find_longest_matching_keyword`.

    Útil quando o caller precisa injetar o mesmo dict de regras em múltiplos
    services (R9/ISP — evita passar o dict inteiro por assinatura).
    """

    def __init__(
        self,
        keywords_by_category: Mapping[str, list[str] | tuple[str, ...]] | None = None,
    ) -> None:
        self._rules = dict(keywords_by_category or {})

    def match(self, description: str) -> tuple[str | None, str | None]:
        return find_longest_matching_keyword(description, self._rules)

    def category_of(self, description: str) -> str | None:
        """Atalho: só a categoria, descarta a keyword matched."""
        return self.match(description)[0]
