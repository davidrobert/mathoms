"""Canonicalização de nomes de bancos (Fase 6 foundation · ADR-089).

Substitui o dict módulo-global ``_BANCO_DISPLAY_TO_CANONICAL`` construído em
``scripts/e3_reconcile.py::_init_config`` (e usado tanto em
``validate_against_baseline`` quanto em ``generate_output_filename``).

A fonte de verdade é ``config/institutions.json`` → ``banco_canonical``:
mapeia ``"itau" → "Itaú"`` (code → display). Nesta camada de domínio, o que
interessa é o **inverso** (qualquer forma livre → código canônico), por dois
motivos:

- comparação segura sem falsos positivos de substring
  (``"c6"`` vs. ``"abc6xyz"`` — ver Fix 4.4 no legado);
- chave estável para agrupar artefatos em disco/DB.

Entradas são normalizadas agressivamente (``lower()``, strip, remoção de
espaços/acentos/caracteres ``/``&``) antes de comparar. Saída é sempre o
código canônico (``"itau"``, ``"c6bank"``) ou, quando não houver match, a
própria string normalizada (fallback conservador).

Zero I/O: recebe o dict já carregado. Quem lê JSON é o call-site
(``pipeline_common`` / ``StageConfig``).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass


def _normalize(raw: str) -> str:
    """Lowercase + strip + remove acentos, espaços e ``/&``.

    ``"Itaú Unibanco"`` → ``"itauunibanco"``; ``"C6 Bank"`` → ``"c6bank"``.
    """
    if not raw:
        return ""
    # NFKD separa acento do caractere base; mantemos apenas o base.
    stripped = "".join(
        c for c in unicodedata.normalize("NFKD", raw) if not unicodedata.combining(c)
    )
    return "".join(c for c in stripped.lower().strip() if c.isalnum())


@dataclass(frozen=True)
class BankCanonicalizer:
    """Resolve formas livres de nome de banco para código canônico.

    Constrói um índice ``normalized_form → canonical_code`` a partir de
    ``banco_canonical`` (``config/institutions.json``). Também indexa o
    próprio código como alvo válido — ``"c6bank"`` mapeia para ``"c6bank"``.

    Uso:

        >>> canon = BankCanonicalizer.from_institutions({
        ...     "banco_canonical": {"itau": "Itaú", "c6bank": "C6 Bank"}
        ... })
        >>> canon.canonicalize("Itaú")
        'itau'
        >>> canon.canonicalize("c6 bank")
        'c6bank'
        >>> canon.canonicalize("desconhecido")   # fallback normalizado
        'desconhecido'
    """

    _index: dict[str, str]

    @classmethod
    def from_institutions(cls, institutions: dict) -> "BankCanonicalizer":
        """Constrói a partir do dict ``config/institutions.json`` completo."""
        mapping = (institutions or {}).get("banco_canonical") or {}
        index: dict[str, str] = {}
        for code, display in mapping.items():
            # Sempre indexa o próprio código.
            index[_normalize(code)] = code
            # E a forma de display, que é a que aparece em extratos.
            if display:
                index[_normalize(display)] = code
        return cls(_index=index)

    @classmethod
    def empty(cls) -> "BankCanonicalizer":
        """Canonicalizer vazio — ``canonicalize`` retorna sempre a forma
        normalizada. Útil para testes e para call-sites que não têm acesso
        a ``institutions.json``.
        """
        return cls(_index={})

    def canonicalize(self, raw: str) -> str:
        """Retorna o código canônico; fallback = string normalizada."""
        norm = _normalize(raw)
        return self._index.get(norm, norm)

    def are_same_bank(self, a: str, b: str) -> bool:
        """``True`` se ``a`` e ``b`` canonicalizam para o mesmo código.

        Comparação segura sem falsos positivos de substring (fix 4.4 do
        legado).
        """
        return self.canonicalize(a) == self.canonicalize(b)


# -----------------------------------------------------------------------------
# Função livre (conveniência — quando já se tem o dict carregado e não vale
# a pena instanciar o canonicalizer).
# -----------------------------------------------------------------------------


def canonicalize_bank(raw: str, institutions: dict) -> str:
    """Atalho ``BankCanonicalizer.from_institutions(...).canonicalize(raw)``.

    Só use quando for uma chamada isolada. Para múltiplas consultas, instancie
    o ``BankCanonicalizer`` uma vez (cacheia o índice).
    """
    return BankCanonicalizer.from_institutions(institutions).canonicalize(raw)
