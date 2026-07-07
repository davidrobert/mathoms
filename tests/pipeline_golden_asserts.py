"""Asserções partilhadas para goldens de execução do pipeline (E4+)."""

from __future__ import annotations

from pathlib import Path


def assert_qa_log_md(tenant_root: Path) -> None:
    """Contrato mínimo de `logs/qa_log.md` gerado por `categorize_transactions.generate_qa_log`."""
    log_path = tenant_root / "logs" / "qa_log.md"
    assert log_path.is_file(), f"expected {log_path}"
    text = log_path.read_text(encoding="utf-8")
    assert text.startswith("# QA Log — E4 Categorização"), log_path
    assert "### Transações não identificadas:" in text
    assert "### Taxa:" in text
