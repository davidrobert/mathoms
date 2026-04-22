"""Shim self-contained para ``tests/fixtures/pdf/`` (A6g.2 — T1.b).

O módulo monolítico de 1067 linhas foi dividido em:
- ``tests/fixtures/pdf/formatters.py`` — helpers BRL/USD + meses
- ``tests/fixtures/pdf/<banco>.py`` — um módulo por layout dedicado
- ``tests/fixtures/pdf/generator.py`` — ``generate_statement`` dispatcher

Este arquivo continua resolvível por dois caminhos:

1. ``from tests.fixtures.pdf_generator import generate_statement`` — import
   normal, delega para o pacote quando ``tests.fixtures.pdf`` é importável.
2. Carregamento manual via ``importlib.util.spec_from_file_location`` (usado
   por ``backend/tests/test_golden_pipeline.py`` — ver comentário lá). Nesse
   cenário, o namespace ``tests`` pode apontar para ``backend/tests/`` e o
   pacote não resolve; fazemos bootstrap manual dos submódulos por path para
   preservar o contrato histórico.

Novos call-sites devem preferir ``from tests.fixtures.pdf import ...``.
"""

from __future__ import annotations

import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path


def _bootstrap_from_path():
    """Carrega ``tests/fixtures/pdf/*.py`` manualmente e registra no sys.modules.

    Necessário quando este arquivo é carregado via ``spec_from_file_location``
    sob um nome artificial (ex.: ``_synthetic_pdf_generator``) — nesse caso
    ``tests.fixtures.pdf`` pode não estar importável.
    """
    here = _Path(__file__).resolve().parent / "pdf"
    # Ordem de dependência: formatters → banks → generator.
    order = [
        "formatters",
        "btg",
        "rico",
        "wise",
        "picpay",
        "bankofamerica",
        "santander",
        "itau",
        "c6",
        "bradesco",
        "caixa",
        "quintoandar",
        "generator",
    ]
    # Registra o pacote pai virtual para que ``from tests.fixtures.pdf.X
    # import Y`` dentro de cada submódulo resolva.
    pkg_name = "tests.fixtures.pdf"
    if pkg_name not in _sys.modules:
        pkg_spec = _ilu.spec_from_file_location(
            pkg_name,
            here / "__init__.py",
            submodule_search_locations=[str(here)],
        )
        pkg = _ilu.module_from_spec(pkg_spec)
        _sys.modules[pkg_name] = pkg
    for name in order:
        full = f"{pkg_name}.{name}"
        if full in _sys.modules:
            continue
        spec = _ilu.spec_from_file_location(full, here / f"{name}.py")
        mod = _ilu.module_from_spec(spec)
        _sys.modules[full] = mod
        spec.loader.exec_module(mod)
    return _sys.modules[f"{pkg_name}.generator"]


try:
    from tests.fixtures.pdf import (  # noqa: F401
        BankCode,
        DocKind,
        Transaction,
        generate_statement,
        write_statement_pdf,
    )
except ImportError:  # pragma: no cover — fallback para carregamento por path
    _gen = _bootstrap_from_path()
    BankCode = _gen.BankCode
    DocKind = _gen.DocKind
    Transaction = _gen.Transaction
    generate_statement = _gen.generate_statement
    write_statement_pdf = _gen.write_statement_pdf


__all__ = [
    "BankCode",
    "DocKind",
    "Transaction",
    "generate_statement",
    "write_statement_pdf",
]
