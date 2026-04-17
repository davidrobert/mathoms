"""Regressão opcional — PDFs reais **anonimizados** em `tests/fixtures/e2_real_pdf_anon/`.

Fase 2 do plano E2 (ver `tests/fixtures/e2_real_pdf_anon/README.md`). Com zero `*.pdf` na pasta,
o teste passa; cada PDF adicionado passa a ser validado no CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.e2.registry import route_to_parser

pytest.importorskip("pdfplumber")

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "e2_real_pdf_anon"


def _anon_pdfs() -> list[Path]:
    if not _FIXTURE_DIR.is_dir():
        return []
    return sorted(p for p in _FIXTURE_DIR.glob("*.pdf") if p.is_file())


def test_e2_real_pdf_anon_directory_exists():
    assert _FIXTURE_DIR.is_dir()
    assert (_FIXTURE_DIR / "README.md").is_file()


def test_each_anonymized_pdf_runs_registered_parser():
    """Sem `*.pdf`: no-op (Fase 2 ainda vazia). Com PDFs: um assert por arquivo."""
    for pdf_path in _anon_pdfs():
        filename = pdf_path.name
        parser_fn = route_to_parser(filename)
        assert parser_fn is not None, (
            f"Nenhum parser em registry para filename={filename!r} — "
            "ajuste o nome ou adicione padrão em scripts/e2/banks/*."
        )
        result = parser_fn(pdf_path, filename)
        assert isinstance(result, dict)
        assert result
        assert (
            "banco" in result
            or "tipo" in result
            or "erro" in result
            or "requires_llm_fallback" in result
        )
