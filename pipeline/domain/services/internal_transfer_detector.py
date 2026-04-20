"""InternalTransferDetector — detecta transferências internas (Sessão A3a · Fase 7 foundation).

Extrai ``is_internal_transfer`` (e4_categorize.py:144) num domain service puro,
recebendo configuração tipada via :class:`InternalTransferConfig` (R9/ISP).

Conservador por design — só marca como interna quando o match é claro:
1. Padrões internos exatos (``internal_patterns``).
2. Recipientes conhecidos da família (``internal_recipients``).
3. Padrões bank-specific com **match exato** (não substring), evitando
   falsos positivos para bancos com keywords genéricas como ``"Pagamento"``.
4. Padrões globais de transferência (``global_transfer_patterns``).

Genéricos (PIX/TED desconhecido) NÃO são marcados como internos.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


def _normalize_text(text: str) -> str:
    """Uppercase + strip de acentos + colapsa whitespace (paridade com
    ``e4_categorize.normalize_text``)."""
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


@dataclass(frozen=True)
class InternalTransferConfig:
    """Padrões para classificar transferência como interna.

    - ``internal_patterns``: substrings que indicam transferência interna
      (qualquer ocorrência → match).
    - ``internal_recipients``: nomes/identificadores de contas próprias.
    - ``bank_specific_patterns``: ``{banco_keyword: (padrão_exato, ...)}`` —
      padrões que **só** valem para descrições de extratos do banco
      especificado, e que precisam de **igualdade exata** (após normalize)
      para evitar falsos positivos.
    - ``global_transfer_patterns``: substrings que sempre marcam como
      transferência (PIX SAQUE, etc.).
    """

    internal_patterns: tuple[str, ...] = ()
    internal_recipients: tuple[str, ...] = ()
    bank_specific_patterns: dict[str, tuple[str, ...]] = field(default_factory=dict)
    global_transfer_patterns: tuple[str, ...] = ()

    @classmethod
    def from_categorization(
        cls, categorization: dict | None = None
    ) -> "InternalTransferConfig":
        """Constrói a partir do dict ``categorization.json``.

        Esperado:
        - ``internal_transfer_patterns: list[str]``
        - ``internal_transfer_recipients: list[str]``
        - ``bank_specific_transfer_patterns: dict[str, list[str]]``
        - ``global_transfer_patterns: list[str]``

        Chaves ausentes viram tuplas/dicts vazios.
        """
        cat = categorization or {}
        bank_raw = cat.get("bank_specific_transfer_patterns") or {}
        bank_specific = {
            str(k): tuple(str(p) for p in v)
            for k, v in bank_raw.items()
            if not str(k).startswith("_")
        }
        return cls(
            internal_patterns=tuple(
                str(p) for p in (cat.get("internal_transfer_patterns") or [])
            ),
            internal_recipients=tuple(
                str(r) for r in (cat.get("internal_transfer_recipients") or [])
            ),
            bank_specific_patterns=bank_specific,
            global_transfer_patterns=tuple(
                str(p) for p in (cat.get("global_transfer_patterns") or [])
            ),
        )


# =============================================================================
# Service
# =============================================================================


class InternalTransferDetector:
    """Detecta se uma descrição de transação representa transferência interna.

    Função pura — sem I/O, sem globals. Reusa o ``config`` em todas as
    chamadas (instanciação barata, mas a normalização interna é repetida
    a cada chamada).
    """

    def __init__(self, config: InternalTransferConfig | None = None) -> None:
        self._config = config or InternalTransferConfig()

    def is_internal_transfer(
        self,
        description: str,
        *,
        banco: str = "",
    ) -> bool:
        """Retorna ``True`` se a descrição casa com algum padrão de
        transferência interna. ``banco`` é opcional — quando informado,
        ativa o match de ``bank_specific_patterns``.
        """
        norm_desc = _normalize_text(description)
        if not norm_desc:
            return False

        # 1. Padrões internos exatos (substring).
        for pattern in self._config.internal_patterns:
            if _normalize_text(pattern) in norm_desc:
                return True

        # 2. Recipientes conhecidos.
        for recipient in self._config.internal_recipients:
            if _normalize_text(recipient) in norm_desc:
                return True

        # 3. Bank-specific: requer match exato (anti-falso-positivo).
        norm_banco = _normalize_text(banco)
        for bank_key, patterns in self._config.bank_specific_patterns.items():
            if _normalize_text(bank_key) in norm_banco:
                for pat in patterns:
                    if norm_desc.strip() == _normalize_text(pat):
                        return True

        # 4. Global patterns (substring).
        for pat in self._config.global_transfer_patterns:
            if _normalize_text(pat) in norm_desc:
                return True

        return False
