#!/usr/bin/env python3
"""Tests for validate_artifact schema validation."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.pipeline_common import validate_artifact


class TestValidateArtifact:
    def test_valid_e2_extract(self, tmp_path):
        data = {
            "pipeline_stage": "E2",
            "banco": "itau",
            "tipo": "extratoconta",
            "moeda": "BRL",
            "transacoes": [
                {"data": "2026-01-15", "descricao": "PIX", "valor": -100.0}
            ],
        }
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e2_extract.schema.json") is True

    def test_invalid_e2_missing_banco(self, tmp_path, capsys):
        data = {
            "pipeline_stage": "E2",
            "tipo": "extratoconta",
            "moeda": "BRL",
        }
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        # Default mode is 'warn' — should return True but log warning
        result = validate_artifact(path, "e2_extract.schema.json")
        assert result is True
        captured = capsys.readouterr()
        assert "banco" in captured.err

    def test_valid_e5_analysis(self, tmp_path):
        data = {
            "score": {"valor": 6.8, "classificacao": "Bom"},
            "patrimonio": {"bruto": 5000000, "liquido": 4000000},
            "fluxo_caixa": {"receita_total": 80000},
        }
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is True

    def test_missing_schema_returns_true(self, tmp_path):
        path = tmp_path / "test.json"
        path.write_text("{}")
        assert validate_artifact(path, "nonexistent_schema.json") is True

    def test_missing_data_file_returns_false(self, tmp_path):
        path = tmp_path / "missing.json"
        assert validate_artifact(path, "e2_extract.schema.json") is False
