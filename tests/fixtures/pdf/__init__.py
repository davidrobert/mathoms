"""Synthetic PDF generator package.

Split of the monolithic ``tests/fixtures/pdf_generator.py`` (A6g.2 — T1.b).
Re-exports the public API so ``from tests.fixtures.pdf import ...`` continues
to work. The legacy ``tests/fixtures/pdf_generator.py`` stays as a shim until
all imports migrate to this package.
"""

from __future__ import annotations

from tests.fixtures.pdf.generator import (
    BankCode,
    DocKind,
    Transaction,
    generate_statement,
    write_statement_pdf,
)

__all__ = [
    "BankCode",
    "DocKind",
    "Transaction",
    "generate_statement",
    "write_statement_pdf",
]
