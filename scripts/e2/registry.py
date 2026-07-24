#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2 Parser Registry — auto-discovers bank parsers and routes filenames to them.
"""

import importlib
import re
from typing import Callable, List, Optional, Tuple

from scripts.e2 import banks

BANK_MODULES = [
    "c6bank",
    "itau",
    "picpay",
    "bradesco",
    "santander",
    "btg",
    "rico",
    "wise",
    "bankofamerica",
    "quintoandar",
    "caixa",
]

# Types that are NOT bank statements and should not be matched by generic patterns
NON_STATEMENT_TYPES = re.compile(
    r"(investimentosposicao|carteirarendafixa|"
    r"informerendimentos|irpf|curriculo|holerite|baseline|dados_)"
)

# Built at module load time
_ALL_PARSERS: List[Tuple[re.Pattern, Callable]] = []
# Prefixos de banco que registram parser de extrato (derivado dos PARSERS no build).
_EXTRATO_BANK_PREFIXES: set = set()
_INVESTMENT_PATTERNS: List[str] = [
    r"cdbresumo",
    r"cdbdetalhes",
    r"investimentosposicao",
    r"carteirarendafixa",
]

# Casa o segmento `{banco}_extratoconta` do filename canônico (prefixo de hash opcional).
_EXTRATO_DOC_RE = re.compile(r"^(?:[a-f0-9]{12}_)?([a-z0-9]+)_extratoconta", re.IGNORECASE)


_HASH_PREFIX_RE = re.compile(r"^\^")


def _normalize_pattern(pattern_str: str) -> str:
    """Aceita o prefixo `{hash[:12]}_` (ADR-084) em patterns ancorados em `^`.

    Parsers foram escritos assumindo o filename canônico
    (ex.: `itau_extratoconta_2026.xls`). O ADR-084 adicionou prefixo
    `{sha256[:12]}_` para evitar colisão. Esta normalização injeta
    `(?:[a-f0-9]{12}_)?` após `^`, tornando o prefixo opcional.
    """
    return _HASH_PREFIX_RE.sub("^(?:[a-f0-9]{12}_)?", pattern_str)


def _build_registry() -> None:
    """Load all bank modules and collect their PARSERS lists."""
    global _ALL_PARSERS, _EXTRATO_BANK_PREFIXES
    _ALL_PARSERS = []
    _EXTRATO_BANK_PREFIXES = set()

    for module_name in BANK_MODULES:
        mod = importlib.import_module(f"scripts.e2.banks.{module_name}")
        parsers_list = getattr(mod, "PARSERS", [])
        for pattern_str, func_name in parsers_list:
            func = getattr(mod, func_name)
            _ALL_PARSERS.append((re.compile(_normalize_pattern(pattern_str), re.IGNORECASE), func))
            _EXTRATO_BANK_PREFIXES.update(re.findall(r"\^([a-z0-9]+)_extratoconta", pattern_str))


_build_registry()


def is_investment_type(filename: str) -> bool:
    """Check if a filename refers to an investment extract (CDB, etc)."""
    return any(re.search(p, filename) for p in _INVESTMENT_PATTERNS)


def route_to_parser(filename: str) -> Optional[Callable]:
    """Find the appropriate parser for a given filename.

    Returns parser function or None if no match.
    Investment types (CDB) are matched first.
    Non-statement types (investimentosposicao, etc) are skipped for generic patterns.
    """
    # Try all registered patterns in order
    for pattern, parser_fn in _ALL_PARSERS:
        if pattern.search(filename):
            return parser_fn

    return None


def is_processable(filename: str) -> bool:
    """Check if a filename is processable by any registered parser."""
    return route_to_parser(filename) is not None


def is_non_statement_type(filename: str) -> bool:
    """Check if filename is a non-statement type that should be skipped."""
    return bool(NON_STATEMENT_TYPES.search(filename))


def known_bank_extrato_without_parser(filename: str) -> Optional[str]:
    """Devolve o código do banco quando o filename é um `extratoconta*` de banco
    que TEM parser de extrato registrado mas mesmo assim não roteia — sinal de
    regressão do furo de roteamento de subtipo de moeda (extrato cairia no LLM e
    poderia sumir do relatório). Devolve None para banco genuinamente sem suporte
    (LLM esperado) ou quando o roteamento funciona."""
    if route_to_parser(filename) is not None:
        return None
    match = _EXTRATO_DOC_RE.match(filename)
    if not match:
        return None
    bank = match.group(1).lower()
    return bank if bank in _EXTRATO_BANK_PREFIXES else None
