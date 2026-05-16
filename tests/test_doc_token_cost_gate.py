"""Testes do gate de economia de tokens da documentação."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_DIR = REPO_ROOT / "dev"

if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

import benchmark_doc_token_cost as bench  # noqa: E402


def test_context_pack_budget_without_reduction_pct_is_reported() -> None:
    results = {
        "Q7": bench.QueryResult(
            tokens=1001,
            chars=4004,
            files_read=["docs/_MOC/_generated/CONTEXT_INDEX.md"],
        )
    }

    assert bench.check_targets(results) == ["  Q7: 1001 > target 1000 (+1)"]


def test_target_summary_supports_queries_without_reduction_pct(capsys) -> None:
    bench._print_targets()

    captured = capsys.readouterr()
    assert "Q7: alvo 1000 tokens" in captured.err
