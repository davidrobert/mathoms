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
    r'(investimentosposicao|carteirarendafixa|'
    r'informerendimentos|irpf|curriculo|holerite|baseline|dados_)'
)

# Built at module load time
_ALL_PARSERS: List[Tuple[re.Pattern, Callable]] = []
_INVESTMENT_PATTERNS: List[str] = [
    r'cdbresumo', r'cdbdetalhes',
]


def _build_registry() -> None:
    """Load all bank modules and collect their PARSERS lists."""
    global _ALL_PARSERS
    _ALL_PARSERS = []

    for module_name in BANK_MODULES:
        mod = importlib.import_module(f"scripts.e2.banks.{module_name}")
        parsers_list = getattr(mod, "PARSERS", [])
        for pattern_str, func_name in parsers_list:
            func = getattr(mod, func_name)
            _ALL_PARSERS.append((re.compile(pattern_str, re.IGNORECASE), func))


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
