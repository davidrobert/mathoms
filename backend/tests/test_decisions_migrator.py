"""Testes do parser do migrator one-shot (A7.2a).

O migrator é descartável; estes testes garantem apenas que o parser
extrai os 15 itens canônicos antes da remoção de ``config/decisions.md``.
Após a Sprint A7.5, este arquivo + o migrator podem ser removidos juntos.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Import direto do módulo dev/ (não vai virar package permanente)
import importlib.util


def _load_migrator_module():
    import sys

    repo_root = Path(__file__).resolve().parents[2]
    name = "_migrator_under_test"
    spec = importlib.util.spec_from_file_location(
        name,
        repo_root / "dev" / "migrate_decisions_to_db.py",
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclass.fields() exige isto em 3.12
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SAMPLE_MARKDOWN = """
| # | Decisão | Data | Detalhes | Status |
|---|---|---|---|---|
| D01 | Quitar financiamento | Mar/2026 | rationale fictício | Pendente execução |
| D06 | Meta antiga | Mar/2026 | TRS 4% | **Superseded por D15** |
| D11 | Terminologia | Mar/2026 | usar por extenso | Decidido |
| D14 | Transferência | Mar/2026 | R$5k/mês | Pendente configuração |
| D15 | Nova meta | Abr/2026 | TRS 5% | TRS decidido; venda pendente avaliação |
""".strip()


@pytest.fixture
def migrator():
    return _load_migrator_module()


def test_parse_table_extracts_all_rows(migrator):
    parsed = migrator._parse_table(SAMPLE_MARKDOWN)
    assert [p.code for p in parsed] == ["D01", "D06", "D11", "D14", "D15"]


def test_parse_table_normalizes_status(migrator):
    parsed = migrator._parse_table(SAMPLE_MARKDOWN)
    by_code = {p.code: p for p in parsed}

    assert by_code["D01"].status == "Pendente"  # "Pendente execução"
    assert by_code["D06"].status == "Superseded"  # bold-stripped
    assert by_code["D11"].status == "Decidido"
    assert by_code["D14"].status == "Pendente"  # "Pendente configuração"
    assert by_code["D15"].status == "Decidido"  # "TRS decidido; ..." → split


def test_parse_table_keeps_rationale(migrator):
    parsed = migrator._parse_table(SAMPLE_MARKDOWN)
    by_code = {p.code: p for p in parsed}
    assert by_code["D01"].rationale == "rationale fictício"


def test_parse_table_skips_header_separator(migrator):
    parsed = migrator._parse_table(SAMPLE_MARKDOWN)
    # ``|---|---|---|---|---|`` não vira linha
    assert all(p.code.startswith("D") for p in parsed)


def test_parse_real_decisions_md_has_15_rows(migrator):
    """Anti-regressão: o config/decisions.md atual tem 15 itens."""
    repo_root = Path(__file__).resolve().parents[2]
    md_path = repo_root / "config" / "decisions.md"
    if not md_path.is_file():
        pytest.skip("config/decisions.md já removido (post-cutover)")

    parsed = migrator._parse_table(md_path.read_text(encoding="utf-8"))
    assert len(parsed) == 15
    assert parsed[0].code == "D01"
    assert parsed[-1].code == "D15"
