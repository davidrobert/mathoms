#!/usr/bin/env python3
"""Tests for validate_artifact schema validation."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.pipeline_common import validate_artifact

_TOP_ATIVO_VALID = {
    "posicao": 1,
    "nome": "Tesouro IPCA+ 2045",
    "classe": "Renda Fixa",
    "membro": "david",
    "instituicao": "Btg",
    "valor": 300000,
    "pct_carteira": 30.0,
    "tipo_origem": "investimento",
}
_IMOVEL_VALID = {
    "posicao": 2,
    "nome": "Sala comercial",
    "classe": "Imóveis Investimento",
    "membro": "",
    "instituicao": "",
    "valor": 250000,
    "pct_carteira": 25.0,
    "tipo_origem": "imovel",
}
_TOP_ATIVO_INVALID_CLASSE = {**_TOP_ATIVO_VALID, "classe": "ClasseDesconhecida"}

_INST_VALID = [
    {"membro": "david", "instituicoes": ["Btg", "Itau"]},
    {"membro": "mariana", "instituicoes": ["Xp"]},
]


def _e5_with_top_ativos(*items):
    return {
        "score": {"valor": 6.8, "classificacao": "Bom"},
        "patrimonio": {"bruto": 5000000, "liquido": 4000000},
        "fluxo_caixa": {"receita_total": 80000},
        "investimentos": {
            "tabela_classes": [{"categoria": "Renda Fixa", "valor": 800000, "pct": 80.0}],
            "total": 1000000,
            "top_ativos": list(items),
        },
    }


def _e5_with_instituicoes(por_membro, n_imoveis=0):
    return {
        "score": {"valor": 6.8, "classificacao": "Bom"},
        "patrimonio": {"bruto": 5000000, "liquido": 4000000},
        "fluxo_caixa": {},
        "investimentos": {
            "instituicoes_por_membro": por_membro,
            "n_imoveis_total": n_imoveis,
        },
    }


class TestValidateArtifact:
    def test_valid_e2_extract(self, tmp_path):
        data = {
            "pipeline_stage": "E2",
            "banco": "itau",
            "tipo": "extratoconta",
            "moeda": "BRL",
            "transacoes": [{"data": "2026-01-15", "descricao": "PIX", "valor": -100.0}],
        }
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e2_extract.schema.json") is True

    def test_invalid_e2_missing_banco(self, tmp_path, caplog, monkeypatch):
        import logging

        # Força warn explicitamente — CI roda o módulo com
        # MATHOMS_PIPELINE_SCHEMA_MODE=strict para cobrir o caminho strict.
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "warn")
        caplog.set_level(logging.WARNING)
        data = {
            "pipeline_stage": "E2",
            "tipo": "extratoconta",
            "moeda": "BRL",
        }
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        # warn mode: should return True but log warning
        result = validate_artifact(path, "e2_extract.schema.json")
        assert result is True
        assert "banco" in caplog.text

    def test_invalid_e2_strict_mode_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        data = {
            "pipeline_stage": "E2",
            "tipo": "extratoconta",
            "moeda": "BRL",
        }
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e2_extract.schema.json") is False

    def test_valid_e5_analysis(self, tmp_path):
        data = {
            "score": {"valor": 6.8, "classificacao": "Bom"},
            "patrimonio": {"bruto": 5000000, "liquido": 4000000},
            "fluxo_caixa": {"receita_total": 80000},
        }
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is True

    def test_valid_e5_analysis_with_top_ativos(self, tmp_path):
        data = _e5_with_top_ativos(_TOP_ATIVO_VALID, _IMOVEL_VALID)
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is True

    def test_invalid_top_ativos_strict_mode_rejects_unknown_classe(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        data = _e5_with_top_ativos(_TOP_ATIVO_INVALID_CLASSE)
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is False

    def test_valid_e5_with_instituicoes_por_membro(self, tmp_path):
        data = _e5_with_instituicoes(_INST_VALID, n_imoveis=2)
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is True

    def test_invalid_instituicoes_strict_mode_rejects_duplicate(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        data = _e5_with_instituicoes([{"membro": "david", "instituicoes": ["Btg", "Btg"]}])
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e5_analysis.schema.json") is False

    def test_valid_e3_reconciled(self, tmp_path):
        data = {
            "banco": "itau",
            "tipo_conta": "extratoconta",
            "titular": None,
            "moeda": "BRL",
            "periodo_cobertura": {"inicio": "2026-01-01", "fim": "2026-01-31"},
            "saldo_inicial": 0.0,
            "saldo_inicial_unknown": False,
            "saldo_final": 0.0,
            "saldo_final_unknown": False,
            "fontes": ["a-2_extract.json"],
            "transacoes_total": 0,
            "transacoes_duplicadas_removidas": 0,
            "transacoes": [],
        }
        path = tmp_path / "e3.json"
        path.write_text(json.dumps(data))
        assert validate_artifact(path, "e3_reconciled.schema.json") is True

    def test_missing_schema_returns_true(self, tmp_path):
        path = tmp_path / "test.json"
        path.write_text("{}")
        assert validate_artifact(path, "nonexistent_schema.json") is True

    def test_missing_data_file_returns_false(self, tmp_path):
        path = tmp_path / "missing.json"
        assert validate_artifact(path, "e2_extract.schema.json") is False
