#!/usr/bin/env python3
"""Unit tests for E7 cross-validation helpers."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import e7_review as e7


class TestScoreClassification:
    def test_custom_scoring_config(self, tmp_path: Path):
        (tmp_path / "config").mkdir(parents=True)
        (tmp_path / "config" / "scoring.json").write_text(
            json.dumps(
                {
                    "score_classificacao": [
                        {"min": 0, "label": "Baixo"},
                        {"min": 6, "label": "Alto"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        e7._init_config(tmp_path)
        assert e7._score_classification(7.0) == "Alto"
        assert e7._score_classification(5.0) == "Baixo"
